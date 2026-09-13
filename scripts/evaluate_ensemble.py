#!/usr/bin/env python
"""
Unified CLI Script to Calibrate, Evaluate, and Benchmark the Ensemble Detection and Risk Scoring Engine.

Models Fused:
1. Isolation Forest (Unsupervised Anomaly Detector)
2. Dense Autoencoder (Deep Learning Reconstruction Detector)
3. LSTM Autoencoder (Sequential Reconstruction Detector)
4. Random Forest (Supervised Baseline Classifier)

Usage Examples:
    python scripts/evaluate_ensemble.py --dataset synthetic --evaluation all
    python scripts/evaluate_ensemble.py --dataset nsl_kdd --threshold 55.0
    python scripts/evaluate_ensemble.py --dataset cicids2017 --weights "isolation_forest=0.3,autoencoder=0.3,lstm_autoencoder=0.2,random_forest=0.2"
    python scripts/evaluate_ensemble.py --dataset unsw_nb15 --unseen-attacks worms,shellcode --no-plots
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
from backend.app.ml.ensemble.ensemble_detector import EnsembleDetector
from backend.app.ml.evaluation.unified_evaluator import UnifiedModelEvaluator
from backend.app.ml.data.loaders.factory import list_supported_datasets
from backend.app.ml.data.utils.data_utils import load_dataframe, load_metadata, save_metadata, ensure_dir


def parse_args():
    parser = argparse.ArgumentParser(
        description="ZeroDayAI - Unified Ensemble Detection and Risk Scoring Engine Evaluation",
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
        "--threshold",
        type=float,
        default=50.0,
        help="Ensemble decision cutoff threshold (0.0 to 100.0).",
    )
    parser.add_argument(
        "--weights",
        type=str,
        default=None,
        help="Comma-separated model weights, e.g. 'isolation_forest=0.3,autoencoder=0.3,lstm_autoencoder=0.2,random_forest=0.2'",
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
        help="Disable generation of diagnostic visualization charts.",
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
        help="Custom output directory for evaluation artifacts.",
    )
    return parser.parse_args()


def parse_weights(weights_str: Optional[str]) -> Optional[dict]:
    if not weights_str:
        return None
    res = {}
    for pair in weights_str.split(","):
        if "=" in pair:
            k, v = pair.split("=", 1)
            res[k.strip().lower()] = float(v.strip())
    return res


def main():
    args = parse_args()
    logger.info("=" * 60)
    logger.info(f"STARTING ENSEMBLE EVALUATION: dataset='{args.dataset}', evaluation='{args.evaluation}'")
    logger.info("=" * 60)

    # 1. Resolve Test Split Data
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

    # Parse Unseen Attack Categories
    unseen_cats = [c.strip().lower() for c in args.unseen_attacks.split(",") if c.strip()]
    if not unseen_cats:
        split_summary_path = settings.PREPROCESSING_DIR / args.dataset / "split_summary.json"
        if split_summary_path.exists():
            try:
                split_info = load_metadata(split_summary_path)
                unseen_cats = split_info.get("unseen_categories", [])
            except Exception:
                unseen_cats = []

    # 2. Instantiate and Configure Ensemble Detector
    custom_weights = parse_weights(args.weights)
    ensemble = EnsembleDetector.load(
        dataset_name=args.dataset,
        custom_weights=custom_weights,
        decision_threshold=args.threshold,
    )

    # 3. Execute Unified Evaluation
    out_dir = (
        Path(args.output_dir)
        if args.output_dir
        else settings.BASE_DIR / "ml_models" / "experiments" / "ensemble"
    )
    ensure_dir(out_dir)

    try:
        report = UnifiedModelEvaluator.evaluate_model(
            model=ensemble,
            X_test=X_test,
            y_test_binary=y_test_binary,
            y_test_category=y_test_category,
            unseen_categories=unseen_cats,
            dataset_name=args.dataset,
            evaluation_type=args.evaluation,
            threshold=args.threshold,
            output_dir=out_dir,
        )
    except Exception as e:
        logger.error(f"Ensemble evaluation failed: {e}", exc_info=True)
        sys.exit(1)

    # 4. Print Formatted Terminal Summary
    std_m = report.get("standard_metrics", {}).get("classification", {})
    cm = report.get("standard_metrics", {}).get("confusion_matrix", {})
    perf = report.get("standard_metrics", {}).get("performance", {})
    unseen_m = report.get("scenario_metrics", {}).get("unseen_attack", {}).get("classification", {})

    print("\n" + "=" * 70)
    print(f"ENSEMBLE DETECTION & RISK SCORING EVALUATION RESULTS ({args.dataset.upper()})")
    print("=" * 70)
    print(f"Total Test Samples:          {report['sample_count']}")
    print(f"Decision Threshold:          {report['threshold_used']}")
    print(f"Unseen Zero-Day Categories:  {report['unseen_categories'] or 'None'}")
    print("-" * 70)
    print("STANDARD CLASSIFICATION BENCHMARK:")
    print(f"  Accuracy:                  {std_m.get('accuracy', 0.0):.4f}")
    print(f"  Balanced Accuracy:         {std_m.get('balanced_accuracy', 0.0):.4f}")
    print(f"  Precision:                 {std_m.get('precision', 0.0):.4f}")
    print(f"  Recall (Detection Rate):   {std_m.get('recall', 0.0):.4f}")
    print(f"  F1-Score:                  {std_m.get('f1_score', 0.0):.4f}")
    print(f"  ROC-AUC:                   {std_m.get('roc_auc')}")
    print(f"  PR-AUC:                    {std_m.get('pr_auc')}")
    print(f"  False Positive Rate (FPR): {std_m.get('false_positive_rate', 0.0):.4f}")
    print(f"  False Negative Rate (FNR): {std_m.get('false_negative_rate', 0.0):.4f}")
    print("-" * 70)
    print("CONFUSION MATRIX:")
    print(f"  True Negatives (TN):  {cm.get('true_negatives', 0):<5} | False Positives (FP): {cm.get('false_positives', 0)}")
    print(f"  False Negatives (FN): {cm.get('false_negatives', 0):<5} | True Positives (TP):  {cm.get('true_positives', 0)}")
    
    if unseen_m:
        print("-" * 70)
        print("UNSEEN ATTACK / ZERO-DAY PROXY BENCHMARK:")
        print(f"  Zero-Day Recall (TPR):     {unseen_m.get('recall', 'N/A')}")
        print(f"  Zero-Day F1-Score:         {unseen_m.get('f1_score', 'N/A')}")
        print(f"  Zero-Day Miss Rate (FNR):  {unseen_m.get('false_negative_rate', 'N/A')}")

    print("-" * 70)
    print("COMPUTATIONAL LATENCY:")
    print(f"  Total Inference Time:      {perf.get('total_inference_time_ms', 0.0):.2f} ms")
    print(f"  Average Latency / Sample:  {perf.get('average_latency_ms', 0.0):.4f} ms")
    print(f"  Throughput:                {perf.get('throughput_samples_per_sec', 0.0):.2f} samples/sec")
    print("=" * 70)
    print(f"Artifact Saved: {out_dir / f'ensemble_{args.dataset}_{args.evaluation}_result.json'}\n")


if __name__ == "__main__":
    main()
