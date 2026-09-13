from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from backend.app.core.logging import logger


@dataclass
class SplitResult:
    """Container holding partitioned datasets and split distribution metadata."""
    X_train: pd.DataFrame
    y_train_binary: pd.Series
    y_train_category: pd.Series
    y_train_original: pd.Series

    X_val: pd.DataFrame
    y_val_binary: pd.Series
    y_val_category: pd.Series
    y_val_original: pd.Series

    X_test: pd.DataFrame
    y_test_binary: pd.Series
    y_test_category: pd.Series
    y_test_original: pd.Series

    split_strategy: str
    unseen_categories: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def summary(self) -> Dict[str, Any]:
        """Return a formatted summary of split sizes and category distributions."""
        return {
            "strategy": self.split_strategy,
            "unseen_categories": self.unseen_categories,
            "train_samples": len(self.X_train),
            "val_samples": len(self.X_val),
            "test_samples": len(self.X_test),
            "train_normal": int((self.y_train_binary == 0).sum()),
            "train_attack": int((self.y_train_binary == 1).sum()),
            "val_normal": int((self.y_val_binary == 0).sum()),
            "val_attack": int((self.y_val_binary == 1).sum()),
            "test_normal": int((self.y_test_binary == 0).sum()),
            "test_attack": int((self.y_test_binary == 1).sum()),
            "train_categories": self.y_train_category.value_counts().to_dict(),
            "val_categories": self.y_val_category.value_counts().to_dict(),
            "test_categories": self.y_test_category.value_counts().to_dict(),
        }


class DatasetSplitter:
    """
    Partitions datasets into Train, Validation, and Test sets supporting
    Standard Random, Stratified, and Unseen Zero-Day Attack Evaluation strategies.
    """

    @classmethod
    def split(
        cls,
        X: pd.DataFrame,
        y_binary: pd.Series,
        y_category: pd.Series,
        y_original: pd.Series,
        strategy: str = "standard",  # "standard", "stratified", "unseen_zero_day"
        val_size: float = 0.15,
        test_size: float = 0.15,
        unseen_categories: Optional[List[str]] = None,
        random_state: int = 42,
    ) -> SplitResult:
        """
        Execute dataset partitioning based on the chosen strategy.
        """
        strat = strategy.lower().strip()
        logger.info(f"Executing dataset split with strategy='{strat}' (val={val_size}, test={test_size})...")

        if strat == "unseen_zero_day":
            return cls._split_unseen_zero_day(
                X, y_binary, y_category, y_original,
                unseen_categories=unseen_categories or [],
                val_size=val_size,
                test_size=test_size,
                random_state=random_state,
            )
        elif strat == "stratified":
            return cls._split_stratified(
                X, y_binary, y_category, y_original,
                val_size=val_size,
                test_size=test_size,
                random_state=random_state,
            )
        else:
            return cls._split_standard(
                X, y_binary, y_category, y_original,
                val_size=val_size,
                test_size=test_size,
                random_state=random_state,
            )

    @classmethod
    def _split_standard(
        cls,
        X: pd.DataFrame,
        y_binary: pd.Series,
        y_category: pd.Series,
        y_original: pd.Series,
        val_size: float,
        test_size: float,
        random_state: int,
    ) -> SplitResult:
        """Standard random train / validation / test split."""
        indices = np.arange(len(X))
        
        # 1. Split off test set
        train_val_idx, test_idx = train_test_split(
            indices, test_size=test_size, random_state=random_state, shuffle=True
        )

        # 2. Split train and validation from remaining
        relative_val_size = val_size / (1.0 - test_size)
        train_idx, val_idx = train_test_split(
            train_val_idx, test_size=relative_val_size, random_state=random_state, shuffle=True
        )

        return SplitResult(
            X_train=X.iloc[train_idx].reset_index(drop=True),
            y_train_binary=y_binary.iloc[train_idx].reset_index(drop=True),
            y_train_category=y_category.iloc[train_idx].reset_index(drop=True),
            y_train_original=y_original.iloc[train_idx].reset_index(drop=True),
            X_val=X.iloc[val_idx].reset_index(drop=True),
            y_val_binary=y_binary.iloc[val_idx].reset_index(drop=True),
            y_val_category=y_category.iloc[val_idx].reset_index(drop=True),
            y_val_original=y_original.iloc[val_idx].reset_index(drop=True),
            X_test=X.iloc[test_idx].reset_index(drop=True),
            y_test_binary=y_binary.iloc[test_idx].reset_index(drop=True),
            y_test_category=y_category.iloc[test_idx].reset_index(drop=True),
            y_test_original=y_original.iloc[test_idx].reset_index(drop=True),
            split_strategy="standard",
        )

    @classmethod
    def _split_stratified(
        cls,
        X: pd.DataFrame,
        y_binary: pd.Series,
        y_category: pd.Series,
        y_original: pd.Series,
        val_size: float,
        test_size: float,
        random_state: int,
    ) -> SplitResult:
        """Stratified split preserving attack category proportions across subsets."""
        indices = np.arange(len(X))
        
        # Use y_category if multiple instances exist for all classes, otherwise fallback to y_binary
        cat_counts = y_category.value_counts()
        strat_target = y_category if (cat_counts.min() >= 2) else y_binary

        train_val_idx, test_idx = train_test_split(
            indices, test_size=test_size, random_state=random_state, shuffle=True, stratify=strat_target
        )

        strat_target_sub = strat_target.iloc[train_val_idx]
        sub_counts = strat_target_sub.value_counts()
        strat_sub = strat_target_sub if (sub_counts.min() >= 2) else None

        relative_val_size = val_size / (1.0 - test_size)
        train_idx_rel, val_idx_rel = train_test_split(
            np.arange(len(train_val_idx)),
            test_size=relative_val_size,
            random_state=random_state,
            shuffle=True,
            stratify=strat_sub,
        )

        train_idx = train_val_idx[train_idx_rel]
        val_idx = train_val_idx[val_idx_rel]

        return SplitResult(
            X_train=X.iloc[train_idx].reset_index(drop=True),
            y_train_binary=y_binary.iloc[train_idx].reset_index(drop=True),
            y_train_category=y_category.iloc[train_idx].reset_index(drop=True),
            y_train_original=y_original.iloc[train_idx].reset_index(drop=True),
            X_val=X.iloc[val_idx].reset_index(drop=True),
            y_val_binary=y_binary.iloc[val_idx].reset_index(drop=True),
            y_val_category=y_category.iloc[val_idx].reset_index(drop=True),
            y_val_original=y_original.iloc[val_idx].reset_index(drop=True),
            X_test=X.iloc[test_idx].reset_index(drop=True),
            y_test_binary=y_binary.iloc[test_idx].reset_index(drop=True),
            y_test_category=y_category.iloc[test_idx].reset_index(drop=True),
            y_test_original=y_original.iloc[test_idx].reset_index(drop=True),
            split_strategy="stratified",
        )

    @classmethod
    def _split_unseen_zero_day(
        cls,
        X: pd.DataFrame,
        y_binary: pd.Series,
        y_category: pd.Series,
        y_original: pd.Series,
        unseen_categories: List[str],
        val_size: float,
        test_size: float,
        random_state: int,
    ) -> SplitResult:
        """
        Unseen Zero-Day Attack Evaluation Split.
        
        Selected attack categories are strictly withheld from Training and Validation
        and routed 100% to the Test set.
        
        The model trains exclusively on normal traffic and known baseline attacks,
        simulating genuine zero-day attack conditions without data leakage.
        """
        unseen_set = set([c.lower().strip() for c in unseen_categories])
        if not unseen_set:
            logger.warning("Unseen Zero-Day split requested but unseen_categories is empty. Falling back to standard split.")
            return cls._split_standard(X, y_binary, y_category, y_original, val_size, test_size, random_state)

        # Identify indices with unseen zero-day attacks
        y_cat_clean = y_category.astype(str).str.lower().str.strip()
        y_orig_clean = y_original.astype(str).str.lower().str.strip()
        
        is_unseen = y_cat_clean.isin(unseen_set) | y_orig_clean.isin(unseen_set)
        unseen_indices = np.where(is_unseen)[0]
        known_indices = np.where(~is_unseen)[0]

        logger.info(
            f"Zero-Day Split: Withholding {len(unseen_indices)} samples for unseen attack categories: {unseen_categories}. "
            f"Known samples for train/val/test split: {len(known_indices)}"
        )

        if len(known_indices) == 0:
            raise ValueError("All samples matched unseen categories! Cannot create training split.")

        # Split known samples into train, val, and known-test
        known_train_val_idx, known_test_idx = train_test_split(
            known_indices, test_size=test_size, random_state=random_state, shuffle=True
        )

        relative_val_size = val_size / (1.0 - test_size)
        known_train_idx, known_val_idx = train_test_split(
            known_train_val_idx, test_size=relative_val_size, random_state=random_state, shuffle=True
        )

        # Combined test set = known test samples + ALL unseen zero-day attack samples
        full_test_idx = np.concatenate([known_test_idx, unseen_indices])
        # Shuffle test set for randomized evaluation order
        rng = np.random.RandomState(random_state)
        rng.shuffle(full_test_idx)

        logger.info(
            f"Zero-Day Split Complete: Train={len(known_train_idx)}, Val={len(known_val_idx)}, "
            f"Test={len(full_test_idx)} (Known Test={len(known_test_idx)}, Unseen Zero-Day Test={len(unseen_indices)})"
        )

        return SplitResult(
            X_train=X.iloc[known_train_idx].reset_index(drop=True),
            y_train_binary=y_binary.iloc[known_train_idx].reset_index(drop=True),
            y_train_category=y_category.iloc[known_train_idx].reset_index(drop=True),
            y_train_original=y_original.iloc[known_train_idx].reset_index(drop=True),
            X_val=X.iloc[known_val_idx].reset_index(drop=True),
            y_val_binary=y_binary.iloc[known_val_idx].reset_index(drop=True),
            y_val_category=y_category.iloc[known_val_idx].reset_index(drop=True),
            y_val_original=y_original.iloc[known_val_idx].reset_index(drop=True),
            X_test=X.iloc[full_test_idx].reset_index(drop=True),
            y_test_binary=y_binary.iloc[full_test_idx].reset_index(drop=True),
            y_test_category=y_category.iloc[full_test_idx].reset_index(drop=True),
            y_test_original=y_original.iloc[full_test_idx].reset_index(drop=True),
            split_strategy="unseen_zero_day",
            unseen_categories=unseen_categories,
        )
