#!/usr/bin/env python
"""
CLI Script to Train Isolation Forest Anomaly Detector.

Usage:
    python scripts/train_isolation_forest.py --dataset synthetic --n-estimators 100 --contamination 0.05
    python scripts/train_isolation_forest.py --dataset nsl_kdd --n-estimators 150 --contamination 0.03
    python scripts/train_isolation_forest.py --dataset cicids2017 --n-estimators 200 --contamination 0.05
    python scripts/train_isolation_forest.py --dataset unsw_nb15 --n-estimators 150 --contamination 0.04
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
from backend.app.ml.training.isolation_forest_trainer import IsolationForestTrainer
from backend.app.ml.data.loaders.factory import list_supported_datasets
from backend.app.ml.data.utils.data_utils import load_dataframe


def parse_args():
    parser = argparse.ArgumentParser(
        description="ZeroDayAI - Isolation Forest Anomaly Detection Training",
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
        default=100,
        help="Number of isolation trees in the forest.",
    )
    parser.add_argument(
        "--contamination",
        type=float,
        default=0.05,
        help="Expected proportion of outliers/anomalies in baseline dataset.",
    )
    parser.add_argument(
        "--max-samples",
        type=str,
        default="auto",
        help="Number of samples to draw from X to train each tree ('auto' or integer).",
    )
    parser.add_argument(
        "--max-features",
        type=float,
        default=1.0,
        help="Proportion of features to draw from X to train each tree.",
    )
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help="Whether trees are fit with replacement sampling.",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Deterministic random seed.",
    )
    parser.add_argument(
        "--n-jobs",
        type=int,
        default=-1,
        help="Number of CPU cores to use (-1 = all available).",
    )
    parser.add_argument(
        "--all-traffic",
        action="store_true",
        help="If set, trains on mixed traffic. By default, trains exclusively on NORMAL traffic.",
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
    logger.info(f"STARTING ISOLATION FOREST TRAINING: dataset='{args.dataset}'")
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

    # If processed data is missing, notify user to run prepare_dataset.py
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

    # Parse max_samples
    max_samples_val = int(args.max_samples) if args.max_samples.isdigit() else args.max_samples

    # 2. Instantiate and Execute Trainer
    trainer = IsolationForestTrainer(
        dataset_name=args.dataset,
        version=args.version,
        n_estimators=args.n_estimators,
        contamination=args.contamination,
        max_samples=max_samples_val,
        max_features=args.max_features,
        bootstrap=args.bootstrap,
        random_state=args.random_state,
        n_jobs=args.n_jobs,
        normal_only_training=not args.all_traffic,
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
    logger.info("ISOLATION FOREST TRAINING COMPLETED SUCCESSFULLY!")
    logger.info(f"Model File:        {model_path}")
    logger.info(f"Metadata File:    {meta_path}")
    logger.info(f"Optimal Threshold: {trainer.optimal_threshold_}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
