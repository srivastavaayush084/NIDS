from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
from backend.app.core.logging import logger


class NumericalScaler:
    """
    Numerical Feature Scaler for Network Anomaly Detection.
    Provides standard, min-max, and robust scaling options.
    Strictly fitted on training data and reusable during inference.
    """

    def __init__(
        self,
        strategy: str = "standard",  # "standard", "minmax", "robust", "none"
        numerical_columns: Optional[List[str]] = None,
    ):
        self.strategy = strategy.lower()
        self.numerical_columns: Optional[List[str]] = numerical_columns
        self.scaler: Optional[Union[StandardScaler, MinMaxScaler, RobustScaler]] = None
        self.fitted_numerical_columns_: List[str] = []
        self.is_fitted: bool = False

    def fit(self, df: pd.DataFrame, y: Optional[pd.Series] = None) -> "NumericalScaler":
        """
        Fit numerical scaler ONLY on training data.
        """
        if self.strategy == "none":
            self.is_fitted = True
            self.fitted_numerical_columns_ = []
            return self

        if self.numerical_columns is not None:
            self.fitted_numerical_columns_ = [c for c in self.numerical_columns if c in df.columns]
        else:
            self.fitted_numerical_columns_ = df.select_dtypes(include=[np.number]).columns.tolist()

        if not self.fitted_numerical_columns_:
            logger.info("No numerical columns detected for scaling.")
            self.is_fitted = True
            return self

        logger.info(f"Fitting {self.strategy.upper()} NumericalScaler on {len(self.fitted_numerical_columns_)} columns...")

        if self.strategy == "standard":
            self.scaler = StandardScaler()
        elif self.strategy == "minmax":
            self.scaler = MinMaxScaler()
        elif self.strategy == "robust":
            self.scaler = RobustScaler()
        else:
            raise ValueError(f"Unsupported scaling strategy: '{self.strategy}'. Choose 'standard', 'minmax', 'robust', or 'none'.")

        num_df = df[self.fitted_numerical_columns_].fillna(0.0).astype(np.float32)
        self.scaler.fit(num_df)
        self.is_fitted = True
        logger.info(f"NumericalScaler ({self.strategy}) fitted successfully.")
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform numerical columns in DataFrame using fitted scaler.
        """
        if not self.is_fitted:
            raise RuntimeError("NumericalScaler must be fitted before transforming data.")

        if self.strategy == "none" or not self.fitted_numerical_columns_ or self.scaler is None:
            return df.copy()

        df_copy = df.copy()
        
        # Extract numerical columns that were fitted
        present_cols = [c for c in self.fitted_numerical_columns_ if c in df_copy.columns]
        
        if len(present_cols) == len(self.fitted_numerical_columns_):
            num_data = df_copy[self.fitted_numerical_columns_].fillna(0.0).astype(np.float32)
            scaled_arr = self.scaler.transform(num_data)
            scaled_df = pd.DataFrame(scaled_arr, columns=self.fitted_numerical_columns_, index=df_copy.index)
            
            # Replace columns with scaled values
            for col in self.fitted_numerical_columns_:
                df_copy[col] = scaled_df[col]
        else:
            # Handle missing columns by creating complete DataFrame with zero defaults
            full_data = pd.DataFrame(0.0, index=df_copy.index, columns=self.fitted_numerical_columns_, dtype=np.float32)
            for c in present_cols:
                full_data[c] = pd.to_numeric(df_copy[c], errors="coerce").fillna(0.0).astype(np.float32)
            
            scaled_arr = self.scaler.transform(full_data)
            scaled_df = pd.DataFrame(scaled_arr, columns=self.fitted_numerical_columns_, index=df_copy.index)
            for c in present_cols:
                df_copy[c] = scaled_df[c]

        return df_copy

    def fit_transform(self, df: pd.DataFrame, y: Optional[pd.Series] = None) -> pd.DataFrame:
        """Fit on DataFrame and transform."""
        return self.fit(df, y).transform(df)
