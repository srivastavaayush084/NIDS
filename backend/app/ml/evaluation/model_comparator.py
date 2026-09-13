from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ml.evaluation.unified_evaluator import UnifiedModelEvaluator
from backend.app.ml.evaluation.comparison_visualizer import ComparisonVisualizer
from backend.app.ml.data.utils.data_utils import ensure_dir, save_metadata, load_dataframe, load_metadata


class ModelComparator:
    """
    Unified Orchestrator for Multi-Model Evaluation and Comparative Benchmarking across:
    1. Isolation Forest (Unsupervised Anomaly Detector)
    2. Dense Autoencoder (Deep Learning Reconstruction Detector)
    3. LSTM Autoencoder (Sequential Reconstruction Detector)
    4. Random Forest (Supervised Baseline Classifier)

    Produces standardized comparison matrices, multi-dimensional rankings,
    and publication-grade comparative visual artifacts.
    """

    ALL_MODELS = [
        "isolation_forest",
        "autoencoder",
        "lstm_autoencoder",
        "random_forest",
        "ensemble",
    ]

    DEFAULT_COMPOSITE_WEIGHTS = {
        "unseen_recall": 0.35,  # Zero-Day Breach Prevention
        "standard_f1": 0.25,    # General Detection Quality
        "precision": 0.20,      # Alert Actionability / False Positive Control
        "fpr_suppression": 0.10,# Normal Traffic Non-Interference (1 - FPR)
        "efficiency": 0.10,     # Inference Latency Optimization
    }

    @classmethod
    def compare_models(
        cls,
        dataset_name: str = "synthetic",
        models_to_evaluate: Optional[List[str]] = None,
        X_test: Optional[Union[np.ndarray, pd.DataFrame]] = None,
        y_test_binary: Optional[Union[np.ndarray, pd.Series]] = None,
        y_test_category: Optional[Union[np.ndarray, pd.Series]] = None,
        unseen_categories: Optional[List[str]] = None,
        evaluation_type: str = "all",
        output_dir: Optional[Union[str, Path]] = None,
        generate_plots: bool = True,
        composite_weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Execute full cross-model comparison benchmark.

        Args:
            dataset_name: Dataset identifier (e.g. 'synthetic', 'nsl_kdd', 'cicids2017', 'unsw_nb15').
            models_to_evaluate: Subset of models to benchmark. Defaults to all 4 models.
            X_test: Optional pre-loaded test feature matrix.
            y_test_binary: Optional pre-loaded test binary labels.
            y_test_category: Optional pre-loaded attack category labels.
            unseen_categories: List of withheld attack categories for zero-day proxy test.
            evaluation_type: 'standard', 'unseen_attack', or 'all'.
            output_dir: Target directory for comparison artifacts.
            generate_plots: Whether to generate diagnostic comparison charts.
            composite_weights: Custom weights for multi-dimensional composite ranking.

        Returns:
            Comprehensive comparison dictionary with results, tables, rankings, and plot paths.
        """
        logger.info("=" * 60)
        logger.info(f"STARTING UNIFIED MODEL COMPARISON: dataset='{dataset_name}'")
        logger.info("=" * 60)

        # 1. Resolve Output Directory
        exp_dir = (
            Path(output_dir)
            if output_dir
            else settings.BASE_DIR / "ml_models" / "experiments" / "comparisons"
        )
        plots_dir = exp_dir / "plots"
        ensure_dir(exp_dir)
        ensure_dir(plots_dir)

        # 2. Resolve Test Data if not passed explicitly
        if X_test is None or y_test_binary is None:
            proc_dir = settings.DATA_DIR / "processed" / dataset_name
            X_test_path = proc_dir / "X_test.csv"
            y_test_path = proc_dir / "y_test.csv"

            if not X_test_path.exists() or not y_test_path.exists():
                raise FileNotFoundError(
                    f"Processed test split not found in {proc_dir}. "
                    f"Please run: python scripts/prepare_dataset.py --dataset {dataset_name}"
                )

            X_test = load_dataframe(X_test_path)
            y_df = load_dataframe(y_test_path)
            y_test_binary = y_df["binary"] if "binary" in y_df.columns else y_df.iloc[:, 0]
            y_test_category = y_df["category"] if "category" in y_df.columns else None

            # Look up unseen categories from split summary if not provided
            if unseen_categories is None:
                split_summary_path = settings.PREPROCESSING_DIR / dataset_name / "split_summary.json"
                if split_summary_path.exists():
                    try:
                        split_info = load_metadata(split_summary_path)
                        unseen_categories = split_info.get("unseen_categories", [])
                    except Exception:
                        unseen_categories = []

        unseen_cats = unseen_categories or []
        model_list = [
            UnifiedModelEvaluator.normalize_model_name(m)
            for m in (models_to_evaluate or cls.ALL_MODELS)
        ]

        # 3. Evaluate Each Selected Model
        evaluation_results: Dict[str, Dict[str, Any]] = {}
        for m_name in model_list:
            try:
                logger.info(f"--> Evaluating model: {m_name}...")
                m_res = UnifiedModelEvaluator.evaluate_model(
                    model=m_name,
                    X_test=X_test,
                    y_test_binary=y_test_binary,
                    y_test_category=y_test_category,
                    unseen_categories=unseen_cats,
                    dataset_name=dataset_name,
                    evaluation_type=evaluation_type,
                    output_dir=None,
                )
                evaluation_results[m_name] = m_res
            except Exception as e:
                logger.error(f"Failed to evaluate model '{m_name}': {e}", exc_info=True)

        if not evaluation_results:
            raise RuntimeError("No models were successfully evaluated.")

        # 4. Generate Standardized Comparison Tables (DataFrames)
        std_df = cls._build_standard_comparison_table(evaluation_results, dataset_name)
        unseen_df = cls._build_unseen_comparison_table(evaluation_results, dataset_name)
        overall_df = cls._build_overall_comparison_table(std_df, unseen_df)

        # Save CSV Artifacts
        std_csv_path = exp_dir / "standard_comparison.csv"
        unseen_csv_path = exp_dir / "unseen_attack_comparison.csv"
        overall_csv_path = exp_dir / "overall_comparison.csv"

        std_df.to_csv(std_csv_path, index=False)
        unseen_df.to_csv(unseen_csv_path, index=False)
        overall_df.to_csv(overall_csv_path, index=False)

        # 5. Compute Multi-Dimensional Model Rankings
        weights = composite_weights or cls.DEFAULT_COMPOSITE_WEIGHTS
        rankings = cls._compute_rankings(evaluation_results, weights)

        # 6. Generate Comparative Visualization Plots
        generated_plots: List[str] = []
        if generate_plots:
            generated_plots = ComparisonVisualizer.generate_all_comparison_plots(
                evaluation_results=evaluation_results,
                dataset_name=dataset_name,
                output_dir=plots_dir,
            )

        # 7. Assemble Comprehensive Comparison Report
        comparison_report = {
            "comparison_id": f"comp_{dataset_name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dataset": dataset_name,
            "evaluated_models": list(evaluation_results.keys()),
            "total_test_samples": len(X_test),
            "unseen_categories_evaluated": unseen_cats,
            "rankings": rankings,
            "comparison_tables": {
                "standard": std_df.to_dict(orient="records"),
                "unseen_attack": unseen_df.to_dict(orient="records"),
                "overall": overall_df.to_dict(orient="records"),
            },
            "saved_artifacts": {
                "standard_csv": str(std_csv_path),
                "unseen_attack_csv": str(unseen_csv_path),
                "overall_csv": str(overall_csv_path),
                "plots": generated_plots,
            },
            "individual_evaluations": {
                m: {
                    "standard_metrics": r.get("standard_metrics"),
                    "scenario_metrics": r.get("scenario_metrics"),
                    "category_breakdown": r.get("category_breakdown"),
                    "threshold_used": r.get("threshold_used"),
                    "input_unit": r.get("input_unit"),
                }
                for m, r in evaluation_results.items()
            },
        }

        # Save JSON Report
        json_report_path = exp_dir / f"model_comparison_{dataset_name}.json"
        save_metadata(comparison_report, json_report_path)
        logger.info(f"Model comparison report saved to: {json_report_path}")

        return comparison_report

    @classmethod
    def _build_standard_comparison_table(
        cls,
        results: Dict[str, Dict[str, Any]],
        dataset_name: str,
    ) -> pd.DataFrame:
        """Construct standard test split comparison DataFrame."""
        rows = []
        for m, r in results.items():
            cm = r.get("standard_metrics", {}).get("classification", {})
            perf = r.get("standard_metrics", {}).get("performance", {})
            rows.append({
                "Model": m,
                "Dataset": dataset_name,
                "Evaluation Type": "Standard",
                "Accuracy": cm.get("accuracy"),
                "Balanced Accuracy": cm.get("balanced_accuracy"),
                "Precision": cm.get("precision"),
                "Recall (Detection Rate)": cm.get("recall"),
                "F1-Score": cm.get("f1_score"),
                "ROC-AUC": cm.get("roc_auc"),
                "PR-AUC": cm.get("pr_auc"),
                "FPR": cm.get("false_positive_rate"),
                "FNR": cm.get("false_negative_rate"),
                "Specificity (TNR)": cm.get("specificity"),
                "Avg Latency (ms)": perf.get("average_latency_ms"),
                "Throughput (items/sec)": perf.get("throughput_samples_per_sec"),
            })
        return pd.DataFrame(rows)

    @classmethod
    def _build_unseen_comparison_table(
        cls,
        results: Dict[str, Dict[str, Any]],
        dataset_name: str,
    ) -> pd.DataFrame:
        """Construct unseen attack (zero-day proxy) comparison DataFrame."""
        rows = []
        for m, r in results.items():
            unseen_m = r.get("scenario_metrics", {}).get("unseen_attack", {}).get("classification", {})
            rows.append({
                "Model": m,
                "Dataset": dataset_name,
                "Evaluation Type": "Unseen Attack (Zero-Day Proxy)",
                "Zero-Day Recall (Detection Rate)": unseen_m.get("recall"),
                "Zero-Day F1-Score": unseen_m.get("f1_score"),
                "Zero-Day Miss Rate (FNR)": unseen_m.get("false_negative_rate"),
                "Precision": unseen_m.get("precision"),
                "FPR": unseen_m.get("false_positive_rate"),
                "ROC-AUC": unseen_m.get("roc_auc"),
                "PR-AUC": unseen_m.get("pr_auc"),
            })
        return pd.DataFrame(rows)

    @classmethod
    def _build_overall_comparison_table(
        cls,
        std_df: pd.DataFrame,
        unseen_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Merge standard and unseen metrics into a unified comparison table."""
        if unseen_df.empty:
            return std_df

        merged = pd.merge(
            std_df,
            unseen_df[["Model", "Zero-Day Recall (Detection Rate)", "Zero-Day F1-Score", "Zero-Day Miss Rate (FNR)"]],
            on="Model",
            how="left",
        )
        return merged

    @classmethod
    def _compute_rankings(
        cls,
        results: Dict[str, Dict[str, Any]],
        weights: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        Compute multi-dimensional model rankings across security, zero-day resilience,
        false positive mitigation, and computational efficiency.
        """
        models = list(results.keys())
        if not models:
            return {}

        def get_val(m, scenario, field, default=0.0):
            if scenario == "standard":
                v = results[m].get("standard_metrics", {}).get("classification", {}).get(field)
            elif scenario == "unseen":
                v = results[m].get("scenario_metrics", {}).get("unseen_attack", {}).get("classification", {}).get(field)
            elif scenario == "perf":
                v = results[m].get("standard_metrics", {}).get("performance", {}).get(field)
            else:
                v = None
            return float(v) if v is not None and not np.isnan(v) else default

        # 1. Ranking A: Standard Detection Performance (Ranked by Standard F1-Score)
        rank_a = sorted(models, key=lambda m: (get_val(m, "standard", "f1_score"), get_val(m, "standard", "balanced_accuracy")), reverse=True)

        # 2. Ranking B: Zero-Day Proxy Resilience (Ranked by Unseen Attack Recall)
        rank_b = sorted(models, key=lambda m: (get_val(m, "unseen", "recall"), get_val(m, "unseen", "f1_score")), reverse=True)

        # 3. Ranking C: Low False Alarm Viability (Ranked by Precision and lowest FPR)
        rank_c = sorted(models, key=lambda m: (get_val(m, "standard", "precision"), -get_val(m, "standard", "false_positive_rate", 1.0)), reverse=True)

        # 4. Ranking D: Breach Prevention Sensitivity (Ranked by Standard Recall)
        rank_d = sorted(models, key=lambda m: (get_val(m, "standard", "recall"), -get_val(m, "standard", "false_negative_rate", 1.0)), reverse=True)

        # 5. Ranking E: Computational Efficiency (Ranked by lowest latency)
        rank_e = sorted(models, key=lambda m: get_val(m, "perf", "average_latency_ms", 9999.0))

        # 6. Composite Ranking Score
        max_lat = max([get_val(m, "perf", "average_latency_ms", 1.0) for m in models] + [1.0])
        composite_scores: Dict[str, float] = {}

        for m in models:
            u_rec = get_val(m, "unseen", "recall", default=get_val(m, "standard", "recall"))
            s_f1 = get_val(m, "standard", "f1_score")
            prec = get_val(m, "standard", "precision")
            fpr = get_val(m, "standard", "false_positive_rate")
            lat = get_val(m, "perf", "average_latency_ms", 1.0)
            eff = max(0.0, 1.0 - (lat / max_lat))

            score = (
                weights.get("unseen_recall", 0.35) * u_rec
                + weights.get("standard_f1", 0.25) * s_f1
                + weights.get("precision", 0.20) * prec
                + weights.get("fpr_suppression", 0.10) * (1.0 - fpr)
                + weights.get("efficiency", 0.10) * eff
            )
            composite_scores[m] = round(float(score), 4)

        rank_composite = sorted(models, key=lambda m: composite_scores[m], reverse=True)

        return {
            "ranking_standard_f1": rank_a,
            "ranking_zero_day_resilience": rank_b,
            "ranking_low_false_alarm": rank_c,
            "ranking_breach_sensitivity": rank_d,
            "ranking_efficiency": rank_e,
            "composite_ranking": rank_composite,
            "composite_scores": composite_scores,
            "composite_weights": weights,
        }

    @classmethod
    def format_text_summary(cls, report: Dict[str, Any]) -> str:
        """Format a human-readable comparison summary suitable for CLI output."""
        lines = [
            "=" * 78,
            f"ZERO-DAY AI - UNIFIED MODEL COMPARISON SUMMARY ({report['dataset'].upper()})",
            "=" * 78,
            f"Evaluated Models:       {', '.join(report['evaluated_models'])}",
            f"Total Test Samples:     {report['total_test_samples']}",
            f"Unseen Zero-Day Proxy:  {report['unseen_categories_evaluated'] or 'None'}",
            "-" * 78,
            "STANDARD TEST SPLIT BENCHMARK:",
            f"{'Model':<20} | {'Accuracy':<8} | {'Precision':<9} | {'Recall':<8} | {'F1-Score':<8} | {'ROC-AUC':<8} | {'Latency':<8}",
            "-" * 78,
        ]

        for row in report.get("comparison_tables", {}).get("standard", []):
            m = row["Model"]
            acc = f"{row['Accuracy']:.3f}" if row['Accuracy'] is not None else "N/A"
            prec = f"{row['Precision']:.3f}" if row['Precision'] is not None else "N/A"
            rec = f"{row['Recall (Detection Rate)']:.3f}" if row['Recall (Detection Rate)'] is not None else "N/A"
            f1 = f"{row['F1-Score']:.3f}" if row['F1-Score'] is not None else "N/A"
            auc = f"{row['ROC-AUC']:.3f}" if row['ROC-AUC'] is not None else "N/A"
            lat = f"{row['Avg Latency (ms)']:.2f}ms" if row['Avg Latency (ms)'] is not None else "N/A"
            lines.append(f"{m:<20} | {acc:<8} | {prec:<9} | {rec:<8} | {f1:<8} | {auc:<8} | {lat:<8}")

        lines.extend([
            "-" * 78,
            "UNSEEN ATTACK / ZERO-DAY PROXY BENCHMARK:",
            f"{'Model':<20} | {'Zero-Day Recall':<16} | {'Zero-Day F1':<12} | {'Miss Rate (FNR)':<16}",
            "-" * 78,
        ])

        for row in report.get("comparison_tables", {}).get("unseen_attack", []):
            m = row["Model"]
            zd_rec = f"{row['Zero-Day Recall (Detection Rate)']:.3f}" if row['Zero-Day Recall (Detection Rate)'] is not None else "N/A"
            zd_f1 = f"{row['Zero-Day F1-Score']:.3f}" if row['Zero-Day F1-Score'] is not None else "N/A"
            zd_fnr = f"{row['Zero-Day Miss Rate (FNR)']:.3f}" if row['Zero-Day Miss Rate (FNR)'] is not None else "N/A"
            lines.append(f"{m:<20} | {zd_rec:<16} | {zd_f1:<12} | {zd_fnr:<16}")

        rankings = report.get("rankings", {})
        lines.extend([
            "-" * 78,
            "MULTI-DIMENSIONAL MODEL RANKINGS:",
            f"  1. Zero-Day Proxy Resilience:   {' > '.join(rankings.get('ranking_zero_day_resilience', []))}",
            f"  2. Standard Detection (F1):     {' > '.join(rankings.get('ranking_standard_f1', []))}",
            f"  3. Low False Alarm (Precision): {' > '.join(rankings.get('ranking_low_false_alarm', []))}",
            f"  4. Breach Sensitivity (Recall): {' > '.join(rankings.get('ranking_breach_sensitivity', []))}",
            f"  5. Inference Efficiency:        {' > '.join(rankings.get('ranking_efficiency', []))}",
            f"  >> Composite Overall Ranking:   {' > '.join(rankings.get('composite_ranking', []))}",
            "=" * 78,
        ])

        return "\n".join(lines)
