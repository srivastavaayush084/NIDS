import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ml.registry.model_registry import model_registry
from backend.app.ml.models.random_forest import RandomForestClassifierModel
from backend.app.ml.models.isolation_forest import IsolationForestDetector
from backend.app.ml.models.autoencoder import AutoencoderDetector
from backend.app.ml.models.lstm_autoencoder import LSTMAutoencoderDetector
from backend.app.ml.ensemble.ensemble_detector import EnsembleDetector
from backend.app.ml.explainability.schemas import (
    ModelExplanation,
    EnsembleExplanation,
    ExplanationRequest,
)
from backend.app.ml.explainability.random_forest_explainer import RandomForestExplainer
from backend.app.ml.explainability.isolation_forest_explainer import IsolationForestExplainer
from backend.app.ml.explainability.autoencoder_explainer import AutoencoderExplainer
from backend.app.ml.explainability.lstm_explainer import LSTMAutoencoderExplainer
from backend.app.ml.explainability.ensemble_explainer import EnsembleExplainer


class ExplainerService:
    """
    Decoupled Service Layer for Explainable AI (XAI).
    Manages cached explainer engines across individual models and ensemble detectors,
    providing synchronous and asynchronous on-demand explanation endpoints.
    """

    def __init__(self, default_dataset: str = "synthetic"):
        self.default_dataset = default_dataset
        self.explainers: Dict[str, Any] = {}

    def get_explainer(self, model_name: str, dataset: Optional[str] = None) -> Any:
        """Retrieve or lazily initialize an explainer engine for the requested model and dataset."""
        ds = (dataset or self.default_dataset).lower().strip()
        m_name = model_name.lower().strip()
        cache_key = f"{ds}:{m_name}"

        if cache_key in self.explainers:
            return self.explainers[cache_key]

        if m_name == "random_forest":
            meta = model_registry.get_model("random_forest", dataset=ds)
            if not meta or not Path(meta.get("artifact_path", "")).exists():
                raise ValueError(f"Random Forest model is not available for dataset '{ds}'.")
            rf_model = RandomForestClassifierModel.load(meta["artifact_path"])
            explainer = RandomForestExplainer(
                model=rf_model,
                dataset_name=ds,
                feature_names=rf_model.feature_names_,
                top_k=settings.XAI_DEFAULT_TOP_K,
            )

        elif m_name == "isolation_forest":
            meta = model_registry.get_model("isolation_forest", dataset=ds)
            if not meta or not Path(meta.get("artifact_path", "")).exists():
                raise ValueError(f"Isolation Forest model is not available for dataset '{ds}'.")
            if_model = IsolationForestDetector.load(meta["artifact_path"])
            explainer = IsolationForestExplainer(
                model=if_model,
                dataset_name=ds,
                feature_names=if_model.feature_names_,
                top_k=settings.XAI_DEFAULT_TOP_K,
            )

        elif m_name == "autoencoder":
            meta = model_registry.get_model("autoencoder", dataset=ds)
            if not meta or not Path(meta.get("artifact_path", "")).exists():
                raise ValueError(f"Autoencoder model is not available for dataset '{ds}'.")
            ae_model = AutoencoderDetector.load(meta["artifact_path"])
            explainer = AutoencoderExplainer(
                model=ae_model,
                dataset_name=ds,
                feature_names=getattr(ae_model, "feature_names_", None),
                top_k=settings.XAI_DEFAULT_TOP_K,
            )

        elif m_name in ("lstm", "lstm_autoencoder"):
            meta = model_registry.get_model("lstm_autoencoder", dataset=ds)
            if not meta or not Path(meta.get("artifact_path", "")).exists():
                raise ValueError(f"LSTM Autoencoder model is not available for dataset '{ds}'.")
            lstm_model = LSTMAutoencoderDetector.load(meta["artifact_path"])
            explainer = LSTMAutoencoderExplainer(
                model=lstm_model,
                dataset_name=ds,
                feature_names=getattr(lstm_model, "feature_names_", None),
                top_k=settings.XAI_DEFAULT_TOP_K,
            )

        elif m_name == "ensemble":
            detector = EnsembleDetector.load(dataset_name=ds)
            explainer = EnsembleExplainer(
                ensemble_detector=detector,
                dataset_name=ds,
                top_k=settings.XAI_DEFAULT_TOP_K,
            )

        else:
            raise ValueError(f"Unsupported explainer model: '{model_name}'.")

        self.explainers[cache_key] = explainer
        logger.info(f"Initialized cached explainer for '{cache_key}'")
        return explainer

    def explain_record(
        self,
        model_name: str,
        record: Union[Dict[str, Any], pd.Series, np.ndarray, List[Any]],
        sequence_window: Optional[Union[np.ndarray, List[List[float]]]] = None,
        dataset: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> Union[ModelExplanation, EnsembleExplanation]:
        """Synchronously generate an explanation for a single record."""
        ds = dataset or self.default_dataset
        m_name = model_name.lower().strip()
        explainer = self.get_explainer(m_name, ds)

        if m_name == "ensemble":
            return explainer.explain_instance(record, sequence_window=sequence_window, top_k=top_k)
        elif m_name in ("lstm", "lstm_autoencoder"):
            sample = sequence_window if sequence_window is not None else record
            return explainer.explain_instance(sample, top_k=top_k)
        else:
            return explainer.explain_instance(record, top_k=top_k)

    async def explain_record_async(
        self,
        model_name: str,
        record: Union[Dict[str, Any], pd.Series, np.ndarray, List[Any]],
        sequence_window: Optional[Union[np.ndarray, List[List[float]]]] = None,
        dataset: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> Union[ModelExplanation, EnsembleExplanation]:
        """Asynchronously generate an explanation for a single record."""
        return await asyncio.to_thread(
            self.explain_record, model_name, record, sequence_window, dataset, top_k
        )


explainer_service = ExplainerService()
