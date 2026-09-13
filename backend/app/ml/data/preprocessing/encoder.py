from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder
from backend.app.core.logging import logger


class CategoricalEncoder:
    """
    Categorical Feature Encoder for Network Intrusion Detection.
    Encodes categorical features (e.g. protocol_type, service, flag, state)
    with safe handling of unseen / unknown categories during zero-day inference.
    """

    def __init__(
        self,
        strategy: str = "onehot",  # "onehot", "ordinal"
        categorical_columns: Optional[List[str]] = None,
        sparse_output: bool = False,
    ):
        self.strategy = strategy.lower()
        self.categorical_columns: Optional[List[str]] = categorical_columns
        self.sparse_output = sparse_output
        self.encoder: Optional[Union[OneHotEncoder, OrdinalEncoder]] = None
        self.encoded_feature_names_: List[str] = []
        self.fitted_categorical_columns_: List[str] = []
        self.is_fitted: bool = False

    def fit(self, df: pd.DataFrame, y: Optional[pd.Series] = None) -> "CategoricalEncoder":
        """
        Fit encoder ONLY on training data.
        """
        if self.categorical_columns is not None:
            self.fitted_categorical_columns_ = [c for c in self.categorical_columns if c in df.columns]
        else:
            self.fitted_categorical_columns_ = df.select_dtypes(exclude=[np.number]).columns.tolist()

        if not self.fitted_categorical_columns_:
            logger.info("No categorical columns detected or configured for encoding.")
            self.is_fitted = True
            self.encoded_feature_names_ = []
            return self

        logger.info(f"Fitting {self.strategy.upper()} CategoricalEncoder on columns: {self.fitted_categorical_columns_}")
        
        # Ensure strings
        cat_df = df[self.fitted_categorical_columns_].astype(str).fillna("unknown")

        if self.strategy == "onehot":
            self.encoder = OneHotEncoder(
                handle_unknown="ignore",
                sparse_output=self.sparse_output,
                dtype=np.float32
            )
            self.encoder.fit(cat_df)
            self.encoded_feature_names_ = list(
                self.encoder.get_feature_names_out(self.fitted_categorical_columns_)
            )
        elif self.strategy == "ordinal":
            self.encoder = OrdinalEncoder(
                handle_unknown="use_encoded_value",
                unknown_value=-1.0,
                dtype=np.float32
            )
            self.encoder.fit(cat_df)
            self.encoded_feature_names_ = list(self.fitted_categorical_columns_)
        else:
            raise ValueError(f"Unsupported categorical encoding strategy: '{self.strategy}'. Use 'onehot' or 'ordinal'.")

        self.is_fitted = True
        logger.info(f"CategoricalEncoder fitted. Generated {len(self.encoded_feature_names_)} encoded features.")
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform categorical columns in DataFrame.
        Replaces original categorical columns with encoded representation.
        Safely handles unseen categories without raising exceptions.
        """
        if not self.is_fitted:
            raise RuntimeError("CategoricalEncoder must be fitted before transforming data.")

        if not self.fitted_categorical_columns_ or self.encoder is None:
            # Return copy of df
            return df.copy()

        df_copy = df.copy()

        # Prepare categorical input DataFrame with missing columns filled if necessary
        cat_data = {}
        for col in self.fitted_categorical_columns_:
            if col in df_copy.columns:
                cat_data[col] = df_copy[col].astype(str).fillna("unknown")
            else:
                cat_data[col] = pd.Series(["unknown"] * len(df_copy), index=df_copy.index)

        cat_df = pd.DataFrame(cat_data, index=df_copy.index)
        encoded_arr = self.encoder.transform(cat_df)
        if hasattr(encoded_arr, "toarray"):
            encoded_arr = encoded_arr.toarray()

        encoded_df = pd.DataFrame(
            encoded_arr,
            columns=self.encoded_feature_names_,
            index=df_copy.index
        )

        # Drop original raw categorical columns and concatenate encoded features
        remaining_cols = [c for c in df_copy.columns if c not in self.fitted_categorical_columns_]
        result_df = pd.concat([df_copy[remaining_cols], encoded_df], axis=1)

        return result_df

    def fit_transform(self, df: pd.DataFrame, y: Optional[pd.Series] = None) -> pd.DataFrame:
        """Fit on DataFrame and transform."""
        return self.fit(df, y).transform(df)
