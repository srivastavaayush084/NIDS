from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from backend.app.core.logging import logger


class NetworkFeatureEngineer:
    """
    Domain-specific Network Feature Engineering layer.
    Extracts traffic flow ratios, packet byte rates, and asymmetry indicators
    adaptively based on the actual columns present in the dataset.
    """

    def __init__(self, enable_engineering: bool = True):
        self.enable_engineering = enable_engineering
        self.engineered_features_: List[str] = []
        self.is_fitted: bool = False

    def fit(self, df: pd.DataFrame, y: Optional[pd.Series] = None) -> "NetworkFeatureEngineer":
        """
        Detect which domain network features can be derived from the available columns.
        """
        self.engineered_features_ = []
        if not self.enable_engineering:
            self.is_fitted = True
            return self

        cols_lower = {c.lower(): c for c in df.columns}

        # 1. Byte ratio (src_bytes vs dst_bytes / sbytes vs dbytes)
        src_byte_col = cols_lower.get("src_bytes") or cols_lower.get("sbytes") or cols_lower.get("total_length_of_fwd_packets")
        dst_byte_col = cols_lower.get("dst_bytes") or cols_lower.get("dbytes") or cols_lower.get("total_length_of_bwd_packets")
        if src_byte_col and dst_byte_col:
            self.engineered_features_.append("feat_byte_ratio")
            self.engineered_features_.append("feat_total_bytes")

        # 2. Flow duration rates (bytes per sec / packets per sec)
        duration_col = cols_lower.get("duration") or cols_lower.get("dur") or cols_lower.get("flow_duration")
        if duration_col and src_byte_col:
            self.engineered_features_.append("feat_src_byte_rate")
        
        # 3. Packet counts & packet ratios
        spkt_col = cols_lower.get("spkts") or cols_lower.get("total_fwd_packets") or cols_lower.get("count")
        dpkt_col = cols_lower.get("dpkts") or cols_lower.get("total_backward_packets") or cols_lower.get("srv_count")
        if spkt_col and dpkt_col:
            self.engineered_features_.append("feat_packet_ratio")

        self.is_fitted = True
        logger.info(f"NetworkFeatureEngineer identified {len(self.engineered_features_)} applicable features: {self.engineered_features_}")
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute engineered domain features without modifying input DataFrame in-place.
        """
        if not self.is_fitted:
            raise RuntimeError("NetworkFeatureEngineer must be fitted before transforming data.")

        if not self.enable_engineering or not self.engineered_features_:
            return df.copy()

        df_copy = df.copy()
        cols_lower = {c.lower(): c for c in df_copy.columns}

        src_byte_col = cols_lower.get("src_bytes") or cols_lower.get("sbytes") or cols_lower.get("total_length_of_fwd_packets")
        dst_byte_col = cols_lower.get("dst_bytes") or cols_lower.get("dbytes") or cols_lower.get("total_length_of_bwd_packets")
        duration_col = cols_lower.get("duration") or cols_lower.get("dur") or cols_lower.get("flow_duration")
        spkt_col = cols_lower.get("spkts") or cols_lower.get("total_fwd_packets") or cols_lower.get("count")
        dpkt_col = cols_lower.get("dpkts") or cols_lower.get("total_backward_packets") or cols_lower.get("srv_count")

        # 1. Byte metrics
        if src_byte_col and dst_byte_col:
            src_b = pd.to_numeric(df_copy[src_byte_col], errors="coerce").fillna(0.0)
            dst_b = pd.to_numeric(df_copy[dst_byte_col], errors="coerce").fillna(0.0)
            if "feat_byte_ratio" in self.engineered_features_:
                df_copy["feat_byte_ratio"] = (src_b + 1.0) / (dst_b + 1.0)
            if "feat_total_bytes" in self.engineered_features_:
                df_copy["feat_total_bytes"] = src_b + dst_b

        # 2. Rate metrics
        if duration_col and src_byte_col and "feat_src_byte_rate" in self.engineered_features_:
            dur = pd.to_numeric(df_copy[duration_col], errors="coerce").fillna(0.0)
            src_b = pd.to_numeric(df_copy[src_byte_col], errors="coerce").fillna(0.0)
            df_copy["feat_src_byte_rate"] = src_b / (dur + 1e-4)

        # 3. Packet ratios
        if spkt_col and dpkt_col and "feat_packet_ratio" in self.engineered_features_:
            spkt = pd.to_numeric(df_copy[spkt_col], errors="coerce").fillna(0.0)
            dpkt = pd.to_numeric(df_copy[dpkt_col], errors="coerce").fillna(0.0)
            df_copy["feat_packet_ratio"] = (spkt + 1.0) / (dpkt + 1.0)

        return df_copy

    def fit_transform(self, df: pd.DataFrame, y: Optional[pd.Series] = None) -> pd.DataFrame:
        """Fit on DataFrame and transform."""
        return self.fit(df, y).transform(df)
