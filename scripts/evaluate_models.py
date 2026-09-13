#!/usr/bin/env python
"""
Unified CLI Script to Evaluate and Compare All Anomaly Detection and Baseline Models.

Models Benchmarked:
1. Isolation Forest (Unsupervised Anomaly Detector)
2. Dense Autoencoder (Deep Learning Reconstruction Detector)
3. LSTM Autoencoder (Sequential Reconstruction Detector)
4. Random Forest (Supervised Baseline Classifier)

Usage Examples:
    python scripts/evaluate_models.py --dataset synthetic --evaluation all
    python scripts/evaluate_models.py --dataset nsl_kdd --evaluation standard --models isolation_forest,random_forest
    python scripts/evaluate_models.py --dataset cicids2017 --evaluation unseen_attack --unseen-attacks botnet,infiltration
    python scripts/evaluate_models.py --dataset unsw_nb15 --evaluation all --no-plots
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ml.evaluation.model_comparator import ModelComparator
from backend.app.ml.data.loaders.factory import list_supported_datasets
from backend.app.ml.data.utils.data_utils import load_dataframe, load_metadata


def parse_args():
    parser = argparse.ArgumentParser(
        description="ZeroDayAI - Unified Multi-Model Evaluation and Comparative Benchmarking",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--dataset",
        type=str,
        default="synthetic",
        choices=list_supported_datasets(),
        help=f"Dataset to evaluate. Options: {list_supported_datasets()}",
    )
    parser.add_argument(
        "--evaluation",
        type=str,
        default="all",
        choices=["standard", "unseen_attack", "known_attack", "all"],
        help="Evaluation scenario type.",
    )
    parser.add_argument(
        "--models",
        type=str,
        default="isolation_forest,autoencoder,lstm_autoencoder,random_forest,ensemble",
        help="Comma-separated list of models to evaluate.",
    )
    parser.add_argument(
        "--unseen-attacks",
        type=str,
        default="",
        help="Comma-separated list of withheld attack categories for zero-day benchmark.",
    )
    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="Disable generation of comparative visualization charts.",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Custom directory containing processed test splits.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Custom output directory for comparison artifacts.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    logger.info("=" * 60)
    logger.info(f"STARTING UNIFIED MODEL EVALUATION CLI: dataset='{args.dataset}', evaluation='{args.evaluation}'")
    logger.info("=" * 60)

    # 1. Parse Models
    models_to_evaluate = [m.strip().lower() for m in args.models.split(",") if m.strip()]
    if not models_to_evaluate:
        logger.error("No models specified for evaluation.")
        sys.exit(1)

    # 2. Parse Unseen Attack Categories
    unseen_cats = [c.strip().lower() for c in args.unseen_attacks.split(",") if c.strip()]
    if not unseen_cats:
        split_summary_path = settings.PREPROCESSING_DIR / args.dataset / "split_summary.json"
        if split_summary_path.exists():
            try:
                split_info = load_metadata(split_summary_path)
                unseen_cats = split_info.get("unseen_categories", [])
            except Exception:
                unseen_cats = []

    # 3. Resolve Test Split Data
    proc_dir = (
        Path(args.data_dir)
        if args.data_dir
        else settings.DATA_DIR / "processed" / args.dataset
    )

    X_test_path = proc_dir / "X_test.csv"
    y_test_path = proc_dir / "y_test.csv"

    if not X_test_path.exists() or not y_test_path.exists():
        logger.error(
            f"Processed test split data not found in {proc_dir}. "
            f"Please run: python scripts/prepare_dataset.py --dataset {args.dataset}"
        )
        sys.exit(1)

    logger.info(f"Loading test split data from: {proc_dir}")
    X_test = load_dataframe(X_test_path)
    y_test_df = load_dataframe(y_test_path)

    y_test_binary = y_test_df["binary"] if "binary" in y_test_df.columns else y_test_df.iloc[:, 0]
    y_test_category = y_test_df["category"] if "category" in y_test_df.columns else None

    # 4. Execute Multi-Model Comparison
    try:
        report = ModelComparator.compare_models(
            dataset_name=args.dataset,
            models_to_evaluate=models_to_evaluate,
            X_test=X_test,
            y_test_binary=y_test_binary,
            y_test_category=y_test_category,
            unseen_categories=unseen_cats,
            evaluation_type=args.evaluation,
            output_dir=args.output_dir,
            generate_plots=not args.no_plots,
        )
    except Exception as e:
        logger.error(f"Model comparison execution failed: {e}", exc_info=True)
        sys.exit(1)

    # 5. Output Summary to Terminal
    summary_text = ModelComparator.format_text_summary(report)
    print("\n" + summary_text)

    # 6. Display Output Locations
    artifacts = report.get("saved_artifacts", {})
    print("\nSaved Comparison Artifacts:")
    print(f"  - Standard CSV Table:     {artifacts.get('standard_csv')}")
    print(f"  - Unseen Attack CSV Table:{artifacts.get('unseen_attack_csv')}")
    print(f"  - Overall CSV Table:      {artifacts.get('overall_csv')}")
    print(f"  - Full JSON Report:       {settings.BASE_DIR / 'ml_models' / 'experiments' / 'comparisons' / f'model_comparison_{args.dataset}.json'}")
    
    plots = artifacts.get("plots", [])
    if plots:
        print(f"  - Generated Plots ({len(plots)}):")
        for p in plots:
            print(f"      * {p}")
    print("=" * 78 + "\n")


if __name__ == "__main__":
    main()
