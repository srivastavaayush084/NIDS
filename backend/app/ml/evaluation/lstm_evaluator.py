from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    roc_curve,
    confusion_matrix,
)

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ml.models.lstm_autoencoder import LSTMAutoencoderDetector
from backend.app.ml.sequence.sequence_builder import SequenceBuilder
from backend.app.ml.data.utils.data_utils import ensure_dir, save_metadata


class LSTMEvaluator:
    """
    Evaluates trained LSTM Autoencoder sequential anomaly detection performance.
    Calculates sequence-level security metrics, reconstruction error distributions,
    and performs unseen attack category (zero-day proxy) evaluation.
    """

    @classmethod
    def evaluate(
        cls,
        detector: LSTMAutoencoderDetector,
        X_test_seq: np.ndarray,
        y_test_binary: np.ndarray,
        y_test_category: Optional[np.ndarray] = None,
        unseen_categories: Optional[List[str]] = None,
        threshold: Optional[float] = None,
        dataset_name: str = "generic",
        output_dir: Optional[Union[str, Path]] = None,
        generate_plots: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute comprehensive sequential evaluation across test sequences.
        """
        logger.info(
            f"Evaluating LSTM Autoencoder on {len(X_test_seq)} test sequences (dataset='{dataset_name}')..."
        )

        eval_threshold = threshold if threshold is not None else detector.reconstruction_threshold
        raw_errors = detector.compute_reconstruction_error(X_test_seq)
        y_pred = (raw_errors >= eval_threshold).astype(int)
        y_true = np.asarray(y_test_binary, dtype=int)

        # 1. Standard Sequence-Level Classification Metrics
        acc = float(accuracy_score(y_true, y_pred))
        prec = float(precision_score(y_true, y_pred, zero_division=0))
        rec = float(recall_score(y_true, y_pred, zero_division=0))
        f1 = float(f1_score(y_true, y_pred, zero_division=0))

        try:
            auc = float(roc_auc_score(y_true, raw_errors))
        except Exception:
            auc = 0.5

        # Confusion Matrix breakdown: [[TN, FP], [FN, TP]]
        cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
        tn, fp, fn, tp = int(cm[0, 0]), int(cm[0, 1]), int(cm[1, 0]), int(cm[1, 1])

        fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
        fnr = float(fn / (fn + tp)) if (fn + tp) > 0 else 0.0
        specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else 1.0

        # 2. Known vs Unseen Zero-Day Attack Breakdown
        category_breakdown: Dict[str, Dict[str, Any]] = {}
        unseen_detection_rate = None
        known_detection_rate = None

        if y_test_category is not None:
            y_cat_series = pd.Series(y_test_category).astype(str).str.lower().str.strip()
            unseen_set = set([c.lower().strip() for c in (unseen_categories or [])])

            for cat in y_cat_series.unique():
                cat_mask = (y_cat_series == cat).to_numpy()
                cat_total = int(np.sum(cat_mask))
                cat_detected = int(np.sum(y_pred[cat_mask] == 1))
                cat_rate = float(cat_detected / cat_total) if cat_total > 0 else 0.0

                category_breakdown[cat] = {
                    "total_samples": cat_total,
                    "detected_anomalies": cat_detected,
                    "detection_rate": round(cat_rate, 4),
                    "is_unseen_zero_day": cat in unseen_set,
                    "mean_reconstruction_error": round(float(np.mean(raw_errors[cat_mask])), 6),
                }

            unseen_mask = y_cat_series.isin(unseen_set).to_numpy()
            known_attack_mask = ((y_true == 1) & (~unseen_mask))

            if np.any(unseen_mask):
                unseen_detected = np.sum(y_pred[unseen_mask] == 1)
                unseen_detection_rate = float(unseen_detected / np.sum(unseen_mask))

            if np.any(known_attack_mask):
                known_detected = np.sum(y_pred[known_attack_mask] == 1)
                known_detection_rate = float(known_detected / np.sum(known_attack_mask))

        # 3. Output Directory & Plots
        exp_dir = Path(output_dir) if output_dir else settings.BASE_DIR / "ml_models" / "experiments"
        plots_dir = exp_dir / "plots"
        ensure_dir(exp_dir)
        ensure_dir(plots_dir)

        generated_plots: List[str] = []
        if generate_plots:
            generated_plots = cls._generate_visualizations(
                detector, y_true, y_pred, raw_errors, eval_threshold, dataset_name, plots_dir
            )

        report = {
            "model_name": "lstm_autoencoder",
            "dataset": dataset_name,
            "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
            "threshold_used": round(eval_threshold, 6),
            "threshold_strategy": detector.threshold_strategy,
            "sequence_length": detector.seq_len,
            "test_samples_total": len(y_true),
            "normal_samples": int(np.sum(y_true == 0)),
            "attack_samples": int(np.sum(y_true == 1)),
            "metrics": {
                "accuracy": round(acc, 4),
                "precision": round(prec, 4),
                "recall_detection_rate": round(rec, 4),
                "f1_score": round(f1, 4),
                "roc_auc": round(auc, 4),
                "specificity": round(specificity, 4),
                "false_positive_rate": round(fpr, 4),
                "false_negative_rate": round(fnr, 4),
            },
            "reconstruction_stats": {
                "normal_mean_mse": round(float(np.mean(raw_errors[y_true == 0])), 6) if np.any(y_true == 0) else 0.0,
                "normal_std_mse": round(float(np.std(raw_errors[y_true == 0])), 6) if np.any(y_true == 0) else 0.0,
                "attack_mean_mse": round(float(np.mean(raw_errors[y_true == 1])), 6) if np.any(y_true == 1) else 0.0,
                "attack_std_mse": round(float(np.std(raw_errors[y_true == 1])), 6) if np.any(y_true == 1) else 0.0,
            },
            "reconstruction_error_distribution": {
                "overall": {
                    "mean": round(float(np.mean(raw_errors)), 6),
                    "median": round(float(np.median(raw_errors)), 6),
                    "max": round(float(np.max(raw_errors)), 6),
                },
                "normal": {
                    "mean": round(float(np.mean(raw_errors[y_true == 0])), 6) if np.any(y_true == 0) else 0.0,
                    "median": round(float(np.median(raw_errors[y_true == 0])), 6) if np.any(y_true == 0) else 0.0,
                    "percentile_95": round(float(np.percentile(raw_errors[y_true == 0], 95)), 6) if np.any(y_true == 0) else 0.0,
                },
                "attack": {
                    "mean": round(float(np.mean(raw_errors[y_true == 1])), 6) if np.any(y_true == 1) else 0.0,
                    "median": round(float(np.median(raw_errors[y_true == 1])), 6) if np.any(y_true == 1) else 0.0,
                    "percentile_95": round(float(np.percentile(raw_errors[y_true == 1], 95)), 6) if np.any(y_true == 1) else 0.0,
                },
            },
            "confusion_matrix": {
                "true_negatives": tn,
                "false_positives": fp,
                "false_negatives": fn,
                "true_positives": tp,
            },
            "zero_day_evaluation": {
                "unseen_categories": unseen_categories or [],
                "unseen_attack_detection_rate": round(unseen_detection_rate, 4) if unseen_detection_rate is not None else "N/A",
                "known_attack_detection_rate": round(known_detection_rate, 4) if known_detection_rate is not None else "N/A",
                "category_breakdown": category_breakdown,
            },
            "generated_plots": generated_plots,
        }

        # Save report JSON
        report_file = exp_dir / f"lstm_autoencoder_{dataset_name}_evaluation.json"
        save_metadata(report, report_file)
        logger.info(f"LSTM Autoencoder evaluation report saved to: {report_file}")

        logger.info(
            f"LSTM Autoencoder Evaluation ({dataset_name}): Accuracy={acc:.4f}, Precision={prec:.4f}, "
            f"Recall={rec:.4f}, F1={f1:.4f}, ROC-AUC={auc:.4f}, FPR={fpr:.4f}"
        )
        return report

    @classmethod
    def _generate_visualizations(
        cls,
        detector: LSTMAutoencoderDetector,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        raw_errors: np.ndarray,
        threshold: float,
        dataset_name: str,
        plots_dir: Path,
    ) -> List[str]:
        """Generate Matplotlib diagnostic visualization plots."""
        plot_files = []

        # 1. Confusion Matrix Plot
        try:
            cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
            fig, ax = plt.subplots(figsize=(6, 5))
            cax = ax.matshow(cm, cmap=plt.cm.Blues, alpha=0.85)
            fig.colorbar(cax)
            for i in range(2):
                for j in range(2):
                    ax.text(x=j, y=i, s=str(cm[i, j]), va="center", ha="center", size="xx-large", weight="bold")
            ax.set_xticks([0, 1])
            ax.set_yticks([0, 1])
            ax.set_xticklabels(["Normal (0)", "Attack (1)"])
            ax.set_yticklabels(["Normal (0)", "Attack (1)"])
            ax.set_xlabel("Predicted Sequence Label", fontsize=11)
            ax.set_ylabel("True Sequence Label", fontsize=11)
            ax.set_title(f"LSTM Autoencoder Confusion Matrix ({dataset_name})", fontsize=12, pad=15)
            plt.tight_layout()
            cm_path = plots_dir / f"cm_lstm_{dataset_name}.png"
            plt.savefig(cm_path, dpi=150)
            plt.close(fig)
            plot_files.append(str(cm_path))
        except Exception as e:
            logger.warning(f"Failed to generate confusion matrix plot: {e}")

        # 2. ROC Curve Plot
        try:
            if len(np.unique(y_true)) > 1:
                fpr_vals, tpr_vals, _ = roc_curve(y_true, raw_errors)
                auc_score = roc_auc_score(y_true, raw_errors)
                fig, ax = plt.subplots(figsize=(6, 5))
                ax.plot(fpr_vals, tpr_vals, color="purple", lw=2, label=f"LSTM Autoencoder (AUC = {auc_score:.3f})")
                ax.plot([0, 1], [0, 1], color="navy", lw=1.5, linestyle="--", label="Random Chance")
                ax.set_xlim([0.0, 1.0])
                ax.set_ylim([0.0, 1.05])
                ax.set_xlabel("False Positive Rate", fontsize=11)
                ax.set_ylabel("True Positive Rate (Recall)", fontsize=11)
                ax.set_title(f"LSTM Autoencoder ROC Curve ({dataset_name})", fontsize=12)
                ax.legend(loc="lower right")
                ax.grid(alpha=0.3)
                plt.tight_layout()
                roc_path = plots_dir / f"roc_lstm_{dataset_name}.png"
                plt.savefig(roc_path, dpi=150)
                plt.close(fig)
                plot_files.append(str(roc_path))
        except Exception as e:
            logger.warning(f"Failed to generate ROC plot: {e}")

        # 3. Reconstruction Error Distribution Plot
        try:
            fig, ax = plt.subplots(figsize=(7, 5))
            normal_errors = raw_errors[y_true == 0]
            attack_errors = raw_errors[y_true == 1]

            if len(normal_errors) > 0:
                ax.hist(normal_errors, bins=25, alpha=0.6, color="forestgreen", label="Normal Sequences", density=True)
            if len(attack_errors) > 0:
                ax.hist(attack_errors, bins=25, alpha=0.6, color="crimson", label="Attack Sequences", density=True)

            ax.axvline(threshold, color="black", linestyle="--", lw=2, label=f"Threshold ({threshold:.4f})")
            ax.set_xlabel("Sequence Reconstruction Error (MSE)", fontsize=11)
            ax.set_ylabel("Density", fontsize=11)
            ax.set_title(f"LSTM Sequence Reconstruction Error Distribution ({dataset_name})", fontsize=12)
            ax.legend()
            ax.grid(alpha=0.3)
            plt.tight_layout()
            dist_path = plots_dir / f"recon_dist_lstm_{dataset_name}.png"
            plt.savefig(dist_path, dpi=150)
            plt.close(fig)
            plot_files.append(str(dist_path))
        except Exception as e:
            logger.warning(f"Failed to generate reconstruction error distribution plot: {e}")

        # 4. Training Loss Curve Plot
        try:
            if detector.history_ and "train_loss" in detector.history_ and detector.history_["train_loss"]:
                fig, ax = plt.subplots(figsize=(7, 4.5))
                epochs_range = range(1, len(detector.history_["train_loss"]) + 1)
                ax.plot(epochs_range, detector.history_["train_loss"], color="tab:blue", lw=2, label="Train MSE Loss")
                if "val_loss" in detector.history_ and detector.history_["val_loss"]:
                    val_range = range(1, len(detector.history_["val_loss"]) + 1)
                    ax.plot(val_range, detector.history_["val_loss"], color="tab:orange", lw=2, linestyle="--", label="Val MSE Loss")
                ax.set_xlabel("Epoch", fontsize=11)
                ax.set_ylabel("Mean Squared Error Loss", fontsize=11)
                ax.set_title(f"LSTM Autoencoder Training Loss Convergence ({dataset_name})", fontsize=12)
                ax.legend()
                ax.grid(alpha=0.3)
                plt.tight_layout()
                loss_path = plots_dir / f"loss_curve_lstm_{dataset_name}.png"
                plt.savefig(loss_path, dpi=150)
                plt.close(fig)
                plot_files.append(str(loss_path))
        except Exception as e:
            logger.warning(f"Failed to generate training loss curve plot: {e}")

        return plot_files
