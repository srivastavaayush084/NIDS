#!/usr/bin/env python
"""
CLI Script to Train Supervised Random Forest Baseline Classifier.

Usage:
    python scripts/train_random_forest.py --dataset synthetic --n-estimators 100
    python scripts/train_random_forest.py --dataset nsl_kdd --n-estimators 150 --max-depth 20
    python scripts/train_random_forest.py --dataset cicids2017 --n-estimators 200
    python scripts/train_random_forest.py --dataset unsw_nb15 --n-estimators 150
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pandas as pd
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ml.training.random_forest_trainer import RandomForestTrainer
from backend.app.ml.data.loaders.factory import list_supported_datasets
from backend.app.ml.data.utils.data_utils import load_dataframe


def parse_args():
    parser = argparse.ArgumentParser(
        description="ZeroDayAI - Supervised Random Forest Baseline Training",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--dataset",
        type=str,
        default="synthetic",
        choices=list_supported_datasets(),
        help=f"Dataset to train on. Options: {list_supported_datasets()}",
    )
    parser.add_argument(
        "--version",
        type=str,
        default="1.0.0",
        help="Version tag for the trained model artifact.",
    )
    parser.add_argument(
        "--n-estimators",
        type=int,
        default=settings.RF_N_ESTIMATORS,
        help="Number of trees in the forest.",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=settings.RF_MAX_DEPTH,
        help="Maximum depth of the tree (None = unlimited).",
    )
    parser.add_argument(
        "--min-samples-split",
        type=int,
        default=settings.RF_MIN_SAMPLES_SPLIT,
        help="Minimum number of samples required to split an internal node.",
    )
    parser.add_argument(
        "--min-samples-leaf",
        type=int,
        default=settings.RF_MIN_SAMPLES_LEAF,
        help="Minimum number of samples required to be at a leaf node.",
    )
    parser.add_argument(
        "--max-features",
        type=str,
        default=settings.RF_MAX_FEATURES,
        help="Number of features to consider when looking for best split ('sqrt', 'log2', or float).",
    )
    parser.add_argument(
        "--class-weight",
        type=str,
        default=settings.RF_CLASS_WEIGHT,
        choices=["balanced", "balanced_subsample", "none"],
        help="Class weight mode for addressing class imbalance.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=settings.RF_THRESHOLD,
        help="Default probability decision threshold for attack classification.",
    )
    parser.add_argument(
        "--no-tune-threshold",
        action="store_true",
        help="Disable validation-based F1 threshold tuning and force default threshold.",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=settings.RF_RANDOM_SEED,
        help="Deterministic random seed.",
    )
    parser.add_argument(
        "--n-jobs",
        type=int,
        default=settings.RF_N_JOBS,
        help="Number of CPU cores to use (-1 = all available).",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Custom directory containing processed training splits.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Custom output directory for model artifacts.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    logger.info("=" * 60)
    logger.info(f"STARTING RANDOM FOREST TRAINING: dataset='{args.dataset}'")
    logger.info("=" * 60)

    # 1. Resolve Processed Data Paths
    proc_dir = (
        Path(args.data_dir)
        if args.data_dir
        else settings.DATA_DIR / "processed" / args.dataset
    )

    X_train_path = proc_dir / "X_train.csv"
    y_train_path = proc_dir / "y_train.csv"
    X_val_path = proc_dir / "X_val.csv"
    y_val_path = proc_dir / "y_val.csv"

    if not X_train_path.exists() or not y_train_path.exists():
        logger.error(
            f"Processed training data not found in {proc_dir}. "
            f"Please run: python scripts/prepare_dataset.py --dataset {args.dataset}"
        )
        sys.exit(1)

    logger.info(f"Loading processed training data from: {proc_dir}")
    X_train = load_dataframe(X_train_path)
    y_train_df = load_dataframe(y_train_path)
    y_train_binary = y_train_df["binary"] if "binary" in y_train_df.columns else y_train_df.iloc[:, 0]

    X_val = load_dataframe(X_val_path) if X_val_path.exists() else None
    y_val_binary = None
    if X_val is not None and y_val_path.exists():
        y_val_df = load_dataframe(y_val_path)
        y_val_binary = y_val_df["binary"] if "binary" in y_val_df.columns else y_val_df.iloc[:, 0]

    class_weight_val = None if args.class_weight == "none" else args.class_weight

    # 2. Instantiate and Execute Trainer
    trainer = RandomForestTrainer(
        dataset_name=args.dataset,
        version=args.version,
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        min_samples_split=args.min_samples_split,
        min_samples_leaf=args.min_samples_leaf,
        max_features=args.max_features,
        class_weight=class_weight_val,
        random_state=args.random_state,
        n_jobs=args.n_jobs,
        decision_threshold=args.threshold,
        tune_threshold=not args.no_tune_threshold,
    )

    trainer.train(
        X_train_proc=X_train,
        y_train_binary=y_train_binary,
        X_val_proc=X_val,
        y_val_binary=y_val_binary,
    )

    # 3. Save Artifacts & Register Model
    model_path, meta_path = trainer.save_artifacts(
        output_dir=args.output_dir,
        preprocessing_dir=settings.PREPROCESSING_DIR / args.dataset,
    )

    logger.info("=" * 60)
    logger.info("RANDOM FOREST TRAINING COMPLETED SUCCESSFULLY!")
    logger.info(f"Model File:         {model_path}")
    logger.info(f"Metadata File:     {meta_path}")
    logger.info(f"Decision Threshold: {trainer.model.decision_threshold:.4f} ({trainer.model.threshold_strategy})")
    logger.info("Top 5 Contributing Features:")
    for feat in trainer.model.get_feature_importances(top_n=5):
        logger.info(f"  #{feat['rank']} - {feat['feature']:<25}: {feat['importance']:.4f}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
