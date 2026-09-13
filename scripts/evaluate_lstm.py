#!/usr/bin/env python
"""
CLI Script to Evaluate Trained Sequential LSTM Autoencoder Anomaly Detector.

Usage:
    python scripts/evaluate_lstm.py --dataset synthetic
    python scripts/evaluate_lstm.py --dataset nsl_kdd --unseen-attacks u2r,r2l
    python scripts/evaluate_lstm.py --dataset cicids2017 --unseen-attacks botnet,infiltration
    python scripts/evaluate_lstm.py --dataset unsw_nb15 --unseen-attacks worms,shellcode
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
from backend.app.ml.models.lstm_autoencoder import LSTMAutoencoderDetector
from backend.app.ml.sequence.sequence_builder import SequenceBuilder
from backend.app.ml.evaluation.lstm_evaluator import LSTMEvaluator
from backend.app.ml.data.loaders.factory import list_supported_datasets
from backend.app.ml.data.utils.data_utils import load_dataframe, load_metadata


def parse_args():
    parser = argparse.ArgumentParser(
        description="ZeroDayAI - Sequential LSTM Autoencoder Evaluation",
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
        "--version",
        type=str,
        default="1.0.0",
        help="Version of the trained model to evaluate.",
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default=None,
        help="Custom path to trained LSTM Autoencoder .pt file.",
    )
    parser.add_argument(
        "--sequence-length",
        type=int,
        default=None,
        help="Sequence window length (defaults to trained model sequence length).",
    )
    parser.add_argument(
        "--sequence-stride",
        type=int,
        default=1,
        help="Stride between test sequence windows.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Custom anomaly decision threshold (raw MSE). Defaults to learned threshold.",
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
        help="Disable generation of diagnostic matplotlib visualization plots.",
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
        help="Output directory for evaluation results and plots.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    logger.info("=" * 60)
    logger.info(f"STARTING LSTM AUTOENCODER EVALUATION: dataset='{args.dataset}'")
    logger.info("=" * 60)

    # 1. Resolve Model Path
    model_path = (
        Path(args.model_path)
        if args.model_path
        else settings.MODELS_DIR / f"lstm_autoencoder_{args.dataset}_v{args.version}.pt"
    )

    if not model_path.exists():
        logger.error(
            f"Trained model not found at {model_path}. "
            f"Please run: python scripts/train_lstm.py --dataset {args.dataset}"
        )
        sys.exit(1)

    detector = LSTMAutoencoderDetector.load(model_path)

    # 2. Resolve Test Split Data
    proc_dir = (
        Path(args.data_dir)
        if args.data_dir
        else settings.DATA_DIR / "processed" / args.dataset
    )

    X_test_path = proc_dir / "X_test.csv"
    y_test_path = proc_dir / "y_test.csv"

    if not X_test_path.exists() or not y_test_path.exists():
        logger.error(f"Test split data not found in {proc_dir}.")
        sys.exit(1)

    logger.info(f"Loading test split data from: {proc_dir}")
    X_test = load_dataframe(X_test_path)
    y_test_df = load_dataframe(y_test_path)

    y_test_binary = y_test_df["binary"] if "binary" in y_test_df.columns else y_test_df.iloc[:, 0]
    y_test_category = y_test_df["category"] if "category" in y_test_df.columns else None

    # 3. Construct Test Sequences
    seq_len = args.sequence_length or detector.seq_len
    seq_builder = SequenceBuilder(sequence_length=seq_len, stride=args.sequence_stride, label_aggregation="any")
    X_seq_test, y_seq_bin, y_seq_cat, _ = seq_builder.build_sequences(
        X=X_test,
        y_binary=y_test_binary,
        y_category=y_test_category,
    )

    if len(X_seq_test) == 0:
        logger.error(
            f"Test data has fewer rows ({len(X_test)}) than required sequence length ({seq_len})."
        )
        sys.exit(1)

    # Parse unseen categories
    unseen_cats = [c.strip().lower() for c in args.unseen_attacks.split(",") if c.strip()]
    if not unseen_cats:
        split_summary_path = settings.PREPROCESSING_DIR / args.dataset / "split_summary.json"
        if split_summary_path.exists():
            try:
                split_info = load_metadata(split_summary_path)
                unseen_cats = split_info.get("unseen_categories", [])
            except Exception:
                pass

    # 4. Execute Comprehensive Sequential Evaluation
    report = LSTMEvaluator.evaluate(
        detector=detector,
        X_test_seq=X_seq_test,
        y_test_binary=y_seq_bin,
        y_test_category=y_seq_cat,
        unseen_categories=unseen_cats,
        threshold=args.threshold,
        dataset_name=args.dataset,
        output_dir=args.output_dir,
        generate_plots=not args.no_plots,
    )

    metrics = report["metrics"]
    cm = report["confusion_matrix"]
    zd = report["zero_day_evaluation"]
    recon = report["reconstruction_error_distribution"]

    print("\n" + "=" * 60)
    print(f"LSTM AUTOENCODER EVALUATION RESULTS ({args.dataset.upper()})")
    print("=" * 60)
    print(f"Total Test Sequences:        {report['test_samples_total']} (Normal: {report['normal_samples']}, Attack: {report['attack_samples']})")
    print(f"Sequence Window Length:      {report['sequence_length']}")
    print(f"Anomaly Decision Threshold:  {report['threshold_used']}")
    print("-" * 60)
    print(f"Sequence Accuracy:           {metrics['accuracy']:.4f} ({metrics['accuracy']*100:.2f}%)")
    print(f"Sequence Precision:          {metrics['precision']:.4f}")
    print(f"Sequence Recall (Detection): {metrics['recall_detection_rate']:.4f} ({metrics['recall_detection_rate']*100:.2f}%)")
    print(f"Sequence F1-Score:           {metrics['f1_score']:.4f}")
    print(f"Sequence ROC-AUC:            {metrics['roc_auc']:.4f}")
    print(f"Sequence Specificity (TNR):  {metrics['specificity']:.4f}")
    print(f"False Positive Rate (FPR):   {metrics['false_positive_rate']:.4f} ({metrics['false_positive_rate']*100:.2f}%)")
    print(f"False Negative Rate (FNR):   {metrics['false_negative_rate']:.4f} ({metrics['false_negative_rate']*100:.2f}%)")
    print("-" * 60)
    print("Sequence Reconstruction Error (MSE) Statistics:")
    print(f"  Overall:  mean={recon['overall']['mean']:.4f}, median={recon['overall']['median']:.4f}, max={recon['overall']['max']:.4f}")
    print(f"  Normal:   mean={recon['normal']['mean']:.4f}, median={recon['normal']['median']:.4f}, 95th={recon['normal']['percentile_95']:.4f}")
    print(f"  Attack:   mean={recon['attack']['mean']:.4f}, median={recon['attack']['median']:.4f}, 95th={recon['attack']['percentile_95']:.4f}")
    print("-" * 60)
    print("Confusion Matrix (Sequence-Level):")
    print(f"  True Negatives (TN):  {cm['true_negatives']:<6} | False Positives (FP): {cm['false_positives']}")
    print(f"  False Negatives (FN): {cm['false_negatives']:<6} | True Positives (TP):  {cm['true_positives']}")
    print("-" * 60)
    print("Zero-Day & Attack Category Breakdown (Sequence-Level):")
    print(f"  Unseen Zero-Day Categories:   {zd['unseen_categories']}")
    print(f"  Unseen Attack Detection Rate: {zd['unseen_attack_detection_rate']}")
    print(f"  Known Attack Detection Rate:  {zd['known_attack_detection_rate']}")
    for cat, info in zd["category_breakdown"].items():
        tag = "[UNSEEN ZERO-DAY]" if info["is_unseen_zero_day"] else "[KNOWN]"
        print(f"    - {cat:<20} {tag:<18}: {info['detected_anomalies']}/{info['total_samples']} detected ({info['detection_rate']*100:.1f}%)")
    print("-" * 60)
    if report["generated_plots"]:
        print("Generated Diagnostic Plots:")
        for plot in report["generated_plots"]:
            print(f"  - {plot}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
