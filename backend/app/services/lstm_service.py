import asyncio
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd

from backend.app.core.logging import logger
from backend.app.ml.inference.lstm_predictor import LSTMPredictor, LSTMPrediction


class LSTMService:
    """
    Decoupled Service Layer for Sequential LSTM Autoencoder Anomaly Detection.
    Manages cached predictor instances across datasets and provides synchronous
    and asynchronous sequence scoring interfaces.
    """

    def __init__(self, default_dataset: str = "synthetic"):
        self.default_dataset = default_dataset
        self.predictors: Dict[str, LSTMPredictor] = {}

    def get_predictor(self, dataset: Optional[str] = None) -> LSTMPredictor:
        """Retrieve or lazily initialize an LSTMPredictor instance for the requested dataset."""
        ds = (dataset or self.default_dataset).lower().strip()
        if ds not in self.predictors:
            logger.info(f"Initializing cached LSTMPredictor for dataset: '{ds}'")
            predictor = LSTMPredictor(dataset_name=ds)
            try:
                predictor.load()
            except Exception as e:
                logger.warning(f"Could not immediately load LSTM predictor for '{ds}': {e}")
            self.predictors[ds] = predictor
        return self.predictors[ds]

    def predict_sequence(
        self,
        sequence: Union[np.ndarray, List[List[float]]],
        dataset: Optional[str] = None,
    ) -> LSTMPrediction:
        """Synchronous inference on a single sequence window."""
        predictor = self.get_predictor(dataset)
        return predictor.predict_single(sequence)

    def predict_batch(
        self,
        sequences: Union[np.ndarray, List[Any]],
        dataset: Optional[str] = None,
    ) -> List[LSTMPrediction]:
        """Synchronous inference across a batch of 3D sequence windows."""
        predictor = self.get_predictor(dataset)
        return predictor.predict_batch(sequences)

    def predict_stream(
        self,
        records_df: pd.DataFrame,
        dataset: Optional[str] = None,
        stride: int = 1,
    ) -> List[LSTMPrediction]:
        """Synchronous inference on a continuous stream of tabular records."""
        predictor = self.get_predictor(dataset)
        return predictor.predict_stream(records_df, stride=stride)

    async def predict_sequence_async(
        self,
        sequence: Union[np.ndarray, List[List[float]]],
        dataset: Optional[str] = None,
    ) -> LSTMPrediction:
        """Asynchronous non-blocking inference on a single sequence window."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.predict_sequence, sequence, dataset)


lstm_service = LSTMService()
