from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from backend.app.core.logging import logger


@dataclass
class DatasetSummary:
    """Comprehensive statistical and distributional profile of a network intrusion dataset."""
    total_samples: int
    total_features: int
    memory_usage_mb: float
    duplicate_rows: int
    missing_cells: int
    numerical_features: List[str] = field(default_factory=list)
    categorical_features: List[str] = field(default_factory=list)
    class_distribution: Dict[str, int] = field(default_factory=dict)
    class_percentages: Dict[str, float] = field(default_factory=dict)
    attack_category_distribution: Dict[str, int] = field(default_factory=dict)
    attack_category_percentages: Dict[str, float] = field(default_factory=dict)
    normal_count: int = 0
    attack_count: int = 0
    imbalance_ratio: float = 0.0  # normal / (attack + 1e-9)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_samples": self.total_samples,
            "total_features": self.total_features,
            "memory_usage_mb": round(self.memory_usage_mb, 2),
            "duplicate_rows": self.duplicate_rows,
            "missing_cells": self.missing_cells,
            "numerical_feature_count": len(self.numerical_features),
            "categorical_feature_count": len(self.categorical_features),
            "numerical_features": self.numerical_features,
            "categorical_features": self.categorical_features,
            "class_distribution": self.class_distribution,
            "class_percentages": self.class_percentages,
            "attack_category_distribution": self.attack_category_distribution,
            "attack_category_percentages": self.attack_category_percentages,
            "normal_count": self.normal_count,
            "attack_count": self.attack_count,
            "imbalance_ratio": round(self.imbalance_ratio, 3),
        }


class DatasetAnalyzer:
    """
    Analyzes network security dataset structures, statistical characteristics,
    and class imbalance distributions for supervised and zero-day detection models.
    """

    @classmethod
    def analyze(
        cls,
        X: pd.DataFrame,
        y_binary: Optional[pd.Series] = None,
        y_category: Optional[pd.Series] = None,
        y_original: Optional[pd.Series] = None,
    ) -> DatasetSummary:
        """
        Generate statistical summary and distribution analysis.
        """
        total_samples = len(X)
        total_features = len(X.columns)
        mem_mb = float(X.memory_usage(deep=True).sum() / (1024 * 1024))
        duplicates = int(X.duplicated().sum()) if total_samples > 0 else 0
        missing = int(X.isna().sum().sum())

        numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()
        cat_cols = X.select_dtypes(exclude=[np.number]).columns.tolist()

        # Class distribution (Binary)
        class_dist: Dict[str, int] = {}
        class_pct: Dict[str, float] = {}
        normal_cnt = 0
        attack_cnt = 0

        if y_binary is not None and len(y_binary) > 0:
            counts = y_binary.value_counts().to_dict()
            normal_cnt = int(counts.get(0, counts.get("0", 0)))
            attack_cnt = int(counts.get(1, counts.get("1", 0)))
            class_dist = {"normal": normal_cnt, "attack": attack_cnt}
            class_pct = {
                "normal": round((normal_cnt / total_samples) * 100, 2) if total_samples else 0.0,
                "attack": round((attack_cnt / total_samples) * 100, 2) if total_samples else 0.0,
            }

        imbalance_ratio = float(normal_cnt / (attack_cnt + 1e-9)) if attack_cnt > 0 else 1.0

        # Attack category distribution
        cat_dist: Dict[str, int] = {}
        cat_pct: Dict[str, float] = {}
        if y_category is not None and len(y_category) > 0:
            for cat, cnt in y_category.value_counts().items():
                cat_str = str(cat)
                cat_dist[cat_str] = int(cnt)
                cat_pct[cat_str] = round((int(cnt) / total_samples) * 100, 2)

        summary = DatasetSummary(
            total_samples=total_samples,
            total_features=total_features,
            memory_usage_mb=mem_mb,
            duplicate_rows=duplicates,
            missing_cells=missing,
            numerical_features=numeric_cols,
            categorical_features=cat_cols,
            class_distribution=class_dist,
            class_percentages=class_pct,
            attack_category_distribution=cat_dist,
            attack_category_percentages=cat_pct,
            normal_count=normal_cnt,
            attack_count=attack_cnt,
            imbalance_ratio=imbalance_ratio,
        )

        logger.info(
            f"Dataset Summary: {total_samples} rows, {total_features} features "
            f"({len(numeric_cols)} num, {len(cat_cols)} cat), Normal={normal_cnt} "
            f"({class_pct.get('normal', 0)}%), Attack={attack_cnt} ({class_pct.get('attack', 0)}%)"
        )
        return summary
