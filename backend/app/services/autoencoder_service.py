from typing import Any, Dict, List, Optional, Union
import pandas as pd
from backend.app.core.logging import logger
from backend.app.ml.inference.autoencoder_predictor import (
    AutoencoderPredictor,
    AutoencoderPrediction,
)
from backend.app.ml.registry.model_registry import model_registry


class AutoencoderService:
    """
    Application Service Layer for Deep Learning Autoencoder Anomaly Detection.
    Provides decoupled asynchronous and synchronous methods for single-flow inference,
    batch reconstruction scoring, and model status telemetry without placing ML logic in API routes.
    """

    def __init__(self, default_dataset: str = "synthetic"):
        self.default_dataset = default_dataset
        self.predictors: Dict[str, AutoencoderPredictor] = {}

    def get_predictor(self, dataset: Optional[str] = None) -> AutoencoderPredictor:
        """Get or lazily load the Autoencoder predictor for a given dataset."""
        ds = (dataset or self.default_dataset).lower().strip()
        if ds not in self.predictors:
            predictor = AutoencoderPredictor(dataset_name=ds)
            predictor.load()
            self.predictors[ds] = predictor
        return self.predictors[ds]

    def predict_flow(
        self,
        flow_data: Union[Dict[str, Any], pd.Series, pd.DataFrame],
        dataset: Optional[str] = None,
    ) -> AutoencoderPrediction:
        """
        Synchronous single-record prediction using Deep Learning Autoencoder.
        """
        predictor = self.get_predictor(dataset)
        return predictor.predict_single(flow_data)

    async def predict_flow_async(
        self,
        flow_data: Union[Dict[str, Any], pd.Series, pd.DataFrame],
        dataset: Optional[str] = None,
    ) -> AutoencoderPrediction:
        """
        Asynchronous single-record prediction for FastAPI endpoints and event streams.
        """
        return self.predict_flow(flow_data, dataset=dataset)

    def predict_batch_flows(
        self,
        flows_df: pd.DataFrame,
        dataset: Optional[str] = None,
    ) -> List[AutoencoderPrediction]:
        """
        High-throughput batch flow reconstruction scoring.
        """
        predictor = self.get_predictor(dataset)
        return predictor.predict_batch(flows_df)

    def get_model_info(self, dataset: Optional[str] = None) -> Dict[str, Any]:
        """
        Return Autoencoder model metadata and status from the Model Registry.
        """
        ds = (dataset or self.default_dataset).lower().strip()
        meta = model_registry.get_model("autoencoder", dataset=ds)
        if meta:
            return meta
        return {
            "model_name": "autoencoder",
            "dataset": ds,
            "status": "not_loaded_or_unregistered",
            "is_active": False,
        }


autoencoder_service = AutoencoderService()
