import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ml.models.random_forest import RandomForestClassifierModel
from backend.app.ml.data.preprocessing.pipeline import NetworkDataPipeline
from backend.app.ml.registry.model_registry import model_registry


class RandomForestPrediction(BaseModel):
    """Standardized prediction output schema for Random Forest supervised baseline."""
    model_name: str = "random_forest"
    model_version: str = "1.0.0"
    dataset: str = "generic"
    prediction: str  # "normal" | "attack"
    is_anomaly: bool
    raw_score: float  # Predicted probability of attack class P(y=1)
    anomaly_score: float = Field(ge=0.0, le=100.0)  # Normalized 0-100 anomaly score
    confidence_score: float  # Confidence level: max(P(0), P(1))
    threshold: float  # Decision threshold
    processing_time_ms: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RandomForestPredictor:
    """
    Production-ready Inference Engine for Supervised Random Forest Baseline.
    Loads paired Phase 3 Preprocessing Pipeline and trained RandomForestClassifierModel
    to perform single-record and batch classifications with probability calibration.
    """

    def __init__(
        self,
        dataset_name: str = "synthetic",
        model_version: Optional[str] = None,
        model_path: Optional[Union[str, Path]] = None,
        preprocessing_dir: Optional[Union[str, Path]] = None,
        custom_threshold: Optional[float] = None,
    ):
        self.dataset_name = dataset_name.lower().strip()
        self.model_version = model_version
        self.model_path = Path(model_path) if model_path else None
        self.preprocessing_dir = Path(preprocessing_dir) if preprocessing_dir else None
        self.custom_threshold = custom_threshold

        self.model: Optional[RandomForestClassifierModel] = None
        self.pipeline: Optional[NetworkDataPipeline] = None
        self.is_loaded: bool = False

    @property
    def threshold(self) -> float:
        if self.custom_threshold is not None:
            return self.custom_threshold
        if self.model is not None:
            return self.model.decision_threshold
        return settings.RF_THRESHOLD

    def load(self) -> None:
        """Load trained Random Forest model and Phase 3 preprocessing artifacts."""
        logger.info(f"Loading RandomForestPredictor for dataset '{self.dataset_name}'...")

        # 1. Resolve Model Path from Registry if not provided
        if not self.model_path:
            meta = model_registry.get_model("random_forest", dataset=self.dataset_name, version=self.model_version)
            if not meta:
                v_tag = f"_v{self.model_version}" if self.model_version else "_v1.0.0"
                candidate = settings.MODELS_DIR / f"random_forest_{self.dataset_name}{v_tag}.joblib"
                if candidate.exists():
                    self.model_path = candidate
                else:
                    raise FileNotFoundError(
                        f"No active Random Forest model registered or found for dataset '{self.dataset_name}'."
                    )
            else:
                self.model_path = Path(meta["artifact_path"])
                if not self.preprocessing_dir and meta.get("preprocessing_path"):
                    self.preprocessing_dir = Path(meta["preprocessing_path"])

        if not self.model_path.exists():
            raise FileNotFoundError(f"Random Forest artifact not found at: {self.model_path}")

        # 2. Load Model
        self.model = RandomForestClassifierModel.load(self.model_path)

        # 3. Resolve and Load Preprocessing Pipeline
        if not self.preprocessing_dir:
            self.preprocessing_dir = settings.PREPROCESSING_DIR / self.dataset_name

        if (self.preprocessing_dir / "pipeline.joblib").exists():
            self.pipeline = NetworkDataPipeline.load(self.preprocessing_dir)
        else:
            logger.warning(
                f"Preprocessing pipeline not found in {self.preprocessing_dir}. Predictor will expect pre-scaled features."
            )
            self.pipeline = None

        self.is_loaded = True
        logger.info(
            f"RandomForestPredictor successfully initialized: model='{self.model_path.name}', "
            f"features={self.model.feature_count_}, threshold={self.threshold:.4f}"
        )

    def _format_prediction(
        self,
        prob_attack: float,
        prob_normal: float,
        elapsed_ms: float,
    ) -> RandomForestPrediction:
        """Construct standard RandomForestPrediction object."""
        is_attack = bool(prob_attack >= self.threshold)
        prediction_label = "attack" if is_attack else "normal"
        confidence = max(prob_attack, prob_normal)
        anomaly_score = float(np.round(np.clip(prob_attack * 100.0, 0.0, 100.0), 2))

        return RandomForestPrediction(
            model_name="random_forest",
            model_version=self.model_version or "1.0.0",
            dataset=self.dataset_name,
            prediction=prediction_label,
            is_anomaly=is_attack,
            raw_score=round(prob_attack, 6),
            anomaly_score=anomaly_score,
            confidence_score=round(confidence, 4),
            threshold=round(self.threshold, 4),
            processing_time_ms=round(elapsed_ms, 3),
            metadata={
                "class_probability_normal": round(prob_normal, 6),
                "class_probability_attack": round(prob_attack, 6),
                "decision_threshold": round(self.threshold, 4),
                "threshold_strategy": self.model.threshold_strategy if self.model else "default",
                "feature_count": self.model.feature_count_ if self.model else None,
            },
        )

    def predict_single(self, record: Union[Dict[str, Any], pd.Series]) -> RandomForestPrediction:
        """
        Execute single-record classification and probability estimation.
        """
        if not self.is_loaded or self.model is None:
            self.load()

        start_time = time.perf_counter()

        if isinstance(record, dict):
            df = pd.DataFrame([record])
        elif isinstance(record, pd.Series):
            df = pd.DataFrame([record.to_dict()])
        else:
            raise TypeError(f"Expected dict or pd.Series, got {type(record)}")

        if self.pipeline is not None:
            X_proc = self.pipeline.transform(df)
        else:
            X_proc = df

        probs = self.model.predict_proba(X_proc)[0]
        prob_normal, prob_attack = float(probs[0]), float(probs[1])

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return self._format_prediction(
            prob_attack=prob_attack,
            prob_normal=prob_normal,
            elapsed_ms=elapsed_ms,
        )

    def predict_batch(self, df: pd.DataFrame) -> List[RandomForestPrediction]:
        """
        Execute high-throughput batch classification across multiple network records.
        """
        if not self.is_loaded or self.model is None:
            self.load()

        if df.empty:
            return []

        start_time = time.perf_counter()

        if self.pipeline is not None:
            X_proc = self.pipeline.transform(df)
        else:
            X_proc = df

        probs = self.model.predict_proba(X_proc)
        total_elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        avg_elapsed_per_row = total_elapsed_ms / max(1, len(df))

        results = []
        for i in range(len(df)):
            prob_normal = float(probs[i, 0])
            prob_attack = float(probs[i, 1])
            results.append(
                self._format_prediction(
                    prob_attack=prob_attack,
                    prob_normal=prob_normal,
                    elapsed_ms=avg_elapsed_per_row,
                )
            )
        return results
