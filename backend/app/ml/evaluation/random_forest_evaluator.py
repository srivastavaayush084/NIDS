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
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    roc_curve,
    precision_recall_curve,
    average_precision_score,
    confusion_matrix,
)

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ml.models.random_forest import RandomForestClassifierModel
from backend.app.ml.data.utils.data_utils import ensure_dir, save_metadata


class RandomForestEvaluator:
    """
    Evaluates trained Supervised Random Forest Classifier performance.
    Calculates classification metrics, PR-AUC, Gini feature importances,
    and performs comparative unseen attack category (zero-day proxy) evaluation.
    """

    @classmethod
    def evaluate(
        cls,
        model: RandomForestClassifierModel,
        X_test: Union[np.ndarray, pd.DataFrame],
        y_test_binary: Union[np.ndarray, pd.Series],
        y_test_category: Optional[Union[np.ndarray, pd.Series]] = None,
        unseen_categories: Optional[List[str]] = None,
        threshold: Optional[float] = None,
        dataset_name: str = "generic",
        output_dir: Optional[Union[str, Path]] = None,
        generate_plots: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute comprehensive evaluation on labeled test split.
        """
        logger.info(f"Evaluating Random Forest on {len(X_test)} test samples (dataset='{dataset_name}')...")

        eval_threshold = threshold if threshold is not None else model.decision_threshold
        probs = model.predict_proba(X_test)
        prob_attack = probs[:, 1]
        y_pred = (prob_attack >= eval_threshold).astype(int)
        y_true = np.asarray(y_test_binary, dtype=int).ravel()

        # 1. Standard Supervised Classification Metrics
        acc = float(accuracy_score(y_true, y_pred))
        balanced_acc = float(balanced_accuracy_score(y_true, y_pred))
        prec = float(precision_score(y_true, y_pred, zero_division=0))
        rec = float(recall_score(y_true, y_pred, zero_division=0))
        f1 = float(f1_score(y_true, y_pred, zero_division=0))

        # ROC-AUC and PR-AUC
        if len(np.unique(y_true)) > 1:
            try:
                auc_score = float(roc_auc_score(y_true, prob_attack))
            except Exception:
                auc_score = float("nan")
            try:
                pr_auc_score = float(average_precision_score(y_true, prob_attack))
            except Exception:
                pr_auc_score = float("nan")
        else:
            auc_score = float("nan")
            pr_auc_score = float("nan")

        # Confusion Matrix breakdown: [[TN, FP], [FN, TP]]
        cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
        tn, fp, fn, tp = int(cm[0, 0]), int(cm[0, 1]), int(cm[1, 0]), int(cm[1, 1])

        fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
        fnr = float(fn / (fn + tp)) if (fn + tp) > 0 else 0.0
        specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else 1.0

        # 2. Known vs Unseen Attack Category Breakdown
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
                    "mean_attack_probability": round(float(np.mean(prob_attack[cat_mask])), 6),
                }

            unseen_mask = y_cat_series.isin(unseen_set).to_numpy()
            known_attack_mask = ((y_true == 1) & (~unseen_mask))

            if np.any(unseen_mask):
                unseen_detected = np.sum(y_pred[unseen_mask] == 1)
                unseen_detection_rate = float(unseen_detected / np.sum(unseen_mask))

            if np.any(known_attack_mask):
                known_detected = np.sum(y_pred[known_attack_mask] == 1)
                known_detection_rate = float(known_detected / np.sum(known_attack_mask))

        # 3. Feature Importance Extraction
        feature_importances = model.get_feature_importances(top_n=20)

        # 4. Output Directory & Plots
        exp_dir = Path(output_dir) if output_dir else settings.BASE_DIR / "ml_models" / "experiments"
        plots_dir = exp_dir / "plots"
        ensure_dir(exp_dir)
        ensure_dir(plots_dir)

        generated_plots: List[str] = []
        if generate_plots:
            generated_plots = cls._generate_visualizations(
                model=model,
                y_true=y_true,
                y_pred=y_pred,
                prob_attack=prob_attack,
                threshold=eval_threshold,
                dataset_name=dataset_name,
                plots_dir=plots_dir,
                feature_importances=feature_importances,
            )

        report = {
            "model_name": "random_forest",
            "model_type": "supervised_classifier_baseline",
            "dataset": dataset_name,
            "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
            "threshold_used": round(eval_threshold, 4),
            "threshold_strategy": model.threshold_strategy,
            "test_samples_total": len(y_true),
            "class_distribution": {
                "normal": int(np.sum(y_true == 0)),
                "attack": int(np.sum(y_true == 1)),
            },
            "metrics": {
                "accuracy": round(acc, 4),
                "balanced_accuracy": round(balanced_acc, 4),
                "precision": round(prec, 4),
                "recall_detection_rate": round(rec, 4),
                "f1_score": round(f1, 4),
                "roc_auc": round(auc_score, 4) if not np.isnan(auc_score) else "N/A",
                "pr_auc": round(pr_auc_score, 4) if not np.isnan(pr_auc_score) else "N/A",
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
            "top_feature_importances": feature_importances[:10],
            "generated_plots": generated_plots,
        }

        # Save report JSON
        report_file = exp_dir / f"random_forest_{dataset_name}_evaluation.json"
        save_metadata(report, report_file)
        logger.info(f"Random Forest evaluation report saved to: {report_file}")

        logger.info(
            f"Random Forest Evaluation ({dataset_name}): Accuracy={acc:.4f}, Precision={prec:.4f}, "
            f"Recall={rec:.4f}, F1={f1:.4f}, ROC-AUC={auc_score if not np.isnan(auc_score) else 'N/A'}, FPR={fpr:.4f}"
        )
        return report

    @classmethod
    def _generate_visualizations(
        cls,
        model: RandomForestClassifierModel,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        prob_attack: np.ndarray,
        threshold: float,
        dataset_name: str,
        plots_dir: Path,
        feature_importances: List[Dict[str, Any]],
    ) -> List[str]:
        """Generate Matplotlib diagnostic visualization plots for Random Forest."""
        plot_files = []

        # 1. Confusion Matrix Plot
        try:
            cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
            fig, ax = plt.subplots(figsize=(6, 5))
            cax = ax.matshow(cm, cmap=plt.cm.Greens, alpha=0.85)
            fig.colorbar(cax)
            for i in range(2):
                for j in range(2):
                    ax.text(x=j, y=i, s=str(cm[i, j]), va="center", ha="center", size="xx-large", weight="bold")
            ax.set_xticks([0, 1])
            ax.set_yticks([0, 1])
            ax.set_xticklabels(["Normal (0)", "Attack (1)"])
            ax.set_yticklabels(["Normal (0)", "Attack (1)"])
            ax.set_xlabel("Predicted Label", fontsize=11)
            ax.set_ylabel("True Label", fontsize=11)
            ax.set_title(f"Random Forest Confusion Matrix ({dataset_name})", fontsize=12, pad=15)
            plt.tight_layout()
            cm_path = plots_dir / f"cm_rf_{dataset_name}.png"
            plt.savefig(cm_path, dpi=150)
            plt.close(fig)
            plot_files.append(str(cm_path))
        except Exception as e:
            logger.warning(f"Failed to generate confusion matrix plot: {e}")

        # 2. ROC Curve Plot
        try:
            if len(np.unique(y_true)) > 1:
                fpr_vals, tpr_vals, _ = roc_curve(y_true, prob_attack)
                auc_val = roc_auc_score(y_true, prob_attack)
                fig, ax = plt.subplots(figsize=(6, 5))
                ax.plot(fpr_vals, tpr_vals, color="darkgreen", lw=2, label=f"Random Forest (AUC = {auc_val:.3f})")
                ax.plot([0, 1], [0, 1], color="navy", lw=1.5, linestyle="--", label="Random Chance")
                ax.set_xlim([0.0, 1.0])
                ax.set_ylim([0.0, 1.05])
                ax.set_xlabel("False Positive Rate", fontsize=11)
                ax.set_ylabel("True Positive Rate (Recall)", fontsize=11)
                ax.set_title(f"Random Forest ROC Curve ({dataset_name})", fontsize=12)
                ax.legend(loc="lower right")
                ax.grid(alpha=0.3)
                plt.tight_layout()
                roc_path = plots_dir / f"roc_rf_{dataset_name}.png"
                plt.savefig(roc_path, dpi=150)
                plt.close(fig)
                plot_files.append(str(roc_path))
        except Exception as e:
            logger.warning(f"Failed to generate ROC plot: {e}")

        # 3. Precision-Recall Curve Plot
        try:
            if len(np.unique(y_true)) > 1 and np.sum(y_true == 1) > 0:
                prec_vals, rec_vals, _ = precision_recall_curve(y_true, prob_attack)
                pr_auc = average_precision_score(y_true, prob_attack)
                fig, ax = plt.subplots(figsize=(6, 5))
                ax.plot(rec_vals, prec_vals, color="teal", lw=2, label=f"Random Forest (PR-AUC = {pr_auc:.3f})")
                ax.set_xlabel("Recall", fontsize=11)
                ax.set_ylabel("Precision", fontsize=11)
                ax.set_title(f"Random Forest Precision-Recall Curve ({dataset_name})", fontsize=12)
                ax.legend(loc="lower left")
                ax.grid(alpha=0.3)
                plt.tight_layout()
                pr_path = plots_dir / f"pr_curve_rf_{dataset_name}.png"
                plt.savefig(pr_path, dpi=150)
                plt.close(fig)
                plot_files.append(str(pr_path))
        except Exception as e:
            logger.warning(f"Failed to generate PR curve plot: {e}")

        # 4. Feature Importance Horizontal Bar Chart
        try:
            if feature_importances:
                top_features = feature_importances[:15]
                names = [f["feature"] for f in reversed(top_features)]
                scores = [f["importance"] for f in reversed(top_features)]

                fig, ax = plt.subplots(figsize=(8, max(4, len(names) * 0.35)))
                y_pos = np.arange(len(names))
                ax.barh(y_pos, scores, color="forestgreen", alpha=0.85)
                ax.set_yticks(y_pos)
                ax.set_yticklabels(names, fontsize=10)
                ax.set_xlabel("Gini Importance Score", fontsize=11)
                ax.set_title(f"Top {len(names)} Features by Random Forest Importance ({dataset_name})", fontsize=12)
                ax.grid(alpha=0.3, axis="x")
                plt.tight_layout()
                fi_path = plots_dir / f"feature_importance_rf_{dataset_name}.png"
                plt.savefig(fi_path, dpi=150)
                plt.close(fig)
                plot_files.append(str(fi_path))
        except Exception as e:
            logger.warning(f"Failed to generate feature importance plot: {e}")

        # 5. Attack Probability Score Distribution Plot
        try:
            fig, ax = plt.subplots(figsize=(7, 5))
            norm_probs = prob_attack[y_true == 0]
            att_probs = prob_attack[y_true == 1]

            if len(norm_probs) > 0:
                ax.hist(norm_probs, bins=25, alpha=0.6, color="forestgreen", label="Normal Samples", density=True)
            if len(att_probs) > 0:
                ax.hist(att_probs, bins=25, alpha=0.6, color="crimson", label="Attack Samples", density=True)

            ax.axvline(threshold, color="black", linestyle="--", lw=2, label=f"Threshold ({threshold:.2f})")
            ax.set_xlabel("Predicted Attack Probability P(y=1)", fontsize=11)
            ax.set_ylabel("Density", fontsize=11)
            ax.set_title(f"Random Forest Probability Distribution ({dataset_name})", fontsize=12)
            ax.legend()
            ax.grid(alpha=0.3)
            plt.tight_layout()
            dist_path = plots_dir / f"score_dist_rf_{dataset_name}.png"
            plt.savefig(dist_path, dpi=150)
            plt.close(fig)
            plot_files.append(str(dist_path))
        except Exception as e:
            logger.warning(f"Failed to generate score distribution plot: {e}")

        return plot_files
