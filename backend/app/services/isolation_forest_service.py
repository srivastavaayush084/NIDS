from typing import Any, Dict, List, Optional, Union
import pandas as pd
from backend.app.core.logging import logger
from backend.app.ml.inference.isolation_forest_predictor import (
    IsolationForestPredictor,
    IsolationForestPrediction,
)
from backend.app.ml.registry.model_registry import model_registry


class IsolationForestService:
    """
    Application Service Layer for Isolation Forest Anomaly Detection.
    Provides decoupled asynchronous and synchronous methods for single-flow inference,
    batch scoring, and model telemetry without embedding ML logic in API route handlers.
    """

    def __init__(self, default_dataset: str = "synthetic"):
        self.default_dataset = default_dataset
        self.predictors: Dict[str, IsolationForestPredictor] = {}

    def get_predictor(self, dataset: Optional[str] = None) -> IsolationForestPredictor:
        """Get or lazily load the predictor for a given dataset."""
        ds = (dataset or self.default_dataset).lower().strip()
        if ds not in self.predictors:
            predictor = IsolationForestPredictor(dataset_name=ds)
            predictor.load()
            self.predictors[ds] = predictor
        return self.predictors[ds]

    def predict_flow(
        self,
        flow_data: Union[Dict[str, Any], pd.Series, pd.DataFrame],
        dataset: Optional[str] = None,
    ) -> IsolationForestPrediction:
        """
        Synchronous single-record prediction.
        """
        predictor = self.get_predictor(dataset)
        return predictor.predict_single(flow_data)

    async def predict_flow_async(
        self,
        flow_data: Union[Dict[str, Any], pd.Series, pd.DataFrame],
        dataset: Optional[str] = None,
    ) -> IsolationForestPrediction:
        """
        Asynchronous single-record prediction for FastAPI endpoints and event streams.
        """
        return self.predict_flow(flow_data, dataset=dataset)

    def predict_batch_flows(
        self,
        flows_df: pd.DataFrame,
        dataset: Optional[str] = None,
    ) -> List[IsolationForestPrediction]:
        """
        High-throughput batch flow anomaly scoring.
        """
        predictor = self.get_predictor(dataset)
        return predictor.predict_batch(flows_df)

    def get_model_info(self, dataset: Optional[str] = None) -> Dict[str, Any]:
        """
        Return model metadata and status from the Model Registry.
        """
        ds = (dataset or self.default_dataset).lower().strip()
        meta = model_registry.get_model("isolation_forest", dataset=ds)
        if meta:
            return meta
        return {
            "model_name": "isolation_forest",
            "dataset": ds,
            "status": "not_loaded_or_unregistered",
            "is_active": False,
        }


isolation_forest_service = IsolationForestService()
