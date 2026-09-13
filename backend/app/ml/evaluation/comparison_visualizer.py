from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import roc_curve, precision_recall_curve, confusion_matrix

from backend.app.core.logging import logger
from backend.app.ml.data.utils.data_utils import ensure_dir


class ComparisonVisualizer:
    """
    Renders multi-model comparative visualization charts including:
    - Multi-Model Metric Bar Charts (F1, Recall, Precision, FPR, FNR, Latency)
    - Combined Multi-Model ROC Curves
    - Combined Multi-Model Precision-Recall Curves
    - Normalized Anomaly Score Distributions (Normal vs Known vs Unseen Zero-Day)
    - Confusion Matrix Comparison Grids
    """

    MODEL_COLORS = {
        "isolation_forest": "#2563EB",  # Blue
        "autoencoder": "#10B981",       # Emerald Green
        "lstm_autoencoder": "#8B5CF6",  # Purple
        "random_forest": "#F59E0B",     # Amber / Orange
        "ensemble": "#EC4899",          # Pink / Magenta (Unified Ensemble)
    }

    MODEL_LABELS = {
        "isolation_forest": "Isolation Forest (Unsupervised)",
        "autoencoder": "Dense Autoencoder (Deep Learning)",
        "lstm_autoencoder": "LSTM Autoencoder (Sequential)",
        "random_forest": "Random Forest (Supervised Baseline)",
        "ensemble": "Unified Ensemble (Fused Risk Scorer)",
    }

    @classmethod
    def generate_all_comparison_plots(
        cls,
        evaluation_results: Dict[str, Dict[str, Any]],
        dataset_name: str,
        output_dir: Union[str, Path],
    ) -> List[str]:
        """
        Generate complete suite of multi-model comparison charts.

        Args:
            evaluation_results: Dict mapping model_name -> evaluation result dict (from UnifiedModelEvaluator).
            dataset_name: Name of dataset evaluated.
            output_dir: Target directory for plot artifacts.

        Returns:
            List of generated plot file paths.
        """
        out_p = Path(output_dir)
        ensure_dir(out_p)
        generated_files: List[str] = []

        try:
            # 1. Standard Scenario Metric Comparison Bar Chart
            p1 = cls.plot_metric_comparison_bars(
                evaluation_results=evaluation_results,
                dataset_name=dataset_name,
                scenario_key="standard_metrics",
                title_suffix="Standard Test Split",
                save_path=out_p / f"metrics_comparison_standard_{dataset_name}.png",
            )
            if p1:
                generated_files.append(str(p1))

            # 2. Unseen Attack (Zero-Day Proxy) Comparison Bar Chart
            has_unseen = any(
                "unseen_attack" in r.get("scenario_metrics", {})
                for r in evaluation_results.values()
            )
            if has_unseen:
                p2 = cls.plot_unseen_attack_comparison_bars(
                    evaluation_results=evaluation_results,
                    dataset_name=dataset_name,
                    save_path=out_p / f"metrics_comparison_unseen_attack_{dataset_name}.png",
                )
                if p2:
                    generated_files.append(str(p2))

            # 3. Combined Multi-Model ROC Curves
            p3 = cls.plot_combined_roc_curves(
                evaluation_results=evaluation_results,
                dataset_name=dataset_name,
                save_path=out_p / f"roc_combined_{dataset_name}.png",
            )
            if p3:
                generated_files.append(str(p3))

            # 4. Combined Multi-Model Precision-Recall Curves
            p4 = cls.plot_combined_pr_curves(
                evaluation_results=evaluation_results,
                dataset_name=dataset_name,
                save_path=out_p / f"pr_curve_combined_{dataset_name}.png",
            )
            if p4:
                generated_files.append(str(p4))

            # 5. Latency and Throughput Comparison Bar Chart
            p5 = cls.plot_latency_throughput_comparison(
                evaluation_results=evaluation_results,
                dataset_name=dataset_name,
                save_path=out_p / f"latency_comparison_{dataset_name}.png",
            )
            if p5:
                generated_files.append(str(p5))

            # 6. Confusion Matrix Grid
            p6 = cls.plot_confusion_matrix_grid(
                evaluation_results=evaluation_results,
                dataset_name=dataset_name,
                save_path=out_p / f"confusion_matrix_grid_{dataset_name}.png",
            )
            if p6:
                generated_files.append(str(p6))

        except Exception as e:
            logger.warning(f"Error during comparison plot generation (non-fatal): {e}")

        return generated_files

    @classmethod
    def plot_metric_comparison_bars(
        cls,
        evaluation_results: Dict[str, Dict[str, Any]],
        dataset_name: str,
        scenario_key: str = "standard_metrics",
        title_suffix: str = "Standard Test",
        save_path: Optional[Path] = None,
    ) -> Optional[Path]:
        """Multi-metric grouped bar chart comparing Accuracy, Precision, Recall, F1, ROC-AUC, FPR, FNR."""
        models = list(evaluation_results.keys())
        if not models:
            return None

        metrics_to_plot = ["accuracy", "precision", "recall", "f1_score", "roc_auc", "false_positive_rate", "false_negative_rate"]
        metric_display_names = ["Accuracy", "Precision", "Recall (TPR)", "F1-Score", "ROC-AUC", "FPR", "FNR"]

        data = {m: [] for m in models}
        for m in models:
            m_res = evaluation_results[m]
            if scenario_key == "standard_metrics":
                c_metrics = m_res.get("standard_metrics", {}).get("classification", {})
            else:
                c_metrics = m_res.get("scenario_metrics", {}).get(scenario_key, {}).get("classification", {})

            for met in metrics_to_plot:
                val = c_metrics.get(met)
                data[m].append(val if val is not None else 0.0)

        x = np.arange(len(metrics_to_plot))
        n_models = len(models)
        width = 0.8 / n_models

        plt.figure(figsize=(12, 6))
        for i, m in enumerate(models):
            offset = (i - n_models / 2 + 0.5) * width
            color = cls.MODEL_COLORS.get(m, "#64748B")
            label = cls.MODEL_LABELS.get(m, m)
            plt.bar(x + offset, data[m], width, label=label, color=color, alpha=0.9, edgecolor="black", linewidth=0.5)

        plt.title(f"Model Comparison - {title_suffix} ({dataset_name.upper()})", fontsize=14, fontweight="bold", pad=12)
        plt.xticks(x, metric_display_names, fontsize=10)
        plt.ylabel("Score / Rate (0.0 to 1.0)", fontsize=11)
        plt.ylim(0.0, 1.1)
        plt.grid(axis="y", linestyle="--", alpha=0.4)
        plt.legend(loc="upper right", framealpha=0.9, fontsize=9)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150)
            plt.close()
            return save_path
        plt.close()
        return None

    @classmethod
    def plot_unseen_attack_comparison_bars(
        cls,
        evaluation_results: Dict[str, Dict[str, Any]],
        dataset_name: str,
        save_path: Optional[Path] = None,
    ) -> Optional[Path]:
        """Comparison bar chart focused on Unseen Attack / Zero-Day Proxy Recall, F1, and FNR."""
        models = list(evaluation_results.keys())
        metrics_to_plot = ["recall", "f1_score", "false_negative_rate", "precision", "false_positive_rate"]
        metric_display_names = ["Zero-Day Recall (TPR)", "Zero-Day F1", "Zero-Day Miss Rate (FNR)", "Precision", "FPR"]

        data = {m: [] for m in models}
        for m in models:
            m_res = evaluation_results[m]
            unseen_m = m_res.get("scenario_metrics", {}).get("unseen_attack", {}).get("classification", {})
            for met in metrics_to_plot:
                val = unseen_m.get(met)
                data[m].append(val if val is not None else 0.0)

        x = np.arange(len(metrics_to_plot))
        n_models = len(models)
        width = 0.8 / n_models

        plt.figure(figsize=(11, 6))
        for i, m in enumerate(models):
            offset = (i - n_models / 2 + 0.5) * width
            color = cls.MODEL_COLORS.get(m, "#64748B")
            label = cls.MODEL_LABELS.get(m, m)
            plt.bar(x + offset, data[m], width, label=label, color=color, alpha=0.9, edgecolor="black", linewidth=0.5)

        plt.title(f"Unseen Attack / Zero-Day Proxy Evaluation ({dataset_name.upper()})", fontsize=13, fontweight="bold", pad=12)
        plt.xticks(x, metric_display_names, fontsize=10)
        plt.ylabel("Score / Rate (0.0 to 1.0)", fontsize=11)
        plt.ylim(0.0, 1.1)
        plt.grid(axis="y", linestyle="--", alpha=0.4)
        plt.legend(loc="upper right", framealpha=0.9, fontsize=9)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150)
            plt.close()
            return save_path
        plt.close()
        return None

    @classmethod
    def plot_combined_roc_curves(
        cls,
        evaluation_results: Dict[str, Dict[str, Any]],
        dataset_name: str,
        save_path: Optional[Path] = None,
    ) -> Optional[Path]:
        """Combined multi-model ROC Curve on identical axes."""
        plt.figure(figsize=(7, 6))
        plt.plot([0, 1], [0, 1], "k--", lw=1.5, label="Random Chance (AUC = 0.500)")

        for m, m_res in evaluation_results.items():
            raw_preds = m_res.get("raw_predictions", {})
            y_true = np.asarray(raw_preds.get("y_true", []))
            # Prefer anomaly scores or raw scores
            scores = raw_preds.get("anomaly_scores") or raw_preds.get("raw_scores")
            if scores is None or len(scores) == 0 or len(y_true) == 0:
                continue

            scores_arr = np.asarray(scores)
            if len(np.unique(y_true)) > 1:
                try:
                    fpr_curve, tpr_curve, _ = roc_curve(y_true, scores_arr)
                    auc_val = m_res.get("standard_metrics", {}).get("classification", {}).get("roc_auc")
                    auc_str = f"{auc_val:.3f}" if auc_val is not None else "N/A"
                    color = cls.MODEL_COLORS.get(m, "#64748B")
                    label = f"{cls.MODEL_LABELS.get(m, m)} (AUC = {auc_str})"
                    plt.plot(fpr_curve, tpr_curve, color=color, lw=2.2, label=label)
                except Exception as e:
                    logger.debug(f"Could not compute ROC curve for {m}: {e}")

        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel("False Positive Rate (1 - Specificity)", fontsize=11)
        plt.ylabel("True Positive Rate (Recall)", fontsize=11)
        plt.title(f"Combined ROC Curves - Multi-Model ({dataset_name.upper()})", fontsize=13, fontweight="bold", pad=10)
        plt.legend(loc="lower right", fontsize=8.5, framealpha=0.95)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150)
            plt.close()
            return save_path
        plt.close()
        return None

    @classmethod
    def plot_combined_pr_curves(
        cls,
        evaluation_results: Dict[str, Dict[str, Any]],
        dataset_name: str,
        save_path: Optional[Path] = None,
    ) -> Optional[Path]:
        """Combined multi-model Precision-Recall Curve."""
        plt.figure(figsize=(7, 6))

        for m, m_res in evaluation_results.items():
            raw_preds = m_res.get("raw_predictions", {})
            y_true = np.asarray(raw_preds.get("y_true", []))
            scores = raw_preds.get("anomaly_scores") or raw_preds.get("raw_scores")
            if scores is None or len(scores) == 0 or len(y_true) == 0:
                continue

            scores_arr = np.asarray(scores)
            if len(np.unique(y_true)) > 1:
                try:
                    p_curve, r_curve, _ = precision_recall_curve(y_true, scores_arr)
                    pr_auc = m_res.get("standard_metrics", {}).get("classification", {}).get("pr_auc")
                    pr_str = f"{pr_auc:.3f}" if pr_auc is not None else "N/A"
                    color = cls.MODEL_COLORS.get(m, "#64748B")
                    label = f"{cls.MODEL_LABELS.get(m, m)} (PR-AUC = {pr_str})"
                    plt.plot(r_curve, p_curve, color=color, lw=2.2, label=label)
                except Exception as e:
                    logger.debug(f"Could not compute PR curve for {m}: {e}")

        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel("Recall (Detection Rate)", fontsize=11)
        plt.ylabel("Precision", fontsize=11)
        plt.title(f"Combined Precision-Recall Curves ({dataset_name.upper()})", fontsize=13, fontweight="bold", pad=10)
        plt.legend(loc="lower left", fontsize=8.5, framealpha=0.95)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150)
            plt.close()
            return save_path
        plt.close()
        return None

    @classmethod
    def plot_latency_throughput_comparison(
        cls,
        evaluation_results: Dict[str, Dict[str, Any]],
        dataset_name: str,
        save_path: Optional[Path] = None,
    ) -> Optional[Path]:
        """Comparison of Inference Latency (ms/sample) and Throughput (samples/sec)."""
        models = list(evaluation_results.keys())
        latencies = []
        throughputs = []

        for m in models:
            perf = evaluation_results[m].get("standard_metrics", {}).get("performance", {})
            latencies.append(perf.get("average_latency_ms", 0.0))
            throughputs.append(perf.get("throughput_samples_per_sec", 0.0))

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

        colors = [cls.MODEL_COLORS.get(m, "#64748B") for m in models]
        labels = [cls.MODEL_LABELS.get(m, m).split(" (")[0] for m in models]

        # 1. Latency Bar Chart
        ax1.bar(labels, latencies, color=colors, alpha=0.85, edgecolor="black", linewidth=0.5)
        ax1.set_title("Average Inference Latency (Lower is Better)", fontsize=11, fontweight="bold")
        ax1.set_ylabel("Latency (ms / sample or sequence)", fontsize=10)
        ax1.grid(axis="y", linestyle="--", alpha=0.4)
        for i, v in enumerate(latencies):
            ax1.text(i, v + 0.01 * (max(latencies) if max(latencies) > 0 else 1), f"{v:.2f}ms", ha="center", fontsize=9)

        # 2. Throughput Bar Chart
        ax2.bar(labels, throughputs, color=colors, alpha=0.85, edgecolor="black", linewidth=0.5)
        ax2.set_title("Inference Throughput (Higher is Better)", fontsize=11, fontweight="bold")
        ax2.set_ylabel("Throughput (items / second)", fontsize=10)
        ax2.grid(axis="y", linestyle="--", alpha=0.4)
        for i, v in enumerate(throughputs):
            ax2.text(i, v + 0.01 * (max(throughputs) if max(throughputs) > 0 else 1), f"{int(v):,}", ha="center", fontsize=9)

        plt.suptitle(f"Computational Efficiency Benchmarks ({dataset_name.upper()})", fontsize=13, fontweight="bold", y=1.02)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            plt.close()
            return save_path
        plt.close()
        return None

    @classmethod
    def plot_confusion_matrix_grid(
        cls,
        evaluation_results: Dict[str, Dict[str, Any]],
        dataset_name: str,
        save_path: Optional[Path] = None,
    ) -> Optional[Path]:
        """2x2 Grid comparing Confusion Matrices of all evaluated models."""
        models = list(evaluation_results.keys())
        n = len(models)
        if n == 0:
            return None

        cols = 2
        rows = (n + 1) // 2
        fig, axes = plt.subplots(rows, cols, figsize=(10, 4.5 * rows))
        axes = np.array(axes).reshape(-1)

        for i, m in enumerate(models):
            ax = axes[i]
            cm_dict = evaluation_results[m].get("standard_metrics", {}).get("confusion_matrix", {})
            tn = cm_dict.get("true_negatives", 0)
            fp = cm_dict.get("false_positives", 0)
            fn = cm_dict.get("false_negatives", 0)
            tp = cm_dict.get("true_positives", 0)
            cm = np.array([[tn, fp], [fn, tp]])

            im = ax.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
            ax.set_title(f"{cls.MODEL_LABELS.get(m, m)}", fontsize=10, fontweight="bold")
            tick_marks = np.arange(2)
            ax.set_xticks(tick_marks)
            ax.set_yticks(tick_marks)
            ax.set_xticklabels(["Normal", "Attack"])
            ax.set_yticklabels(["Normal", "Attack"])
            ax.set_xlabel("Predicted")
            ax.set_ylabel("Actual")

            thresh = cm.max() / 2.0 if cm.max() > 0 else 1
            for r_idx in range(2):
                for c_idx in range(2):
                    ax.text(c_idx, r_idx, format(cm[r_idx, c_idx], "d"),
                            ha="center", va="center",
                            color="white" if cm[r_idx, c_idx] > thresh else "black",
                            fontsize=11, fontweight="bold")

        # Hide any unused subplots
        for j in range(n, len(axes)):
            axes[j].axis("off")

        plt.suptitle(f"Confusion Matrix Comparison ({dataset_name.upper()})", fontsize=13, fontweight="bold", y=1.00)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            plt.close()
            return save_path
        plt.close()
        return None
