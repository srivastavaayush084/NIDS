from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ml.data.preprocessing.pipeline import NetworkDataPipeline


class TrafficPreprocessor:
    """
    Inference-ready Traffic Preprocessor.
    Wraps the NetworkDataPipeline to transform raw network flow metrics
    into standardized, leak-free feature vectors for real-time model inference.
    """

    def __init__(self, pipeline: Optional[NetworkDataPipeline] = None, dataset_name: str = "generic"):
        self.pipeline = pipeline
        self.dataset_name = dataset_name
        self.feature_columns: List[str] = [
            "duration", "src_bytes", "dst_bytes", "packet_count"
        ]
        self.is_fitted: bool = pipeline.is_fitted if pipeline else False

    def load_pipeline(self, artifact_dir: Optional[Union[str, Path]] = None, dataset_name: Optional[str] = None) -> "TrafficPreprocessor":
        """Load fitted NetworkDataPipeline from artifact storage."""
        ds_name = dataset_name or self.dataset_name
        dir_path = Path(artifact_dir) if artifact_dir else settings.PREPROCESSING_DIR / ds_name
        self.pipeline = NetworkDataPipeline.load(dir_path)
        self.is_fitted = True
        self.feature_columns = self.pipeline.selected_features_
        logger.info(f"Loaded TrafficPreprocessor pipeline from {dir_path} ({len(self.feature_columns)} features).")
        return self

    def fit(self, df: pd.DataFrame, y: Optional[pd.Series] = None) -> "TrafficPreprocessor":
        """Fit internal pipeline on incoming DataFrame."""
        logger.info(f"Fitting TrafficPreprocessor on {len(df)} samples...")
        if self.pipeline is None:
            self.pipeline = NetworkDataPipeline(dataset_name=self.dataset_name)
        self.pipeline.fit(df, y=y)
        self.is_fitted = True
        self.feature_columns = self.pipeline.selected_features_
        return self

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        """Transform network features into model input numpy array."""
        if self.pipeline and self.pipeline.is_fitted:
            return self.pipeline.transform_to_numpy(df)

        # Fallback for uninitialized models during baseline testing
        logger.debug("Preprocessor pipeline not fitted; using raw numeric columns fallback.")
        numeric_cols = [c for c in self.feature_columns if c in df.columns]
        if numeric_cols:
            return df[numeric_cols].fillna(0).to_numpy(dtype=np.float32)
        return np.zeros((len(df), len(self.feature_columns)), dtype=np.float32)

    def fit_transform(self, df: pd.DataFrame, y: Optional[pd.Series] = None) -> np.ndarray:
        return self.fit(df, y).transform(df)
