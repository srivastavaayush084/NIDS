import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ml.models.isolation_forest import IsolationForestDetector
from backend.app.ml.data.preprocessing.pipeline import NetworkDataPipeline
from backend.app.ml.registry.model_registry import model_registry


class IsolationForestPrediction(BaseModel):
    """Standardized prediction output schema for Isolation Forest anomaly detection."""
    model_name: str = "isolation_forest"
    model_version: str = "1.0.0"
    dataset: str = "generic"
    prediction: str  # "normal" | "anomaly"
    is_anomaly: bool
    raw_score: float
    anomaly_score: float = Field(ge=0.0, le=100.0)
    threshold: float
    processing_time_ms: float


class IsolationForestPredictor:
    """
    Production-ready Inference Engine for Isolation Forest Anomaly Detection.
    Loads paired preprocessing pipeline and trained model artifacts to perform
    low-latency single-flow scoring and high-throughput batch predictions.
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

        self.detector: Optional[IsolationForestDetector] = None
        self.pipeline: Optional[NetworkDataPipeline] = None
        self.is_loaded: bool = False
        self.threshold: float = 60.0

    def load(self) -> "IsolationForestPredictor":
        """
        Load trained IsolationForest model and corresponding Phase 3 Preprocessing Pipeline.
        """
        logger.info(f"Loading IsolationForestPredictor for dataset '{self.dataset_name}'...")

        # 1. Resolve model artifact path
        if not self.model_path:
            meta = model_registry.get_model("isolation_forest", dataset=self.dataset_name, version=self.model_version)
            if meta and Path(meta.get("artifact_path", "")).exists():
                self.model_path = Path(meta["artifact_path"])
                self.model_version = meta.get("version", "1.0.0")
                if not self.preprocessing_dir and meta.get("preprocessing_dir"):
                    self.preprocessing_dir = Path(meta["preprocessing_dir"])
            else:
                # Fallback search in models directory
                candidate = settings.MODELS_DIR / f"isolation_forest_{self.dataset_name}_v{self.model_version or '1.0.0'}.joblib"
                if candidate.exists():
                    self.model_path = candidate
                else:
                    # Find any matching isolation_forest for this dataset
                    matches = list(settings.MODELS_DIR.glob(f"isolation_forest_{self.dataset_name}_*.joblib"))
                    if matches:
                        self.model_path = matches[0]

        if not self.model_path or not self.model_path.exists():
            raise FileNotFoundError(
                f"Isolation Forest model artifact not found at '{self.model_path}'. "
                f"Please train the model first using scripts/train_isolation_forest.py --dataset {self.dataset_name}"
            )

        # 2. Resolve preprocessing pipeline directory
        if not self.preprocessing_dir:
            self.preprocessing_dir = settings.PREPROCESSING_DIR / self.dataset_name

        if not self.preprocessing_dir.exists() or not (self.preprocessing_dir / "pipeline.joblib").exists():
            raise FileNotFoundError(
                f"Preprocessing pipeline artifact not found at '{self.preprocessing_dir}'. "
                f"Please run scripts/prepare_dataset.py --dataset {self.dataset_name} first."
            )

        # 3. Load artifacts
        self.detector = IsolationForestDetector.load(self.model_path)
        self.pipeline = NetworkDataPipeline.load(self.preprocessing_dir)
        self.threshold = self.custom_threshold if self.custom_threshold is not None else self.detector.anomaly_threshold
        self.is_loaded = True

        logger.info(
            f"IsolationForestPredictor successfully initialized: model='{self.model_path.name}', "
            f"features={self.detector.feature_count_}, threshold={self.threshold}"
        )
        return self

    def _prepare_input_df(self, record: Union[Dict[str, Any], pd.Series, pd.DataFrame]) -> pd.DataFrame:
        """Standardize single record or batch input into a DataFrame."""
        if isinstance(record, dict):
            df = pd.DataFrame([record])
        elif isinstance(record, pd.Series):
            df = pd.DataFrame([record.to_dict()])
        elif isinstance(record, pd.DataFrame):
            df = record.copy()
        else:
            raise TypeError(f"Unsupported record type: {type(record)}. Expected dict, pd.Series, or pd.DataFrame.")
        return df

    def predict_single(self, record: Union[Dict[str, Any], pd.Series, pd.DataFrame]) -> IsolationForestPrediction:
        """
        Execute single-flow anomaly detection with execution latency tracking.
        """
        if not self.is_loaded or self.detector is None or self.pipeline is None:
            self.load()

        start_time = time.perf_counter()
        df_raw = self._prepare_input_df(record)

        # Transform using saved preprocessing pipeline (leak-free)
        X_proc = self.pipeline.transform(df_raw)
        raw_score = float(self.detector.score_samples(X_proc)[0])
        anomaly_score = float(self.detector.compute_anomaly_scores(X_proc)[0])

        is_anomaly = bool(anomaly_score >= self.threshold)
        prediction_label = "anomaly" if is_anomaly else "normal"

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return IsolationForestPrediction(
            model_name="isolation_forest",
            model_version=self.model_version or "1.0.0",
            dataset=self.dataset_name,
            prediction=prediction_label,
            is_anomaly=is_anomaly,
            raw_score=round(raw_score, 4),
            anomaly_score=anomaly_score,
            threshold=self.threshold,
            processing_time_ms=round(elapsed_ms, 3),
        )

    def predict_batch(self, df: pd.DataFrame) -> List[IsolationForestPrediction]:
        """
        Execute vectorized batch inference across multiple network records.
        """
        if not self.is_loaded or self.detector is None or self.pipeline is None:
            self.load()

        if df.empty:
            return []

        start_time = time.perf_counter()
        X_proc = self.pipeline.transform(df)

        raw_scores = self.detector.score_samples(X_proc)
        anomaly_scores = self.detector.compute_anomaly_scores(X_proc)
        is_anomalies = (anomaly_scores >= self.threshold)

        total_elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        avg_elapsed_per_row = total_elapsed_ms / max(1, len(df))

        results = []
        for i in range(len(df)):
            is_anom = bool(is_anomalies[i])
            results.append(
                IsolationForestPrediction(
                    model_name="isolation_forest",
                    model_version=self.model_version or "1.0.0",
                    dataset=self.dataset_name,
                    prediction="anomaly" if is_anom else "normal",
                    is_anomaly=is_anom,
                    raw_score=round(float(raw_scores[i]), 4),
                    anomaly_score=float(anomaly_scores[i]),
                    threshold=self.threshold,
                    processing_time_ms=round(avg_elapsed_per_row, 3),
                )
            )

        return results
