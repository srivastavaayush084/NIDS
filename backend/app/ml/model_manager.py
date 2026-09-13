from typing import Dict, Any, Optional
from pathlib import Path
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ml.preprocessor import TrafficPreprocessor
from backend.app.ml.models.isolation_forest import IsolationForestDetector
from backend.app.ml.autoencoder import AutoencoderDetector
from backend.app.ml.lstm_detector import LSTMDetector
from backend.app.ml.baseline_rf import RandomForestBaseline
from backend.app.ml.registry.model_registry import model_registry


class ModelManager:
    """Manages ML model lifecycles, artifact loading, registry, and inference pipeline orchestration."""

    def __init__(self):
        self.preprocessor = TrafficPreprocessor()
        self.isolation_forest = IsolationForestDetector()
        self.autoencoder = AutoencoderDetector()
        self.lstm = LSTMDetector()
        self.random_forest = RandomForestBaseline()
        self.models_loaded: bool = False

    def load_models(self, dataset: str = "synthetic") -> None:
        """Load trained model weights from artifact storage directory."""
        models_dir = settings.MODELS_DIR
        logger.info(f"Checking model artifacts directory at: {models_dir}")
        if not models_dir.exists():
            models_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created model directory at: {models_dir}")

        # Check if Isolation Forest model is available in registry
        if_meta = model_registry.get_model("isolation_forest", dataset=dataset)
        if if_meta and Path(if_meta.get("artifact_path", "")).exists():
            try:
                self.isolation_forest = IsolationForestDetector.load(if_meta["artifact_path"])
                logger.info(f"Loaded Isolation Forest model from registry: {if_meta['artifact_path']}")
            except Exception as e:
                logger.warning(f"Could not load Isolation Forest model: {e}")

        # Check if Autoencoder model is available in registry
        ae_meta = model_registry.get_model("autoencoder", dataset=dataset)
        if ae_meta and Path(ae_meta.get("artifact_path", "")).exists():
            try:
                self.autoencoder = AutoencoderDetector.load(ae_meta["artifact_path"])
                logger.info(f"Loaded Autoencoder model from registry: {ae_meta['artifact_path']}")
            except Exception as e:
                logger.warning(f"Could not load Autoencoder model: {e}")

        # Check if LSTM Autoencoder model is available in registry
        lstm_meta = model_registry.get_model("lstm_autoencoder", dataset=dataset)
        if lstm_meta and Path(lstm_meta.get("artifact_path", "")).exists():
            try:
                self.lstm = LSTMDetector.load(lstm_meta["artifact_path"])
                logger.info(f"Loaded LSTM Autoencoder model from registry: {lstm_meta['artifact_path']}")
            except Exception as e:
                logger.warning(f"Could not load LSTM Autoencoder model: {e}")

        # Check if Random Forest model is available in registry
        rf_meta = model_registry.get_model("random_forest", dataset=dataset)
        if rf_meta and Path(rf_meta.get("artifact_path", "")).exists():
            try:
                self.random_forest = RandomForestBaseline.load(rf_meta["artifact_path"])
                logger.info(f"Loaded Random Forest model from registry: {rf_meta['artifact_path']}")
            except Exception as e:
                logger.warning(f"Could not load Random Forest model: {e}")

        self.models_loaded = (
            self.isolation_forest.is_trained
            or self.autoencoder.is_trained
            or self.lstm.is_trained
            or self.random_forest.is_trained
        )

    def get_model_status(self, dataset: Optional[str] = None) -> Dict[str, Any]:
        """Returns registration and training status across all pipeline models."""
        ds = dataset or "synthetic"
        if_meta = model_registry.get_model("isolation_forest", dataset=ds)
        is_if_trained = bool(if_meta is not None or self.isolation_forest.is_trained)

        ae_meta = model_registry.get_model("autoencoder", dataset=ds)
        is_ae_trained = bool(ae_meta is not None or self.autoencoder.is_trained)

        lstm_meta = model_registry.get_model("lstm_autoencoder", dataset=ds)
        is_lstm_trained = bool(lstm_meta is not None or self.lstm.is_trained)

        rf_meta = model_registry.get_model("random_forest", dataset=ds)
        is_rf_trained = bool(rf_meta is not None or self.random_forest.is_trained)

        return {
            "isolation_forest": {
                "name": "Isolation Forest (Unsupervised)",
                "is_trained": is_if_trained,
                "type": "Unsupervised",
                "version": if_meta.get("version") if if_meta else None,
                "artifact_path": if_meta.get("artifact_path") if if_meta else None,
            },
            "autoencoder": {
                "name": "Autoencoder (Deep Learning)",
                "is_trained": is_ae_trained,
                "type": "Deep Learning / Reconstruction",
                "version": ae_meta.get("version") if ae_meta else None,
                "artifact_path": ae_meta.get("artifact_path") if ae_meta else None,
            },
            "lstm": {
                "name": "LSTM Network (Temporal / Sequential)",
                "is_trained": is_lstm_trained,
                "type": "Recurrent / Sequential Reconstruction",
                "version": lstm_meta.get("version") if lstm_meta else None,
                "artifact_path": lstm_meta.get("artifact_path") if lstm_meta else None,
            },
            "random_forest": {
                "name": "Random Forest (Baseline Comparison)",
                "is_trained": is_rf_trained,
                "type": "Supervised Baseline",
                "version": rf_meta.get("version") if rf_meta else None,
                "artifact_path": rf_meta.get("artifact_path") if rf_meta else None,
            }
        }


model_manager = ModelManager()
