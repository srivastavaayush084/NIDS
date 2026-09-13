#!/usr/bin/env python
"""
CLI Script to Train Sequential LSTM Autoencoder Anomaly Detector.

Usage:
    python scripts/train_lstm.py --dataset synthetic --epochs 30 --sequence-length 5 --latent-dim 8
    python scripts/train_lstm.py --dataset nsl_kdd --epochs 40 --sequence-length 10 --latent-dim 16
    python scripts/train_lstm.py --dataset cicids2017 --epochs 40 --sequence-length 10 --latent-dim 16
    python scripts/train_lstm.py --dataset unsw_nb15 --epochs 40 --sequence-length 10 --latent-dim 16
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
from backend.app.ml.training.lstm_trainer import LSTMTrainer
from backend.app.ml.data.loaders.factory import list_supported_datasets
from backend.app.ml.data.utils.data_utils import load_dataframe


def parse_args():
    parser = argparse.ArgumentParser(
        description="ZeroDayAI - Sequential LSTM Autoencoder Training",
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
        "--sequence-length",
        type=int,
        default=settings.LSTM_SEQUENCE_LENGTH,
        help="Number of consecutive timesteps per sliding window.",
    )
    parser.add_argument(
        "--sequence-stride",
        type=int,
        default=settings.LSTM_SEQUENCE_STRIDE,
        help="Stride step size between consecutive sliding sequence windows.",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=settings.LSTM_EPOCHS,
        help="Maximum training epochs.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=settings.LSTM_BATCH_SIZE,
        help="Training batch size.",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=settings.LSTM_LEARNING_RATE,
        help="Learning rate for Adam optimizer.",
    )
    parser.add_argument(
        "--encoder-units",
        type=int,
        default=settings.LSTM_ENCODER_UNITS,
        help="Number of hidden units in LSTM encoder.",
    )
    parser.add_argument(
        "--latent-dim",
        type=int,
        default=settings.LSTM_LATENT_DIM,
        help="Bottleneck latent representation dimension.",
    )
    parser.add_argument(
        "--decoder-units",
        type=int,
        default=settings.LSTM_DECODER_UNITS,
        help="Number of hidden units in LSTM decoder.",
    )
    parser.add_argument(
        "--num-layers",
        type=int,
        default=settings.LSTM_NUM_LAYERS,
        help="Number of stacked LSTM layers in encoder and decoder.",
    )
    parser.add_argument(
        "--dropout",
        type=float,
        default=settings.LSTM_DROPOUT,
        help="Dropout probability between layers.",
    )
    parser.add_argument(
        "--threshold-percentile",
        type=float,
        default=settings.LSTM_THRESHOLD_PERCENTILE,
        help="Reconstruction error percentile on normal validation sequences for anomaly threshold.",
    )
    parser.add_argument(
        "--threshold-strategy",
        type=str,
        default="percentile",
        choices=["percentile", "std_dev"],
        help="Threshold determination strategy.",
    )
    parser.add_argument(
        "--patience",
        type=int,
        default=settings.LSTM_EARLY_STOPPING_PATIENCE,
        help="Early stopping patience (epochs without validation loss improvement).",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=settings.LSTM_RANDOM_SEED,
        help="Deterministic random seed.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        choices=["auto", "cpu", "cuda"],
        help="Device to train on ('auto', 'cpu', 'cuda').",
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
    logger.info(f"STARTING LSTM AUTOENCODER TRAINING: dataset='{args.dataset}'")
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

    # 2. Instantiate and Execute Trainer
    trainer = LSTMTrainer(
        dataset_name=args.dataset,
        version=args.version,
        sequence_length=args.sequence_length,
        sequence_stride=args.sequence_stride,
        encoder_units=args.encoder_units,
        latent_dim=args.latent_dim,
        decoder_units=args.decoder_units,
        num_layers=args.num_layers,
        dropout=args.dropout,
        learning_rate=args.learning_rate,
        batch_size=args.batch_size,
        epochs=args.epochs,
        early_stopping_patience=args.patience,
        threshold_percentile=args.threshold_percentile,
        threshold_strategy=args.threshold_strategy,
        random_seed=args.random_state,
        device=args.device,
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
    logger.info("LSTM AUTOENCODER TRAINING COMPLETED SUCCESSFULLY!")
    logger.info(f"Model File:        {model_path}")
    logger.info(f"Metadata File:    {meta_path}")
    logger.info(f"Learned Threshold (Raw MSE): {trainer.detector.optimal_threshold_:.6f}")
    logger.info(f"Calibrated Threshold (Score): {trainer.detector.optimal_score_threshold_:.2f}/100")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
