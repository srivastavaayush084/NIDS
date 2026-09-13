import asyncio
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd

from backend.app.core.logging import logger
from backend.app.ml.ensemble.ensemble_detector import EnsembleDetector
from backend.app.ml.ensemble.schemas import EnsemblePrediction


class EnsembleService:
    """
    Decoupled Service Layer for Ensemble Detection and Risk Scoring Engine.
    Manages cached EnsembleDetector instances across datasets and provides
    synchronous and asynchronous multi-model inference interfaces.
    """

    def __init__(self, default_dataset: str = "synthetic"):
        self.default_dataset = default_dataset
        self.detectors: Dict[str, EnsembleDetector] = {}

    def get_detector(self, dataset: Optional[str] = None) -> EnsembleDetector:
        """Retrieve or lazily initialize an EnsembleDetector instance for the requested dataset."""
        ds = (dataset or self.default_dataset).lower().strip()
        if ds not in self.detectors:
            logger.info(f"Initializing cached EnsembleDetector for dataset: '{ds}'")
            try:
                detector = EnsembleDetector.load(dataset_name=ds)
            except Exception as e:
                logger.warning(f"Could not load EnsembleDetector for '{ds}': {e}. Using uninitialized detector.")
                detector = EnsembleDetector(dataset_name=ds)
            self.detectors[ds] = detector
        return self.detectors[ds]

    def predict_flow(
        self,
        record: Union[Dict[str, Any], pd.Series, np.ndarray],
        sequence_window: Optional[Union[np.ndarray, List[List[float]]]] = None,
        dataset: Optional[str] = None,
    ) -> EnsemblePrediction:
        """Synchronous ensemble inference on a single flow record."""
        detector = self.get_detector(dataset)
        return detector.predict_single(record, sequence_window=sequence_window)

    def predict_batch(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        dataset: Optional[str] = None,
    ) -> List[EnsemblePrediction]:
        """Synchronous batch ensemble inference across multiple flow records."""
        detector = self.get_detector(dataset)
        _, _, pred_objs = detector.predict_batch(X)
        return pred_objs

    async def predict_flow_async(
        self,
        record: Union[Dict[str, Any], pd.Series, np.ndarray],
        sequence_window: Optional[Union[np.ndarray, List[List[float]]]] = None,
        dataset: Optional[str] = None,
    ) -> EnsemblePrediction:
        """Asynchronous non-blocking ensemble inference on a single flow record."""
        return await asyncio.to_thread(self.predict_flow, record, sequence_window, dataset)

    async def predict_batch_async(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        dataset: Optional[str] = None,
    ) -> List[EnsemblePrediction]:
        """Asynchronous non-blocking batch ensemble inference."""
        return await asyncio.to_thread(self.predict_batch, X, dataset)


ensemble_service = EnsembleService()
