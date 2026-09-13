from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ml.data.preprocessing.cleaner import DataCleaner
from backend.app.ml.data.preprocessing.encoder import CategoricalEncoder
from backend.app.ml.data.preprocessing.scaler import NumericalScaler
from backend.app.ml.data.preprocessing.feature_engineer import NetworkFeatureEngineer
from backend.app.ml.data.preprocessing.feature_selector import FeatureSelector
from backend.app.ml.data.utils.data_utils import (
    ensure_dir,
    save_artifact,
    load_artifact,
    save_metadata,
    load_metadata,
)


class NetworkDataPipeline:
    """
    Unified end-to-end Preprocessing and Feature Engineering Pipeline.
    Encapsulates data cleaning, domain feature extraction, categorical encoding,
    numerical scaling, and feature selection into a single reusable object.
    
    Guarantees leak-free fitting on training data and deterministic inference transformations.
    """

    def __init__(
        self,
        dataset_name: str = "generic",
        cleaner: Optional[DataCleaner] = None,
        feature_engineer: Optional[NetworkFeatureEngineer] = None,
        encoder: Optional[CategoricalEncoder] = None,
        scaler: Optional[NumericalScaler] = None,
        feature_selector: Optional[FeatureSelector] = None,
        scaling_strategy: str = "standard",
        encoding_strategy: str = "onehot",
        selection_strategy: str = "variance",
        variance_threshold: float = 0.0,
        correlation_threshold: float = 0.98,
        k_features: Optional[int] = None,
        drop_duplicates: bool = True,
        enable_feature_engineering: bool = True,
    ):
        self.dataset_name = dataset_name
        self.scaling_strategy = scaling_strategy
        self.encoding_strategy = encoding_strategy
        self.selection_strategy = selection_strategy
        self.variance_threshold = variance_threshold
        self.correlation_threshold = correlation_threshold
        self.k_features = k_features
        self.drop_duplicates = drop_duplicates
        self.enable_feature_engineering = enable_feature_engineering

        # Initialize sub-components if not supplied
        self.cleaner = cleaner or DataCleaner(
            drop_duplicates=drop_duplicates,
            handle_infinities=True,
        )
        self.feature_engineer = feature_engineer or NetworkFeatureEngineer(
            enable_engineering=enable_feature_engineering
        )
        self.encoder = encoder or CategoricalEncoder(
            strategy=encoding_strategy,
            sparse_output=False,
        )
        self.scaler = scaler or NumericalScaler(
            strategy=scaling_strategy
        )
        self.feature_selector = feature_selector or FeatureSelector(
            strategy=selection_strategy,
            variance_threshold=variance_threshold,
            correlation_threshold=correlation_threshold,
            k_features=k_features,
        )

        self.is_fitted: bool = False
        self.selected_features_: List[str] = []
        self.input_feature_count_: int = 0
        self.output_feature_count_: int = 0
        self.fitted_at_: Optional[str] = None

    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> "NetworkDataPipeline":
        """
        Fit all pipeline stages sequentially ONLY on training data X (and optional target y).
        """
        logger.info(f"Fitting NetworkDataPipeline for dataset '{self.dataset_name}' on {len(X)} samples...")
        self.input_feature_count_ = len(X.columns)

        # 1. Cleaner Fit & Transform (on training data)
        X_clean = self.cleaner.fit_transform(X)

        # 2. Feature Engineer Fit & Transform
        X_eng = self.feature_engineer.fit_transform(X_clean)

        # 3. Categorical Encoder Fit & Transform
        X_enc = self.encoder.fit_transform(X_eng)

        # 4. Numerical Scaler Fit & Transform
        X_scaled = self.scaler.fit_transform(X_enc)

        # 5. Feature Selector Fit & Transform
        X_selected = self.feature_selector.fit_transform(X_scaled, y=y)

        self.selected_features_ = list(X_selected.columns)
        self.output_feature_count_ = len(self.selected_features_)
        self.is_fitted = True
        self.fitted_at_ = datetime.now(timezone.utc).isoformat()

        logger.info(
            f"NetworkDataPipeline fitted successfully: "
            f"Input features={self.input_feature_count_} -> Output features={self.output_feature_count_}"
        )
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Apply learned pipeline transformations sequentially to validation, test, or inference data.
        Does NOT alter learned parameters or fit on new data.
        """
        if not self.is_fitted:
            raise RuntimeError("NetworkDataPipeline must be fitted before transforming data.")

        # Clean (inference mode - does not drop duplicates from live stream)
        cleaner_no_dup = DataCleaner(
            drop_duplicates=False,
            numeric_impute_strategy=self.cleaner.numeric_impute_strategy,
            categorical_impute_value=self.cleaner.categorical_impute_value,
            handle_infinities=self.cleaner.handle_infinities,
            drop_columns=self.cleaner.drop_columns,
        )
        cleaner_no_dup.numerical_columns_ = self.cleaner.numerical_columns_
        cleaner_no_dup.categorical_columns_ = self.cleaner.categorical_columns_
        cleaner_no_dup.numeric_fill_values = self.cleaner.numeric_fill_values
        cleaner_no_dup.numeric_clip_bounds = self.cleaner.numeric_clip_bounds
        cleaner_no_dup.is_fitted = True

        X_clean = cleaner_no_dup.transform(X)
        X_eng = self.feature_engineer.transform(X_clean)
        X_enc = self.encoder.transform(X_eng)
        X_scaled = self.scaler.transform(X_enc)
        X_selected = self.feature_selector.transform(X_scaled)

        return X_selected

    def fit_transform(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> pd.DataFrame:
        """Fit pipeline on X and return transformed DataFrame."""
        return self.fit(X, y).transform(X)

    def transform_to_numpy(self, X: pd.DataFrame) -> np.ndarray:
        """Transform DataFrame and return contiguous float32 NumPy array for ML models."""
        df_trans = self.transform(X)
        return df_trans.to_numpy(dtype=np.float32)

    def save(self, artifact_dir: Optional[Union[str, Path]] = None) -> Path:
        """
        Serialize all pipeline artifacts, components, and metadata to disk.
        """
        if not self.is_fitted:
            raise RuntimeError("Cannot save an unfitted pipeline.")

        out_dir = Path(artifact_dir) if artifact_dir else settings.PREPROCESSING_DIR / self.dataset_name
        ensure_dir(out_dir)

        # Save main pipeline object
        save_artifact(self, out_dir / "pipeline.joblib")

        # Save individual sub-components for modular inspection
        save_artifact(self.scaler, out_dir / "scaler.joblib")
        save_artifact(self.encoder, out_dir / "encoder.joblib")
        save_artifact(self.feature_selector, out_dir / "feature_selector.joblib")

        # Save metadata
        metadata = {
            "dataset_name": self.dataset_name,
            "pipeline_version": "1.0.0",
            "created_at": self.fitted_at_,
            "input_feature_count": self.input_feature_count_,
            "output_feature_count": self.output_feature_count_,
            "selected_features": self.selected_features_,
            "scaling_strategy": self.scaling_strategy,
            "encoding_strategy": self.encoding_strategy,
            "selection_strategy": self.selection_strategy,
            "variance_threshold": self.variance_threshold,
            "correlation_threshold": self.correlation_threshold,
            "enable_feature_engineering": self.enable_feature_engineering,
        }
        save_metadata(metadata, out_dir / "metadata.json")
        save_metadata({"features": self.selected_features_}, out_dir / "selected_features.json")

        logger.info(f"All preprocessing artifacts successfully saved to: {out_dir}")
        return out_dir

    @classmethod
    def load(cls, artifact_dir: Union[str, Path]) -> "NetworkDataPipeline":
        """
        Load a serialized NetworkDataPipeline from disk.
        """
        path = Path(artifact_dir)
        pipeline_file = path / "pipeline.joblib" if path.is_dir() else path
        if not pipeline_file.exists():
            raise FileNotFoundError(f"Pipeline artifact not found at: {pipeline_file}")

        pipeline = load_artifact(pipeline_file)
        logger.info(
            f"Loaded NetworkDataPipeline for dataset '{pipeline.dataset_name}' "
            f"({len(pipeline.selected_features_)} features)"
        )
        return pipeline
