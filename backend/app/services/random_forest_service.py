import asyncio
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd

from backend.app.core.logging import logger
from backend.app.ml.inference.random_forest_predictor import (
    RandomForestPredictor,
    RandomForestPrediction,
)


class RandomForestService:
    """
    Decoupled Service Layer for Supervised Random Forest Baseline Classifier.
    Manages cached predictor instances across datasets and provides synchronous
    and asynchronous flow classification interfaces.
    """

    def __init__(self, default_dataset: str = "synthetic"):
        self.default_dataset = default_dataset
        self.predictors: Dict[str, RandomForestPredictor] = {}

    def get_predictor(self, dataset: Optional[str] = None) -> RandomForestPredictor:
        """Retrieve or lazily initialize a RandomForestPredictor instance for the requested dataset."""
        ds = (dataset or self.default_dataset).lower().strip()
        if ds not in self.predictors:
            logger.info(f"Initializing cached RandomForestPredictor for dataset: '{ds}'")
            predictor = RandomForestPredictor(dataset_name=ds)
            try:
                predictor.load()
            except Exception as e:
                logger.warning(f"Could not immediately load Random Forest predictor for '{ds}': {e}")
            self.predictors[ds] = predictor
        return self.predictors[ds]

    def predict_flow(
        self,
        record: Union[Dict[str, Any], pd.Series],
        dataset: Optional[str] = None,
    ) -> RandomForestPrediction:
        """Synchronous inference on a single flow record."""
        predictor = self.get_predictor(dataset)
        return predictor.predict_single(record)

    def predict_batch(
        self,
        df: pd.DataFrame,
        dataset: Optional[str] = None,
    ) -> List[RandomForestPrediction]:
        """Synchronous batch inference across multiple flow records."""
        predictor = self.get_predictor(dataset)
        return predictor.predict_batch(df)

    async def predict_flow_async(
        self,
        record: Union[Dict[str, Any], pd.Series],
        dataset: Optional[str] = None,
    ) -> RandomForestPrediction:
        """Asynchronous non-blocking inference on a single flow record."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.predict_flow, record, dataset)


random_forest_service = RandomForestService()
