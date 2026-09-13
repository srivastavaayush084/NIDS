import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ml.explainability.schemas import (
    ModelExplanation,
    EnsembleExplanation,
)
from backend.app.services.explainer_service import explainer_service
from backend.app.ml.sequence.sequence_builder import SequenceBuilder
from backend.app.ml.data.utils.data_utils import ensure_dir


def save_explanation_plot(
    explanation: Any,
    output_dir: Path,
    model_name: str,
    dataset_name: str,
    sample_index: int,
) -> Path:
    """Generate and save visual explanation artifact."""
    ensure_dir(output_dir)
    plot_path = output_dir / f"xai_{model_name}_{dataset_name}_sample_{sample_index}.png"

    fig, ax = plt.subplots(figsize=(10, 6), dpi=150)

    if model_name == "ensemble" and isinstance(explanation, EnsembleExplanation):
        # Plot model risk contributions
        models = list(explanation.model_contributions.keys())
        scores = [explanation.model_contributions[m]["weighted_contribution"] for m in models]
        y_pos = np.arange(len(models))

        colors = ["#e74c3c" if explanation.model_contributions[m]["is_anomaly"] else "#2ecc71" for m in models]
        ax.barh(y_pos, scores, color=colors, align="center")
        ax.set_yticks(y_pos)
        ax.set_yticklabels(models)
        ax.invert_yaxis()
        ax.set_xlabel("Weighted Risk Contribution (0 - 100)")
        ax.set_title(f"Ensemble Risk Breakdown: {explanation.risk_score:.1f}/100.0 ({explanation.severity})")

    elif isinstance(explanation, ModelExplanation) and explanation.timestep_contributions:
        # Plot timestep reconstruction errors for LSTM
        timesteps = [t.timestep_label for t in explanation.timestep_contributions]
        errors = [t.reconstruction_error for t in explanation.timestep_contributions]

        ax.bar(timesteps, errors, color="#3498db", alpha=0.85)
        ax.axhline(explanation.decision_threshold, color="#e74c3c", linestyle="--", label=f"Threshold ({explanation.decision_threshold:.4f})")
        ax.set_xlabel("Sequence Timestep")
        ax.set_ylabel("Reconstruction Error (MSE)")
        ax.set_title(f"LSTM Timestep Error Decomposition (Risk: {explanation.risk_score:.1f}/100.0)")
        ax.legend()

    elif isinstance(explanation, ModelExplanation):
        # Plot top feature contributions
        feats = [f.feature_name for f in explanation.feature_contributions[:10]]
        contribs = [f.contribution for f in explanation.feature_contributions[:10]]
        y_pos = np.arange(len(feats))

        colors = ["#e74c3c" if c > 0 else "#2ecc71" for c in contribs]
        ax.barh(y_pos, contribs, color=colors, align="center")
        ax.axvline(0, color="black", linewidth=0.8, linestyle=":")
        ax.set_yticks(y_pos)
        ax.set_yticklabels(feats)
        ax.invert_yaxis()
        ax.set_xlabel("Feature Attribution / Contribution")
        ax.set_title(f"{model_name.replace('_', ' ').title()} Explanation: {explanation.prediction.upper()} (Risk: {explanation.risk_score:.1f}/100.0)")

    plt.tight_layout()
    plt.savefig(plot_path)
    plt.close(fig)
    logger.info(f"Saved explanation visualization to: {plot_path}")
    return plot_path


def main():
    parser = argparse.ArgumentParser(
        description="Explain model predictions and ensemble risk scores using the ZeroDayAI XAI layer."
    )
    parser.add_argument(
        "--model",
        type=str,
        default="ensemble",
        choices=["random_forest", "isolation_forest", "autoencoder", "lstm", "lstm_autoencoder", "ensemble"],
        help="Target model to explain (default: ensemble).",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="synthetic",
        help="Dataset name (default: synthetic).",
    )
    parser.add_argument(
        "--sample-index",
        type=int,
        default=0,
        help="Row index of test sample to explain (default: 0).",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Number of top features to include in explanation (default: 10).",
    )
    parser.add_argument(
        "--save-plot",
        action="store_true",
        help="Generate and save visual plot artifact under experiments/explainability/.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional path to save JSON serialized explanation.",
    )

    args = parser.parse_args()

    # Load test dataset
    data_path = settings.DATA_DIR / "processed" / args.dataset / "X_test.csv"
    if not data_path.exists():
        logger.error(f"Test data file not found at: {data_path}")
        sys.exit(1)

    df_test = pd.read_csv(data_path)
    if args.sample_index >= len(df_test):
        logger.error(f"Sample index {args.sample_index} exceeds dataset size ({len(df_test)}).")
        sys.exit(1)

    record = df_test.iloc[args.sample_index]
    logger.info(f"Explaining prediction for model='{args.model}', dataset='{args.dataset}', sample_index={args.sample_index}")

    # Fetch explainer
    explainer = explainer_service.get_explainer(args.model, args.dataset)

    # Generate sequence window if needed for LSTM or Ensemble
    sequence_window = None
    if args.model in ("lstm", "lstm_autoencoder", "ensemble"):
        target_seq_len = 3
        if hasattr(explainer, "model") and hasattr(explainer.model, "seq_len"):
            target_seq_len = explainer.model.seq_len
        elif hasattr(explainer, "detector") and explainer.detector.lstm_autoencoder is not None:
            target_seq_len = explainer.detector.lstm_autoencoder.seq_len

        start_idx = max(0, args.sample_index - target_seq_len + 1)
        window_df = df_test.iloc[start_idx : args.sample_index + 1]
        if len(window_df) < target_seq_len:
            pad_needed = target_seq_len - len(window_df)
            padding = pd.concat([window_df.iloc[[0]]] * pad_needed, ignore_index=True)
            window_df = pd.concat([padding, window_df], ignore_index=True)
        sequence_window = window_df.to_numpy(dtype=np.float32).reshape(1, target_seq_len, -1)

    # Generate explanation
    if args.model == "ensemble":
        exp = explainer.explain_instance(record=record, sequence_window=sequence_window, top_k=args.top_k)
    elif args.model in ("lstm", "lstm_autoencoder"):
        exp = explainer.explain_instance(X_sample=sequence_window, top_k=args.top_k)
    else:
        exp = explainer.explain_instance(X_sample=record, top_k=args.top_k)

    # Print Formatted Report
    print("\n" + "=" * 70)
    print(" ZERO-DAY ATTACK DETECTION SYSTEM -- EXPLAINABLE AI (XAI) REPORT ")
    print("=" * 70)
    print(f"Explanation ID       : {exp.explanation_id}")
    print(f"Model Evaluated      : {exp.model_name.upper()} (Dataset: {args.dataset})")
    print(f"Prediction           : {exp.prediction.upper()} (Is Anomaly: {exp.is_anomaly})")
    print(f"Risk Score           : {exp.risk_score:.2f} / 100.0 (Severity: {exp.severity})")
    print(f"Decision Threshold   : {exp.decision_threshold}")
    print(f"Total Execution Time : {exp.total_latency_ms:.2f} ms (Inference: {exp.prediction_latency_ms:.2f} ms, XAI: {exp.explanation_latency_ms:.2f} ms)")
    print("-" * 70)

    if isinstance(exp, EnsembleExplanation):
        print("CONSTITUENT MODEL CONTRIBUTIONS:")
        for m_name, c in exp.model_contributions.items():
            avail_str = "AVAILABLE" if c["is_available"] else "UNAVAILABLE"
            print(f"  * {m_name.ljust(18)}: Risk={c['normalized_risk_score']:5.1f} | Weight={c['effective_weight']:.2f} | Weighted Contribution={c['weighted_contribution']:5.2f} [{avail_str}]")
        print(f"Model Consensus Agreement Ratio: {exp.agreement.get('agreement_ratio', 1.0) * 100.0:.1f}%")
        print("-" * 70)
        print("FUSED TOP CONTRIBUTING FEATURES:")
        for f in exp.fused_feature_contributions[:args.top_k]:
            arrow = "(+) increases risk" if f.direction == "increases_risk" else "(-) decreases risk"
            print(f"  {f.rank:2d}. {f.feature_name.ljust(25)} : {f.contribution:+8.4f} {arrow}")

    elif isinstance(exp, ModelExplanation):
        print(f"EXPLANATION METHOD: {exp.explanation_method}")
        if exp.timestep_contributions:
            print("\nTIMESTEP ANOMALY BREAKDOWN:")
            for t in exp.timestep_contributions[:5]:
                print(f"  Timestep {t.timestep_label} [Rank {t.rank}]: Error={t.reconstruction_error:.6f} | Relative Share={t.relative_contribution * 100.0:.1f}%")

        print("\nTOP CONTRIBUTING FEATURES:")
        for f in exp.feature_contributions[:args.top_k]:
            arrow = "(+) increases risk" if f.direction == "increases_risk" else "(-) decreases risk"
            val_str = f"val={f.feature_value}" if f.feature_value is not None else ""
            print(f"  {f.rank:2d}. {f.feature_name.ljust(25)} : {f.contribution:+8.4f} {val_str.ljust(15)} {arrow}")

    print("-" * 70)
    print("DYNAMIC EXPLANATION SUMMARY:")
    print(f"  \"{exp.summary}\"")
    print("-" * 70)
    print("METHODOLOGICAL LIMITATIONS:")
    for lim in exp.limitations:
        print(f"  * {lim}")
    print("=" * 70 + "\n")

    # Optional plot generation
    if args.save_plot:
        plot_dir = settings.XAI_EXPERIMENTS_DIR
        save_explanation_plot(exp, plot_dir, args.model, args.dataset, args.sample_index)

    # Optional JSON output
    if args.output:
        out_p = Path(args.output)
        ensure_dir(out_p.parent)
        with open(out_p, "w", encoding="utf-8") as f:
            f.write(exp.model_dump_json(indent=2))
        logger.info(f"Saved explanation JSON to: {out_p}")


if __name__ == "__main__":
    main()
