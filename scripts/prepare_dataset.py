#!/usr/bin/env python
"""
Command-Line Interface for Network Intrusion & Zero-Day Dataset Ingestion & Preprocessing.

Usage:
    python scripts/prepare_dataset.py --dataset synthetic --split-strategy unseen_zero_day --unseen-attacks zero_day_unseen
    python scripts/prepare_dataset.py --dataset nsl_kdd --split-strategy standard --scaling standard
    python scripts/prepare_dataset.py --dataset cicids2017 --split-strategy stratified
    python scripts/prepare_dataset.py --dataset unsw_nb15 --split-strategy unseen_zero_day --unseen-attacks worms,shellcode
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path so backend imports resolve seamlessly
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pandas as pd
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ml.data.loaders.factory import get_dataset_loader, list_supported_datasets
from backend.app.ml.data.validation.dataset_validator import DatasetValidator
from backend.app.ml.data.statistics.dataset_analyzer import DatasetAnalyzer
from backend.app.ml.data.preprocessing.pipeline import NetworkDataPipeline
from backend.app.ml.data.splitting.dataset_splitter import DatasetSplitter
from backend.app.ml.data.utils.data_utils import save_dataframe, save_metadata, ensure_dir


def parse_args():
    parser = argparse.ArgumentParser(
        description="ZeroDayAI - Dataset Ingestion, Preprocessing & Feature Engineering Pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--dataset",
        type=str,
        default="synthetic",
        choices=list_supported_datasets(),
        help=f"Dataset to ingest and process. Options: {list_supported_datasets()}",
    )
    parser.add_argument(
        "--file-path",
        type=str,
        default=None,
        help="Optional custom file path to raw dataset file.",
    )
    parser.add_argument(
        "--split-strategy",
        type=str,
        default="standard",
        choices=["standard", "stratified", "unseen_zero_day"],
        help="Dataset partitioning strategy for ML and zero-day attack benchmarking.",
    )
    parser.add_argument(
        "--unseen-attacks",
        type=str,
        default="",
        help="Comma-separated list of attack categories to withhold from training for zero-day evaluation.",
    )
    parser.add_argument(
        "--scaling",
        type=str,
        default="standard",
        choices=["standard", "minmax", "robust", "none"],
        help="Numerical feature scaling strategy.",
    )
    parser.add_argument(
        "--encoding",
        type=str,
        default="onehot",
        choices=["onehot", "ordinal"],
        help="Categorical feature encoding strategy.",
    )
    parser.add_argument(
        "--feature-selection",
        type=str,
        default="variance",
        choices=["variance", "correlation", "k_best", "none"],
        help="Feature selection algorithm.",
    )
    parser.add_argument(
        "--k-features",
        type=int,
        default=None,
        help="Number of top features to select when using k_best.",
    )
    parser.add_argument(
        "--variance-threshold",
        type=float,
        default=0.0,
        help="Variance threshold for constant feature elimination.",
    )
    parser.add_argument(
        "--correlation-threshold",
        type=float,
        default=0.98,
        help="Correlation threshold for collinear feature elimination.",
    )
    parser.add_argument(
        "--val-size",
        type=float,
        default=0.15,
        help="Proportion of data allocated to the validation split.",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.15,
        help="Proportion of data allocated to the test split.",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Random seed for reproducible dataset partitioning.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Custom output directory for processed datasets.",
    )
    parser.add_argument(
        "--save-format",
        type=str,
        default="csv",
        choices=["csv", "parquet"],
        help="Storage format for processed dataset splits.",
    )
    return parser.parse_args()


def run_pipeline(args):
    logger.info("=" * 60)
    logger.info(f"STARTING DATASET PREPARATION: dataset='{args.dataset}'")
    logger.info("=" * 60)

    # 1. Instantiate Dataset Loader
    loader = get_dataset_loader(args.dataset)
    logger.info(f"[1/8] Ingesting dataset using loader: {loader.__class__.__name__}")
    
    try:
        raw_df = loader.load(file_path=args.file_path)
    except FileNotFoundError as e:
        logger.error(f"Failed to load dataset: {e}")
        sys.exit(1)

    # 2. Validate Dataset
    logger.info("[2/8] Performing dataset validation and schema checks...")
    val_report = DatasetValidator.validate_dataframe(
        raw_df,
        target_column=loader.target_column,
        check_leakage=True
    )
    if not val_report.is_valid:
        logger.error(f"Dataset validation failed: {val_report.errors}")
        sys.exit(1)

    # 3. Separate Feature Matrix X and Ground-Truth Labels y (Prevent Leakage)
    logger.info("[3/8] Isolating feature matrix X and ground-truth labels...")
    X, y_original, y_category, y_binary = loader.extract_labels(raw_df)

    # 4. Analyze Dataset Statistics & Imbalance
    logger.info("[4/8] Analyzing dataset structure and class balance...")
    summary = DatasetAnalyzer.analyze(X, y_binary=y_binary, y_category=y_category, y_original=y_original)

    # 5. Partition Dataset (Standard, Stratified, or Unseen Zero-Day Split)
    unseen_cats = [c.strip().lower() for c in args.unseen_attacks.split(",") if c.strip()]
    logger.info(f"[5/8] Partitioning dataset (strategy='{args.split_strategy}', unseen_categories={unseen_cats})...")
    
    split_res = DatasetSplitter.split(
        X=X,
        y_binary=y_binary,
        y_category=y_category,
        y_original=y_original,
        strategy=args.split_strategy,
        val_size=args.val_size,
        test_size=args.test_size,
        unseen_categories=unseen_cats,
        random_state=args.random_state,
    )

    # 6. Fit Preprocessing Pipeline (STRICTLY on Training Data)
    logger.info("[6/8] Fitting preprocessing pipeline on X_train (Leak-Free)...")
    pipeline = NetworkDataPipeline(
        dataset_name=loader.dataset_name,
        scaling_strategy=args.scaling,
        encoding_strategy=args.encoding,
        selection_strategy=args.feature_selection,
        variance_threshold=args.variance_threshold,
        correlation_threshold=args.correlation_threshold,
        k_features=args.k_features,
        drop_duplicates=True,
        enable_feature_engineering=True,
    )
    
    # Fit strictly on X_train
    pipeline.fit(split_res.X_train, y=split_res.y_train_binary)

    # Transform all splits using fitted pipeline
    logger.info("Transforming X_train, X_val, and X_test through fitted pipeline...")
    X_train_proc = pipeline.transform(split_res.X_train)
    X_val_proc = pipeline.transform(split_res.X_val)
    X_test_proc = pipeline.transform(split_res.X_test)

    # 7. Save Preprocessing Artifacts
    logger.info("[7/8] Saving preprocessing artifacts for inference reuse...")
    artifact_dir = settings.PREPROCESSING_DIR / loader.dataset_name
    pipeline.save(artifact_dir)

    # Save dataset statistics report
    save_metadata(summary.to_dict(), artifact_dir / "dataset_summary.json")
    save_metadata(split_res.summary(), artifact_dir / "split_summary.json")

    # 8. Save Processed Dataset Splits
    logger.info("[8/8] Saving processed dataset splits to disk...")
    processed_dir = (
        Path(args.output_dir)
        if args.output_dir
        else settings.DATA_DIR / "processed" / loader.dataset_name
    )
    ensure_dir(processed_dir)

    ext = args.save_format.lower()
    # Save Feature Matrices
    save_dataframe(X_train_proc, processed_dir / f"X_train.{ext}", file_format=ext)
    save_dataframe(X_val_proc, processed_dir / f"X_val.{ext}", file_format=ext)
    save_dataframe(X_test_proc, processed_dir / f"X_test.{ext}", file_format=ext)

    # Save Labels
    y_train_df = pd.DataFrame({
        "original": split_res.y_train_original,
        "category": split_res.y_train_category,
        "binary": split_res.y_train_binary,
    })
    y_val_df = pd.DataFrame({
        "original": split_res.y_val_original,
        "category": split_res.y_val_category,
        "binary": split_res.y_val_binary,
    })
    y_test_df = pd.DataFrame({
        "original": split_res.y_test_original,
        "category": split_res.y_test_category,
        "binary": split_res.y_test_binary,
    })

    save_dataframe(y_train_df, processed_dir / f"y_train.csv", file_format="csv")
    save_dataframe(y_val_df, processed_dir / f"y_val.csv", file_format="csv")
    save_dataframe(y_test_df, processed_dir / f"y_test.csv", file_format="csv")

    logger.info("=" * 60)
    logger.info("DATASET PREPARATION COMPLETED SUCCESSFULLY!")
    logger.info(f"Dataset:              {loader.dataset_name}")
    logger.info(f"Split Strategy:       {args.split_strategy}")
    logger.info(f"Train Shape:          {X_train_proc.shape}")
    logger.info(f"Validation Shape:     {X_val_proc.shape}")
    logger.info(f"Test Shape:           {X_test_proc.shape}")
    logger.info(f"Features:             {pipeline.output_feature_count_} selected")
    logger.info(f"Artifacts Saved to:   {artifact_dir}")
    logger.info(f"Processed Splits in:  {processed_dir}")
    logger.info("=" * 60)


if __name__ == "__main__":
    cli_args = parse_args()
    run_pipeline(cli_args)
