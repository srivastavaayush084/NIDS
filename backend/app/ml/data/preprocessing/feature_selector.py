from typing import Any, Dict, List, Optional, Set, Union
import numpy as np
import pandas as pd
from sklearn.feature_selection import VarianceThreshold, SelectKBest, f_classif, mutual_info_classif
from backend.app.core.logging import logger


class FeatureSelector:
    """
    Configurable Feature Selection for Network Intrusion Data.
    Performs low-variance filtering, collinear feature removal,
    and statistical ranking while preserving deterministic feature alignment.
    """

    def __init__(
        self,
        strategy: str = "variance",  # "variance", "correlation", "k_best", "none", "explicit"
        variance_threshold: float = 0.0,  # drop constant features by default
        correlation_threshold: float = 0.98,
        k_features: Optional[int] = None,
        scoring_func: str = "f_classif",  # "f_classif", "mutual_info"
        explicit_features: Optional[List[str]] = None,
    ):
        self.strategy = strategy.lower()
        self.variance_threshold = variance_threshold
        self.correlation_threshold = correlation_threshold
        self.k_features = k_features
        self.scoring_func = scoring_func
        self.explicit_features = explicit_features
        
        self.selected_features_: List[str] = []
        self.dropped_features_: Dict[str, List[str]] = {"variance": [], "correlation": []}
        self.is_fitted: bool = False

    def fit(self, df: pd.DataFrame, y: Optional[pd.Series] = None) -> "FeatureSelector":
        """
        Fit feature selection criteria ONLY on training features.
        """
        all_cols = list(df.columns)
        if self.strategy == "none":
            self.selected_features_ = all_cols
            self.is_fitted = True
            return self

        if self.strategy == "explicit" and self.explicit_features is not None:
            self.selected_features_ = [c for c in self.explicit_features if c in all_cols]
            self.is_fitted = True
            return self

        logger.info(f"Fitting FeatureSelector ({self.strategy}) on {len(all_cols)} features...")
        current_df = df.copy()

        # 1. Variance Threshold Filter (Drop constant / near constant features)
        if self.variance_threshold >= 0:
            num_cols = current_df.select_dtypes(include=[np.number]).columns.tolist()
            if num_cols:
                variances = current_df[num_cols].var()
                low_var_cols = variances[variances <= self.variance_threshold].index.tolist()
                if low_var_cols:
                    logger.info(f"Dropping {len(low_var_cols)} low-variance (<= {self.variance_threshold}) features.")
                    self.dropped_features_["variance"] = low_var_cols
                    current_df = current_df.drop(columns=low_var_cols)

        # 2. Correlation Filter (Drop redundant highly collinear features)
        if self.strategy in ("correlation", "all") and self.correlation_threshold < 1.0:
            num_cols = current_df.select_dtypes(include=[np.number]).columns.tolist()
            if len(num_cols) > 1:
                corr_matrix = current_df[num_cols].corr().abs()
                upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
                to_drop = [column for column in upper.columns if any(upper[column] > self.correlation_threshold)]
                if to_drop:
                    logger.info(f"Dropping {len(to_drop)} collinear features (corr > {self.correlation_threshold}).")
                    self.dropped_features_["correlation"] = to_drop
                    current_df = current_df.drop(columns=to_drop)

        # 3. K-Best Statistical Selection (if supervised labels y provided and k specified)
        if self.strategy in ("k_best", "all") and self.k_features is not None and y is not None:
            num_cols = current_df.select_dtypes(include=[np.number]).columns.tolist()
            k = min(self.k_features, len(num_cols))
            if k > 0 and len(num_cols) > k:
                score_fn = f_classif if self.scoring_func == "f_classif" else mutual_info_classif
                selector = SelectKBest(score_func=score_fn, k=k)
                X_num = current_df[num_cols].fillna(0.0)
                selector.fit(X_num, y)
                selected_num = [num_cols[i] for i in selector.get_support(indices=True)]
                non_num_cols = [c for c in current_df.columns if c not in num_cols]
                current_df = current_df[non_num_cols + selected_num]

        self.selected_features_ = list(current_df.columns)
        self.is_fitted = True
        logger.info(f"Feature Selection complete. Retained {len(self.selected_features_)} / {len(all_cols)} features.")
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Align dataset to selected features in exact deterministic order.
        Missing features are imputed with 0.0 to guarantee schema stability during inference.
        """
        if not self.is_fitted:
            raise RuntimeError("FeatureSelector must be fitted before transforming data.")

        df_copy = df.copy()
        
        # Ensure all selected features exist, fill missing with 0.0
        for col in self.selected_features_:
            if col not in df_copy.columns:
                df_copy[col] = 0.0

        return df_copy[self.selected_features_]

    def fit_transform(self, df: pd.DataFrame, y: Optional[pd.Series] = None) -> pd.DataFrame:
        """Fit on DataFrame and transform."""
        return self.fit(df, y).transform(df)
