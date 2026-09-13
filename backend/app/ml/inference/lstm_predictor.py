import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ml.models.lstm_autoencoder import LSTMAutoencoderDetector
from backend.app.ml.sequence.sequence_builder import SequenceBuilder, SequenceWindow
from backend.app.ml.sequence.sequence_validator import validate_sequence_data
from backend.app.ml.data.preprocessing.pipeline import NetworkDataPipeline
from backend.app.ml.registry.model_registry import model_registry


class LSTMPrediction(BaseModel):
    """Standardized prediction output schema for LSTM Autoencoder sequential anomaly detection."""
    model_name: str = "lstm_autoencoder"
    model_version: str = "1.0.0"
    dataset: str = "generic"
    prediction: str  # "normal" | "anomaly"
    is_anomaly: bool
    raw_score: float  # Raw sequence reconstruction MSE
    raw_mse: Optional[float] = None  # Alias field for raw sequence MSE
    anomaly_score: float = Field(ge=0.0, le=100.0)
    threshold: float  # Learned sequence reconstruction error decision threshold
    processing_time_ms: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LSTMPredictor:
    """
    Production-ready Inference Engine for Sequential LSTM Autoencoder Anomaly Detection.
    Loads paired Phase 3 Preprocessing Pipeline and trained PyTorch LSTM Autoencoder
    to score single sequence windows, batch sequences, or continuous event streams.
    """

    def __init__(
        self,
        dataset_name: str = "synthetic",
        model_version: Optional[str] = None,
        model_path: Optional[Union[str, Path]] = None,
        preprocessing_dir: Optional[Union[str, Path]] = None,
        custom_threshold: Optional[float] = None,
        device: Optional[str] = None,
    ):
        self.dataset_name = dataset_name.lower().strip()
        self.model_version = model_version
        self.model_path = Path(model_path) if model_path else None
        self.preprocessing_dir = Path(preprocessing_dir) if preprocessing_dir else None
        self.custom_threshold = custom_threshold
        self.device = device

        self.detector: Optional[LSTMAutoencoderDetector] = None
        self.pipeline: Optional[NetworkDataPipeline] = None
        self.sequence_builder: Optional[SequenceBuilder] = None
        self.is_loaded: bool = False

    @property
    def threshold(self) -> float:
        if self.custom_threshold is not None:
            return self.custom_threshold
        if self.detector is not None:
            return self.detector.reconstruction_threshold
        return settings.DEFAULT_ANOMALY_THRESHOLD

    def load(self) -> None:
        """Load trained LSTM model weights and Phase 3 preprocessing artifacts."""
        logger.info(f"Loading LSTMPredictor for dataset '{self.dataset_name}'...")

        # 1. Resolve Model Path from Registry if not provided
        if not self.model_path:
            meta = model_registry.get_model("lstm_autoencoder", dataset=self.dataset_name, version=self.model_version)
            if not meta:
                # Try fallback filename in models directory
                v_tag = f"_v{self.model_version}" if self.model_version else "_v1.0.0"
                candidate = settings.MODELS_DIR / f"lstm_autoencoder_{self.dataset_name}{v_tag}.pt"
                if candidate.exists():
                    self.model_path = candidate
                else:
                    raise FileNotFoundError(
                        f"No active LSTM Autoencoder model registered or found for dataset '{self.dataset_name}'."
                    )
            else:
                self.model_path = Path(meta["artifact_path"])
                if not self.preprocessing_dir and meta.get("preprocessing_path"):
                    self.preprocessing_dir = Path(meta["preprocessing_path"])

        if not self.model_path.exists():
            raise FileNotFoundError(f"LSTM model checkpoint not found at: {self.model_path}")

        # 2. Load LSTM Autoencoder Detector
        self.detector = LSTMAutoencoderDetector.load(self.model_path, device=self.device)

        # 3. Resolve and Load Preprocessing Pipeline
        if not self.preprocessing_dir:
            self.preprocessing_dir = settings.PREPROCESSING_DIR / self.dataset_name

        if (self.preprocessing_dir / "pipeline.joblib").exists():
            self.pipeline = NetworkDataPipeline.load(self.preprocessing_dir)
        else:
            logger.warning(
                f"Preprocessing pipeline not found in {self.preprocessing_dir}. Predictor will expect pre-scaled sequences."
            )
            self.pipeline = None

        # 4. Initialize SequenceBuilder matching detector sequence length
        self.sequence_builder = SequenceBuilder(
            sequence_length=self.detector.seq_len,
            stride=1,
            label_aggregation="any",
        )

        self.is_loaded = True
        logger.info(
            f"LSTMPredictor successfully initialized: model='{self.model_path.name}', "
            f"seq_len={self.detector.seq_len}, features={self.detector.input_dim}, threshold={self.threshold:.6f}"
        )

    def _format_prediction(
        self,
        raw_mse: float,
        anomaly_score: float,
        elapsed_ms: float,
        timestep_errors: Optional[np.ndarray] = None,
        window: Optional[SequenceWindow] = None,
    ) -> LSTMPrediction:
        """Construct standard LSTMPrediction object."""
        is_anomaly = bool(raw_mse >= self.threshold)
        prediction_label = "anomaly" if is_anomaly else "normal"

        meta_dict: Dict[str, Any] = {
            "reconstruction_error": round(raw_mse, 6),
            "sequence_length": self.detector.seq_len if self.detector else None,
            "input_dimension": self.detector.input_dim if self.detector else None,
            "latent_dim": self.detector.latent_dim if self.detector else None,
            "threshold_strategy": self.detector.threshold_strategy if self.detector else None,
        }

        if timestep_errors is not None:
            meta_dict["timestep_errors"] = [round(float(e), 6) for e in timestep_errors]
        if window is not None:
            meta_dict["start_row_idx"] = window.start_row_idx
            meta_dict["end_row_idx"] = window.end_row_idx

        return LSTMPrediction(
            model_name="lstm_autoencoder",
            model_version=self.model_version or "1.0.0",
            dataset=self.dataset_name,
            prediction=prediction_label,
            is_anomaly=is_anomaly,
            raw_score=round(raw_mse, 6),
            raw_mse=round(raw_mse, 6),
            anomaly_score=anomaly_score,
            threshold=round(self.threshold, 6),
            processing_time_ms=round(elapsed_ms, 3),
            metadata=meta_dict,
        )

    def predict_single(self, sequence: Union[np.ndarray, List[List[float]]]) -> LSTMPrediction:
        """
        Evaluate a single sequence window (T, D) or (1, T, D) for anomalous temporal patterns.
        """
        if not self.is_loaded or self.detector is None:
            self.load()

        start_time = time.perf_counter()
        seq_arr = np.asarray(sequence, dtype=np.float32)

        # Validate sequence
        validated = validate_sequence_data(
            seq_arr,
            expected_seq_len=self.detector.seq_len,
            expected_feat_dim=self.detector.input_dim or seq_arr.shape[-1],
            allow_single_sequence=True,
        )

        raw_mse = float(self.detector.compute_reconstruction_error(validated)[0])
        anomaly_score = float(self.detector.compute_anomaly_scores(validated)[0])
        ts_errors = self.detector.compute_timestep_errors(validated)[0]

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return self._format_prediction(
            raw_mse=raw_mse,
            anomaly_score=anomaly_score,
            elapsed_ms=elapsed_ms,
            timestep_errors=ts_errors,
        )

    def predict_batch(self, sequences: Union[np.ndarray, List[Any]]) -> List[LSTMPrediction]:
        """
        High-throughput batch evaluation across multiple sequence windows (N, T, D).
        """
        if not self.is_loaded or self.detector is None:
            self.load()

        if len(sequences) == 0:
            return []

        start_time = time.perf_counter()
        seq_arr = np.asarray(sequences, dtype=np.float32)

        validated = validate_sequence_data(
            seq_arr,
            expected_seq_len=self.detector.seq_len,
            expected_feat_dim=self.detector.input_dim or seq_arr.shape[2],
            allow_single_sequence=False,
        )

        raw_mses = self.detector.compute_reconstruction_error(validated)
        anomaly_scores = self.detector.compute_anomaly_scores(validated)
        timestep_errors = self.detector.compute_timestep_errors(validated)

        total_elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        avg_elapsed_per_seq = total_elapsed_ms / max(1, len(validated))

        results = []
        for i in range(len(validated)):
            results.append(
                self._format_prediction(
                    raw_mse=float(raw_mses[i]),
                    anomaly_score=float(anomaly_scores[i]),
                    elapsed_ms=avg_elapsed_per_seq,
                    timestep_errors=timestep_errors[i],
                )
            )
        return results

    def predict_stream(self, records_df: pd.DataFrame, stride: int = 1) -> List[LSTMPrediction]:
        """
        Continuous stream inference:
        Takes a 2D tabular DataFrame of records, applies Phase 3 preprocessing,
        builds sliding windows with specified stride, and scores each sequence.
        """
        if not self.is_loaded or self.detector is None:
            self.load()

        if len(records_df) < self.detector.seq_len:
            logger.warning(
                f"Stream records ({len(records_df)}) < model sequence length ({self.detector.seq_len}). "
                f"Returning empty prediction list."
            )
            return []

        start_time = time.perf_counter()

        # 1. Preprocess raw records if pipeline available
        if self.pipeline is not None:
            X_proc = self.pipeline.transform(records_df)
        else:
            X_proc = records_df

        # 2. Build sliding sequences
        builder = SequenceBuilder(sequence_length=self.detector.seq_len, stride=stride)
        X_seq, _, _, windows = builder.build_sequences(X_proc)

        if len(X_seq) == 0:
            return []

        raw_mses = self.detector.compute_reconstruction_error(X_seq)
        anomaly_scores = self.detector.compute_anomaly_scores(X_seq)
        timestep_errors = self.detector.compute_timestep_errors(X_seq)

        total_elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        avg_elapsed = total_elapsed_ms / len(X_seq)

        results = []
        for i in range(len(X_seq)):
            results.append(
                self._format_prediction(
                    raw_mse=float(raw_mses[i]),
                    anomaly_score=float(anomaly_scores[i]),
                    elapsed_ms=avg_elapsed,
                    timestep_errors=timestep_errors[i],
                    window=windows[i] if i < len(windows) else None,
                )
            )
        return results
