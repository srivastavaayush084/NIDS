from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ml.data.utils.data_utils import load_dataframe


class BaseDatasetLoader(ABC):
    """
    Abstract base class for network intrusion dataset ingestion loaders.
    Provides standard interfaces for loading, column classification,
    label normalization, and target leakage prevention.
    """

    def __init__(self, raw_dir: Optional[Union[str, Path]] = None):
        if raw_dir:
            self.raw_dir = Path(raw_dir)
        else:
            self.raw_dir = settings.DATA_DIR / "raw" / self.dataset_name

    @property
    @abstractmethod
    def dataset_name(self) -> str:
        """Name identifier of the dataset (e.g., 'nsl_kdd', 'cicids2017', 'unsw_nb15', 'synthetic')."""
        pass

    @property
    @abstractmethod
    def target_column(self) -> str:
        """Name of the raw ground-truth attack label column."""
        pass

    @property
    @abstractmethod
    def categorical_columns(self) -> List[str]:
        """List of categorical feature names."""
        pass

    @property
    @abstractmethod
    def numerical_columns(self) -> List[str]:
        """List of numerical feature names."""
        pass

    @property
    def drop_columns(self) -> List[str]:
        """List of metadata, identifier, or timestamp columns that must be dropped to prevent leakage."""
        return []

    @abstractmethod
    def get_attack_category_mapping(self) -> Dict[str, str]:
        """Dictionary mapping fine-grained attack labels to broader attack families/categories."""
        pass

    @abstractmethod
    def load(self, file_path: Optional[Union[str, Path]] = None, **kwargs) -> pd.DataFrame:
        """Ingest and load the raw dataset files into a consolidated pandas DataFrame."""
        pass

    def extract_labels(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.Series, pd.Series, pd.Series]:
        """
        Safely extract and separate ground-truth labels from feature matrix X.
        Prevents target leakage into ML feature sets.

        Returns:
            X (pd.DataFrame): Feature matrix without labels or leakage metadata.
            y_original (pd.Series): Original raw attack labels.
            y_category (pd.Series): Mapped high-level attack category (e.g., DoS, Probe, Benign).
            y_binary (pd.Series): Binary label (0 = Normal/Benign, 1 = Attack).
        """
        df_copy = df.copy()

        # Identify label column
        target_col = self.target_column
        if target_col not in df_copy.columns:
            # Fallback search for common label column variants (case-insensitive)
            col_lower_map = {c.lower().strip(): c for c in df_copy.columns}
            for candidate in ("label", "attack", "class", "attack_cat", "attack_category"):
                if candidate in col_lower_map:
                    target_col = col_lower_map[candidate]
                    break
            else:
                raise ValueError(
                    f"Target label column '{self.target_column}' not found in dataset columns: "
                    f"{df_copy.columns.tolist()}"
                )

        y_raw = df_copy[target_col].astype(str).str.strip().str.lower()

        # 1. Original labels (cleaned whitespace)
        y_original = df_copy[target_col].astype(str).str.strip()

        # 2. Attack category mapping
        mapping = {k.lower().strip(): v.lower().strip() for k, v in self.get_attack_category_mapping().items()}
        
        def map_category(val: str) -> str:
            val_clean = val.lower().strip()
            if val_clean in mapping:
                return mapping[val_clean]
            val_no_dot = val_clean.rstrip(".")
            if val_no_dot in mapping:
                return mapping[val_no_dot]
            if val_clean in ("normal", "benign", "0", "false"):
                return "normal"
            return "other_attack"

        y_category = y_raw.map(map_category)

        # 3. Binary label (0 = Normal/Benign, 1 = Attack)
        is_normal = y_raw.isin(["normal", "benign", "0", "false"])
        y_binary = (~is_normal).astype(int)

        # Separate feature matrix X (drop target column and any secondary label / leakage columns)
        drop_set = set([target_col] + self.drop_columns)
        for extra in ["attack_cat", "difficulty_level", "binary_label", "attack_category", "label"]:
            if extra in df_copy.columns:
                drop_set.add(extra)

        X = df_copy.drop(columns=[c for c in drop_set if c in df_copy.columns])

        logger.info(
            f"Separated features and labels for '{self.dataset_name}': X shape={X.shape}, "
            f"Normal={int((y_binary == 0).sum())}, Attack={int((y_binary == 1).sum())}"
        )
        return X, y_original, y_category, y_binary
