from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from backend.app.ml.explainability.schemas import FeatureContribution


def resolve_feature_names(
    feature_names: Optional[List[str]],
    feature_count: int,
    fallback_prefix: str = "feature",
) -> List[str]:
    """
    Ensure meaningful feature names are returned, avoiding generic names if available.
    """
    if feature_names and len(feature_names) == feature_count:
        return list(feature_names)
    return [f"{fallback_prefix}_{i}" for i in range(feature_count)]


def build_feature_contributions(
    feature_names: List[str],
    feature_values: Union[np.ndarray, List[Any]],
    contributions: Union[np.ndarray, List[float]],
    reconstructed_values: Optional[Union[np.ndarray, List[float]]] = None,
    reconstruction_errors: Optional[Union[np.ndarray, List[float]]] = None,
    shap_values: Optional[Union[np.ndarray, List[float]]] = None,
    baseline_values: Optional[Union[np.ndarray, List[float]]] = None,
    raw_feature_map: Optional[Dict[str, str]] = None,
    metadata_map: Optional[Dict[str, Dict[str, Any]]] = None,
    top_k: int = 10,
) -> Tuple[List[FeatureContribution], List[FeatureContribution], List[FeatureContribution]]:
    """
    Construct standardized, ranked, and partitioned FeatureContribution objects.
    
    Returns:
        (all_ranked_top_k, top_positive_contributions, top_negative_contributions)
    """
    feat_vals = np.asarray(feature_values).ravel()
    contribs = np.asarray(contributions, dtype=float).ravel()
    num_features = len(feat_vals)

    recon_vals = np.asarray(reconstructed_values).ravel() if reconstructed_values is not None else None
    recon_errs = np.asarray(reconstruction_errors, dtype=float).ravel() if reconstruction_errors is not None else None
    shaps = np.asarray(shap_values, dtype=float).ravel() if shap_values is not None else None
    baselines = np.asarray(baseline_values, dtype=float).ravel() if baseline_values is not None else None

    items: List[Dict[str, Any]] = []

    for i in range(num_features):
        name = feature_names[i] if i < len(feature_names) else f"feature_{i}"
        val = float(feat_vals[i]) if np.issubdtype(type(feat_vals[i]), np.number) else feat_vals[i]
        c_val = float(contribs[i])
        abs_c = abs(c_val)

        if c_val > 1e-7:
            direction = "increases_risk"
        elif c_val < -1e-7:
            direction = "decreases_risk"
        else:
            direction = "neutral"

        raw_name = raw_feature_map.get(name, name) if raw_feature_map else name
        meta = metadata_map.get(name, {}) if metadata_map else {}

        item = {
            "feature_name": name,
            "feature_value": val,
            "contribution": round(c_val, 6),
            "direction": direction,
            "absolute_contribution": round(abs_c, 6),
            "raw_feature_name": raw_name,
            "reconstructed_value": round(float(recon_vals[i]), 6) if recon_vals is not None else None,
            "reconstruction_error": round(float(recon_errs[i]), 6) if recon_errs is not None else None,
            "shap_value": round(float(shaps[i]), 6) if shaps is not None else None,
            "baseline_value": round(float(baselines[i]), 6) if baselines is not None else None,
            "metadata": meta,
        }
        items.append(item)

    # Sort all features by absolute contribution descending
    items_sorted = sorted(items, key=lambda x: x["absolute_contribution"], reverse=True)
    for rank, item in enumerate(items_sorted, start=1):
        item["rank"] = rank

    all_ranked = [FeatureContribution(**item) for item in items_sorted[:top_k]]

    # Positive contributions (pushing toward anomaly)
    pos_items = [item for item in items_sorted if item["direction"] == "increases_risk"]
    top_pos = [FeatureContribution(**item) for item in pos_items[:top_k]]

    # Negative contributions (pushing toward benign/normal)
    neg_items = [item for item in items_sorted if item["direction"] == "decreases_risk"]
    top_neg = [FeatureContribution(**item) for item in neg_items[:top_k]]

    return all_ranked, top_pos, top_neg


def generate_natural_language_summary(
    model_name: str,
    prediction: str,
    risk_score: float,
    severity: str,
    top_pos_features: List[FeatureContribution],
    top_neg_features: List[FeatureContribution],
    agreement_ratio: Optional[float] = None,
    participating_models: Optional[List[str]] = None,
) -> str:
    """
    Generate dynamic, contextual human-readable explanation summary.
    Strictly avoids static boilerplate and uses observed feature names and contributions.
    """
    is_anomaly = (prediction.lower() in ("attack", "anomaly") or risk_score >= 50.0)
    pos_names = [f.feature_name for f in top_pos_features[:3]]
    neg_names = [f.feature_name for f in top_neg_features[:2]]

    if model_name.lower() == "ensemble":
        parts = []
        if is_anomaly:
            models_str = ", ".join(participating_models) if participating_models else "multiple detection models"
            parts.append(
                f"The ensemble classified this network event as {severity} risk (score: {risk_score:.1f}/100.0) "
                f"because detection engines ({models_str}) flagged anomalous behavior."
            )
            if pos_names:
                parts.append(f"Elevated risk was primarily driven by prominent network metrics: {', '.join(pos_names)}.")
            if agreement_ratio is not None:
                parts.append(f"Ensemble consensus agreement ratio is {agreement_ratio * 100.0:.1f}%.")
        else:
            parts.append(
                f"The ensemble classified this network event as normal baseline traffic (risk score: {risk_score:.1f}/100.0) "
                f"with {severity} severity."
            )
            if neg_names:
                parts.append(f"Consistent normal traffic attributes ({', '.join(neg_names)}) kept the composite risk low.")
        return " ".join(parts)

    elif model_name.lower() == "random_forest":
        if is_anomaly:
            lead = f"Random Forest classified this event as an attack (probability score: {risk_score:.1f}/100.0)."
            if pos_names:
                detail = f"The largest positive SHAP contributions pushing the score above the decision threshold were {', '.join(pos_names)}."
            else:
                detail = "Multiple distributed features contributed slightly above baseline."
            return f"{lead} {detail}"
        else:
            lead = f"Random Forest classified this event as benign normal traffic (score: {risk_score:.1f}/100.0)."
            if neg_names:
                detail = f"Features strongly driving the prediction toward normal included {', '.join(neg_names)}."
            else:
                detail = "Feature values were within standard benign parameter distributions."
            return f"{lead} {detail}"

    elif model_name.lower() == "isolation_forest":
        if is_anomaly:
            lead = f"Isolation Forest isolated this sample rapidly as an anomaly (risk score: {risk_score:.1f}/100.0)."
            if pos_names:
                detail = f"Feature sensitivity perturbations indicate that deviations in {', '.join(pos_names)} contributed most to isolating this sample."
            else:
                detail = "Unusual multivariate combinations caused premature tree partitioning."
            return f"{lead} {detail}"
        else:
            return (
                f"Isolation Forest identified this sample as typical benign traffic (risk score: {risk_score:.1f}/100.0), "
                f"requiring deep partition paths across isolation trees."
            )

    elif model_name.lower() == "autoencoder":
        if is_anomaly:
            lead = f"Dense Autoencoder detected an anomaly with elevated reconstruction loss (risk score: {risk_score:.1f}/100.0)."
            if pos_names:
                detail = f"The model struggled most to reconstruct features: {', '.join(pos_names)}, indicating these features deviate from learned normal manifolds."
            else:
                detail = "Reconstruction error was distributed across multiple input features."
            return f"{lead} {detail}"
        else:
            return (
                f"Dense Autoencoder reconstructed this network sample with low residual error (risk score: {risk_score:.1f}/100.0), "
                f"closely matching learned benign network traffic representations."
            )

    elif model_name.lower() in ("lstm", "lstm_autoencoder"):
        if is_anomaly:
            lead = f"LSTM Autoencoder flagged temporal sequence anomaly (risk score: {risk_score:.1f}/100.0)."
            if pos_names:
                detail = f"Temporal sequence reconstruction deviations were concentrated in features: {', '.join(pos_names)}."
            else:
                detail = "Temporal transition dynamics violated learned normal sequence patterns."
            return f"{lead} {detail}"
        else:
            return (
                f"LSTM Autoencoder successfully reconstructed the temporal event sequence (risk score: {risk_score:.1f}/100.0), "
                f"confirming normal chronological transition dynamics."
            )

    # Generic fallback
    status = "anomalous" if is_anomaly else "normal"
    return f"Model '{model_name}' evaluated sample as {status} (risk score: {risk_score:.1f}/100.0, severity: {severity})."


def get_model_limitations(model_name: str, method: str) -> List[str]:
    """
    Provide standardized, technically precise limitations for the explanation.
    Never claims causal proof of security compromise.
    """
    common = [
        "Explainability describes model internal behavior and feature sensitivities; it does not constitute physical proof of real-world cyber attack causality.",
        "Explanations reflect representations learned from training data distributions and may not generalize to unseen adversarial evasion attacks."
    ]

    m_lower = model_name.lower()
    if m_lower == "random_forest" or "shap" in method.lower():
        return [
            "SHAP values measure additive feature attribution for the trained Random Forest classifier.",
            "SHAP TreeExplainer computes conditional expectations assuming tree partition boundaries, not causal mechanisms.",
        ] + common

    elif m_lower == "isolation_forest":
        return [
            "Isolation Forest explanations use controlled feature perturbation sensitivity relative to normal reference baselines.",
            "This heuristic attribution identifies features whose alteration moves the isolation score most, but is not an exact Shapley value.",
        ] + common

    elif m_lower == "autoencoder":
        return [
            "Autoencoder explanations measure per-feature squared reconstruction errors $(x_j - \\hat{x}_j)^2$.",
            "High reconstruction error indicates that feature values fall outside learned normal traffic topological manifolds, not that the feature was maliciously manipulated.",
        ] + common

    elif m_lower in ("lstm", "lstm_autoencoder"):
        return [
            "LSTM Autoencoder explanations measure temporal sequence reconstruction error across timesteps and features.",
            "Timestep attribution identifies when the sequence reconstruction deteriorated most, but temporal correlation does not prove attack onset timing.",
        ] + common

    elif m_lower == "ensemble":
        return [
            "Ensemble explanations reflect the weighted combination of participating models and consensus metrics.",
            "If individual models are unavailable or uncalibrated, ensemble reliability and explanation completeness are degraded accordingly.",
        ] + common

    return common
