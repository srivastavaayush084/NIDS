from typing import Any, Dict, List, Optional, Set, Union
import numpy as np
import pandas as pd
from backend.app.core.logging import logger


class DataCleaner:
    """
    Data cleaning module for network traffic logs and intrusion datasets.
    Handles column normalization, missing values, infinite rates, duplicates,
    and invalid numerical/categorical entries with explicit audit logging.
    """

    def __init__(
        self,
        drop_duplicates: bool = True,
        numeric_impute_strategy: str = "median",  # "median", "mean", "zero"
        categorical_impute_value: str = "unknown",
        handle_infinities: bool = True,
        drop_columns: Optional[List[str]] = None,
    ):
        self.drop_duplicates = drop_duplicates
        self.numeric_impute_strategy = numeric_impute_strategy
        self.categorical_impute_value = categorical_impute_value
        self.handle_infinities = handle_infinities
        self.drop_columns: List[str] = drop_columns or []
        
        self.numeric_fill_values: Dict[str, float] = {}
        self.numeric_clip_bounds: Dict[str, float] = {}
        self.categorical_columns_: List[str] = []
        self.numerical_columns_: List[str] = []
        self.is_fitted: bool = False
        self.cleaning_stats: Dict[str, Any] = {}

    def _normalize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Strip whitespace and normalize column names."""
        df.columns = [c.strip() for c in df.columns]
        return df

    def fit(self, df: pd.DataFrame, y: Optional[pd.Series] = None) -> "DataCleaner":
        """
        Fit cleaning statistics (medians, means, bounds) ONLY on training data.
        """
        logger.info(f"Fitting DataCleaner on {len(df)} samples...")
        df_clean = df.copy()
        df_clean = self._normalize_column_names(df_clean)

        # Detect numerical and categorical columns
        self.numerical_columns_ = df_clean.select_dtypes(include=[np.number]).columns.tolist()
        self.categorical_columns_ = df_clean.select_dtypes(exclude=[np.number]).columns.tolist()

        # Compute numerical imputation values and finite bounds
        self.numeric_fill_values = {}
        self.numeric_clip_bounds = {}

        for col in self.numerical_columns_:
            series = df_clean[col].replace([np.inf, -np.inf], np.nan)
            if self.numeric_impute_strategy == "median":
                fill_val = float(series.median()) if not series.dropna().empty else 0.0
            elif self.numeric_impute_strategy == "mean":
                fill_val = float(series.mean()) if not series.dropna().empty else 0.0
            else:  # "zero"
                fill_val = 0.0
            self.numeric_fill_values[col] = 0.0 if np.isnan(fill_val) else fill_val

            # Max finite value for clipping infinities if encountered
            valid_series = series.dropna()
            if not valid_series.empty:
                self.numeric_clip_bounds[col] = float(valid_series.max())
            else:
                self.numeric_clip_bounds[col] = 0.0

        self.is_fitted = True
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply learned cleaning rules to transform dataset without data leakage.
        """
        initial_rows = len(df)
        initial_cols = len(df.columns)
        df_clean = df.copy()
        df_clean = self._normalize_column_names(df_clean)

        # 1. Drop configured unnecessary/leakage columns
        cols_to_drop = [c for c in self.drop_columns if c in df_clean.columns]
        if cols_to_drop:
            df_clean = df_clean.drop(columns=cols_to_drop)

        # 2. Deduplicate if enabled (only when transforming in training/offline ingestion)
        duplicates_removed = 0
        if self.drop_duplicates:
            before_dup = len(df_clean)
            df_clean = df_clean.drop_duplicates()
            duplicates_removed = before_dup - len(df_clean)

        # 3. Handle categorical columns (whitespace, lowercase, fillna)
        cat_cols = [c for c in self.categorical_columns_ if c in df_clean.columns]
        for col in cat_cols:
            df_clean[col] = (
                df_clean[col]
                .astype(str)
                .str.strip()
                .replace({"nan": self.categorical_impute_value, "None": self.categorical_impute_value, "": self.categorical_impute_value})
                .fillna(self.categorical_impute_value)
            )

        # 4. Handle numerical columns (Infinities and NaNs)
        inf_handled = 0
        nan_handled = 0
        num_cols = [c for c in self.numerical_columns_ if c in df_clean.columns]
        for col in num_cols:
            series = pd.to_numeric(df_clean[col], errors="coerce")
            
            # Count infinities
            inf_mask = np.isinf(series)
            inf_handled += int(inf_mask.sum())
            
            # Replace infinities with clip bound or NaN
            if self.handle_infinities and col in self.numeric_clip_bounds:
                series = series.replace([np.inf, -np.inf], self.numeric_clip_bounds[col])
            else:
                series = series.replace([np.inf, -np.inf], np.nan)

            # Impute NaNs
            nan_count = int(series.isna().sum())
            nan_handled += nan_count
            fill_val = self.numeric_fill_values.get(col, 0.0)
            series = series.fillna(fill_val)

            df_clean[col] = series

        self.cleaning_stats = {
            "initial_rows": initial_rows,
            "final_rows": len(df_clean),
            "duplicates_removed": duplicates_removed,
            "infinities_handled": inf_handled,
            "nans_imputed": nan_handled,
            "initial_columns": initial_cols,
            "final_columns": len(df_clean.columns),
            "columns_dropped": cols_to_drop,
        }

        logger.info(
            f"Data Cleaning Completed: Initial rows={initial_rows}, Final rows={len(df_clean)}, "
            f"Duplicates removed={duplicates_removed}, Inf handled={inf_handled}, NaN imputed={nan_handled}"
        )
        return df_clean

    def fit_transform(self, df: pd.DataFrame, y: Optional[pd.Series] = None) -> pd.DataFrame:
        """Fit on DataFrame and transform."""
        return self.fit(df, y).transform(df)
