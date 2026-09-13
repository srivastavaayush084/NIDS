import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
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

# Use non-interactive backend for matplotlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ml.models.isolation_forest import IsolationForestDetector
from backend.app.ml.data.utils.data_utils import ensure_dir, save_metadata


class IsolationForestEvaluator:
    """
    Comprehensive Evaluation and Diagnostics Engine for Isolation Forest Anomaly Detection.
    Computes security-critical metrics (FPR, FNR, Recall, F1, ROC-AUC), analyzes threshold sensitivity,
    benchmarks known vs unseen zero-day attacks, and renders diagnostic visualization charts.
    """

    @classmethod
    def evaluate(
        cls,
        detector: IsolationForestDetector,
        X_test: Union[np.ndarray, pd.DataFrame],
        y_test_binary: Union[np.ndarray, pd.Series],
        y_test_category: Optional[Union[np.ndarray, pd.Series]] = None,
        unseen_categories: Optional[List[str]] = None,
        threshold: Optional[float] = None,
        dataset_name: str = "synthetic",
        output_dir: Optional[Union[str, Path]] = None,
        generate_plots: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute full evaluation benchmark on test dataset.
        """
        logger.info(f"Evaluating IsolationForest on {len(X_test)} test samples (dataset='{dataset_name}')...")
        
        y_true = np.asarray(y_test_binary, dtype=int)
        anomaly_scores = detector.compute_anomaly_scores(X_test)
        raw_scores = detector.score_samples(X_test)
        
        eval_threshold = threshold if threshold is not None else detector.anomaly_threshold
        y_pred = (anomaly_scores >= eval_threshold).astype(int)

        # 1. Core Performance Metrics
        acc = float(accuracy_score(y_true, y_pred))
        prec = float(precision_score(y_true, y_pred, zero_division=0))
        rec = float(recall_score(y_true, y_pred, zero_division=0))
        f1 = float(f1_score(y_true, y_pred, zero_division=0))

        # ROC-AUC calculation
        try:
            auc = float(roc_auc_score(y_true, anomaly_scores))
        except Exception:
            auc = 0.5

        # Confusion Matrix breakdown: [[TN, FP], [FN, TP]]
        cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
        tn, fp, fn, tp = int(cm[0, 0]), int(cm[0, 1]), int(cm[1, 0]), int(cm[1, 1])

        # Security-critical rates
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
                }

            # Aggregate unseen vs known attack detection
            unseen_mask = y_cat_series.isin(unseen_set).to_numpy()
            known_attack_mask = ((y_true == 1) & (~unseen_mask))

            if np.any(unseen_mask):
                unseen_detected = np.sum(y_pred[unseen_mask] == 1)
                unseen_detection_rate = float(unseen_detected / np.sum(unseen_mask))

            if np.any(known_attack_mask):
                known_detected = np.sum(y_pred[known_attack_mask] == 1)
                known_detection_rate = float(known_detected / np.sum(known_attack_mask))

        # 3. Threshold Sensitivity Analysis
        threshold_analysis = []
        for test_th in np.linspace(10.0, 90.0, 17):
            t_pred = (anomaly_scores >= test_th).astype(int)
            t_prec = float(precision_score(y_true, t_pred, zero_division=0))
            t_rec = float(recall_score(y_true, t_pred, zero_division=0))
            t_f1 = float(f1_score(y_true, t_pred, zero_division=0))
            t_cm = confusion_matrix(y_true, t_pred, labels=[0, 1])
            t_fp, t_tn = int(t_cm[0, 1]), int(t_cm[0, 0])
            t_fpr = float(t_fp / (t_fp + t_tn)) if (t_fp + t_tn) > 0 else 0.0

            threshold_analysis.append({
                "threshold": round(float(test_th), 1),
                "precision": round(t_prec, 4),
                "recall": round(t_rec, 4),
                "f1_score": round(t_f1, 4),
                "false_positive_rate": round(t_fpr, 4),
            })

        # 4. Generate Output Directory & Plots
        exp_dir = Path(output_dir) if output_dir else settings.BASE_DIR / "ml_models" / "experiments"
        plots_dir = exp_dir / "plots"
        ensure_dir(exp_dir)
        ensure_dir(plots_dir)

        generated_plots: List[str] = []
        if generate_plots:
            generated_plots = cls._generate_visualizations(
                y_true, y_pred, anomaly_scores, eval_threshold, dataset_name, plots_dir
            )

        report = {
            "dataset": dataset_name,
            "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
            "threshold_used": eval_threshold,
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
            "threshold_sensitivity": threshold_analysis,
            "generated_plots": generated_plots,
        }

        # Save report JSON
        report_file = exp_dir / f"isolation_forest_{dataset_name}_evaluation.json"
        save_metadata(report, report_file)
        logger.info(f"Evaluation report saved to: {report_file}")

        logger.info(
            f"Evaluation Summary ({dataset_name}): Accuracy={acc:.4f}, Precision={prec:.4f}, "
            f"Recall={rec:.4f}, F1={f1:.4f}, ROC-AUC={auc:.4f}, FPR={fpr:.4f}"
        )
        return report

    @classmethod
    def _generate_visualizations(
        cls,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        anomaly_scores: np.ndarray,
        threshold: float,
        dataset_name: str,
        plots_dir: Path,
    ) -> List[str]:
        """Generate Confusion Matrix, ROC Curve, and Anomaly Score Distribution plots."""
        plot_files = []

        try:
            # 1. Confusion Matrix Plot
            cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
            plt.figure(figsize=(6, 5))
            plt.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
            plt.title(f"Confusion Matrix - Isolation Forest ({dataset_name})")
            plt.colorbar()
            tick_marks = np.arange(2)
            plt.xticks(tick_marks, ["Normal", "Anomaly"])
            plt.yticks(tick_marks, ["Normal", "Anomaly"])
            plt.xlabel("Predicted Label")
            plt.ylabel("True Label")
            
            thresh = cm.max() / 2.0
            for i in range(2):
                for j in range(2):
                    plt.text(j, i, format(cm[i, j], "d"),
                             horizontalalignment="center",
                             color="white" if cm[i, j] > thresh else "black")
            plt.tight_layout()
            cm_path = plots_dir / f"cm_{dataset_name}.png"
            plt.savefig(cm_path, dpi=150)
            plt.close()
            plot_files.append(str(cm_path))

            # 2. ROC Curve Plot
            fpr_curve, tpr_curve, _ = roc_curve(y_true, anomaly_scores)
            auc = roc_auc_score(y_true, anomaly_scores)
            plt.figure(figsize=(6, 5))
            plt.plot(fpr_curve, tpr_curve, color="darkorange", lw=2, label=f"ROC curve (AUC = {auc:.3f})")
            plt.plot([0, 1], [0, 1], color="navy", lw=1.5, linestyle="--", label="Random Chance")
            plt.xlim([0.0, 1.0])
            plt.ylim([0.0, 1.05])
            plt.xlabel("False Positive Rate (1 - Specificity)")
            plt.ylabel("True Positive Rate (Recall)")
            plt.title(f"ROC Curve - Isolation Forest ({dataset_name})")
            plt.legend(loc="lower right")
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            roc_path = plots_dir / f"roc_{dataset_name}.png"
            plt.savefig(roc_path, dpi=150)
            plt.close()
            plot_files.append(str(roc_path))

            # 3. Anomaly Score Distribution Plot
            plt.figure(figsize=(7, 5))
            norm_scores = anomaly_scores[y_true == 0]
            anom_scores = anomaly_scores[y_true == 1]
            if len(norm_scores) > 0:
                plt.hist(norm_scores, bins=15, alpha=0.6, label="Normal Baseline", color="green", density=True)
            if len(anom_scores) > 0:
                plt.hist(anom_scores, bins=15, alpha=0.6, label="Attack Traffic", color="red", density=True)
            plt.axvline(threshold, color="black", linestyle="--", linewidth=2, label=f"Decision Threshold ({threshold:.1f})")
            plt.title(f"Anomaly Score Distribution ({dataset_name})")
            plt.xlabel("Normalized Anomaly Score (0 - 100)")
            plt.ylabel("Density")
            plt.legend(loc="upper right")
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            dist_path = plots_dir / f"score_dist_{dataset_name}.png"
            plt.savefig(dist_path, dpi=150)
            plt.close()
            plot_files.append(str(dist_path))

        except Exception as e:
            logger.warning(f"Plot generation encountered error (non-fatal): {e}")

        return plot_files
