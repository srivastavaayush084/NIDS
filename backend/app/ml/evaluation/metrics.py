from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
)
from backend.app.core.logging import logger


@dataclass
class StandardizedMetrics:
    """
    Standardized container holding security classification metrics,
    confusion matrix elements, and computational latency measurements.
    """
    # Classification Metrics
    accuracy: Optional[float] = None
    balanced_accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None  # Detection Rate / True Positive Rate (TPR)
    f1_score: Optional[float] = None
    roc_auc: Optional[float] = None
    pr_auc: Optional[float] = None
    specificity: Optional[float] = None  # True Negative Rate (TNR)
    false_positive_rate: Optional[float] = None  # FPR
    false_negative_rate: Optional[float] = None  # FNR

    # Confusion Matrix Counts
    true_positives: int = 0
    true_negatives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    total_samples: int = 0

    # Computational Performance & Latency Metrics
    total_inference_time_ms: float = 0.0
    average_latency_ms: float = 0.0
    throughput_samples_per_sec: float = 0.0

    # Diagnostic metadata on missing / undefined metrics
    metric_diagnostics: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize metrics to a dictionary."""
        return {
            "classification": {
                "accuracy": round(self.accuracy, 4) if self.accuracy is not None else None,
                "balanced_accuracy": round(self.balanced_accuracy, 4) if self.balanced_accuracy is not None else None,
                "precision": round(self.precision, 4) if self.precision is not None else None,
                "recall": round(self.recall, 4) if self.recall is not None else None,
                "f1_score": round(self.f1_score, 4) if self.f1_score is not None else None,
                "roc_auc": round(self.roc_auc, 4) if self.roc_auc is not None else None,
                "pr_auc": round(self.pr_auc, 4) if self.pr_auc is not None else None,
                "specificity": round(self.specificity, 4) if self.specificity is not None else None,
                "false_positive_rate": round(self.false_positive_rate, 4) if self.false_positive_rate is not None else None,
                "false_negative_rate": round(self.false_negative_rate, 4) if self.false_negative_rate is not None else None,
            },
            "confusion_matrix": {
                "true_positives": self.true_positives,
                "true_negatives": self.true_negatives,
                "false_positives": self.false_positives,
                "false_negatives": self.false_negatives,
                "total_samples": self.total_samples,
            },
            "performance": {
                "total_inference_time_ms": round(self.total_inference_time_ms, 3),
                "average_latency_ms": round(self.average_latency_ms, 4),
                "throughput_samples_per_sec": round(self.throughput_samples_per_sec, 2),
            },
            "metric_diagnostics": self.metric_diagnostics,
        }


class StandardizedMetricsCalculator:
    """
    Calculates security classification and performance metrics across models
    with mathematical safeguards against single-class splits and divide-by-zero scenarios.
    """

    @classmethod
    def calculate_metrics(
        cls,
        y_true: Union[np.ndarray, pd.Series, List[int]],
        y_pred: Union[np.ndarray, pd.Series, List[int]],
        continuous_scores: Optional[Union[np.ndarray, pd.Series, List[float]]] = None,
        inference_time_ms: float = 0.0,
        unit_name: str = "samples",
    ) -> StandardizedMetrics:
        """
        Calculate full set of standardized metrics.

        Args:
            y_true: Ground truth binary labels (0 = Normal, 1 = Attack).
            y_pred: Predicted binary labels (0 = Normal, 1 = Attack).
            continuous_scores: Optional continuous anomaly scores/probabilities for ROC-AUC & PR-AUC.
            inference_time_ms: Total duration of inference execution in milliseconds.
            unit_name: 'samples' or 'sequences' for throughput calculation.
        """
        y_t = np.asarray(y_true, dtype=int).ravel()
        y_p = np.asarray(y_pred, dtype=int).ravel()
        n_samples = len(y_t)
        diagnostics: Dict[str, str] = {}

        if n_samples == 0:
            return StandardizedMetrics(
                metric_diagnostics={"error": "Empty evaluation dataset provided"}
            )

        # 1. Confusion Matrix Elements
        cm = confusion_matrix(y_t, y_p, labels=[0, 1])
        tn, fp, fn, tp = int(cm[0, 0]), int(cm[0, 1]), int(cm[1, 0]), int(cm[1, 1])

        # 2. Standard Classification Metrics
        try:
            acc = float(accuracy_score(y_t, y_p))
        except Exception as e:
            acc = None
            diagnostics["accuracy"] = str(e)

        try:
            balanced_acc = float(balanced_accuracy_score(y_t, y_p))
        except Exception as e:
            balanced_acc = None
            diagnostics["balanced_accuracy"] = str(e)

        try:
            prec = float(precision_score(y_t, y_p, zero_division=0))
        except Exception as e:
            prec = None
            diagnostics["precision"] = str(e)

        try:
            rec = float(recall_score(y_t, y_p, zero_division=0))
        except Exception as e:
            rec = None
            diagnostics["recall"] = str(e)

        try:
            f1 = float(f1_score(y_t, y_p, zero_division=0))
        except Exception as e:
            f1 = None
            diagnostics["f1_score"] = str(e)

        # 3. Security-Critical Specificity, FPR, and FNR
        specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else None
        if specificity is None:
            diagnostics["specificity"] = "No normal samples (y_true=0) in evaluation split"

        fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else None
        if fpr is None:
            diagnostics["false_positive_rate"] = "No normal samples (y_true=0) in evaluation split"

        fnr = float(fn / (fn + tp)) if (fn + tp) > 0 else None
        if fnr is None:
            diagnostics["false_negative_rate"] = "No attack samples (y_true=1) in evaluation split"

        # 4. ROC-AUC and PR-AUC Calculation
        roc_auc = None
        pr_auc = None

        if continuous_scores is not None:
            scores = np.asarray(continuous_scores, dtype=float).ravel()
            unique_classes = np.unique(y_t)
            if len(unique_classes) > 1:
                try:
                    roc_auc = float(roc_auc_score(y_t, scores))
                except Exception as e:
                    diagnostics["roc_auc"] = f"Calculation failed: {e}"

                try:
                    pr_auc = float(average_precision_score(y_t, scores))
                except Exception as e:
                    diagnostics["pr_auc"] = f"Calculation failed: {e}"
            else:
                diagnostics["roc_auc"] = f"Only one class present ({unique_classes[0]}), ROC-AUC mathematically undefined"
                diagnostics["pr_auc"] = f"Only one class present ({unique_classes[0]}), PR-AUC mathematically undefined"
        else:
            diagnostics["roc_auc"] = "Continuous scores not provided"
            diagnostics["pr_auc"] = "Continuous scores not provided"

        # 5. Throughput and Latency
        avg_latency = float(inference_time_ms / n_samples) if n_samples > 0 else 0.0
        throughput = float(n_samples / (inference_time_ms / 1000.0)) if inference_time_ms > 0 else 0.0

        return StandardizedMetrics(
            accuracy=acc,
            balanced_accuracy=balanced_acc,
            precision=prec,
            recall=rec,
            f1_score=f1,
            roc_auc=roc_auc,
            pr_auc=pr_auc,
            specificity=specificity,
            false_positive_rate=fpr,
            false_negative_rate=fnr,
            true_positives=tp,
            true_negatives=tn,
            false_positives=fp,
            false_negatives=fn,
            total_samples=n_samples,
            total_inference_time_ms=inference_time_ms,
            average_latency_ms=avg_latency,
            throughput_samples_per_sec=throughput,
            metric_diagnostics=diagnostics,
        )
