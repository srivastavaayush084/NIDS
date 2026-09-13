import time
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd

from backend.app.core.logging import logger
from backend.app.ml.models.isolation_forest import IsolationForestDetector
from backend.app.ml.ensemble.severity import classify_severity
from backend.app.ml.explainability.base_explainer import BaseExplainer
from backend.app.ml.explainability.schemas import ModelExplanation
from backend.app.ml.explainability.feature_attribution import (
    resolve_feature_names,
    build_feature_contributions,
    generate_natural_language_summary,
    get_model_limitations,
)


class IsolationForestExplainer(BaseExplainer):
    """
    Explainable AI engine for Isolation Forest using controlled feature perturbation sensitivity.
    Evaluates how resetting individual feature dimensions to a benign reference baseline alters the anomaly score.
    """

    def __init__(
        self,
        model: IsolationForestDetector,
        dataset_name: str = "generic",
        feature_names: Optional[List[str]] = None,
        reference_baseline: Optional[np.ndarray] = None,
        top_k: int = 10,
    ):
        feat_names = feature_names or model.feature_names_
        super().__init__(
            model_name="isolation_forest",
            explanation_method="isolation_forest_perturbation",
            dataset_name=dataset_name,
            feature_names=feat_names,
            top_k=top_k,
        )
        self.model = model
        self.reference_baseline: Optional[np.ndarray] = reference_baseline
        self.is_initialized = model.is_trained

    def set_reference_baseline(self, X_normal_reference: Union[np.ndarray, pd.DataFrame]) -> None:
        """Set empirical median baseline from normal background traffic."""
        X_arr = self._ensure_2d_numpy(X_normal_reference)
        self.reference_baseline = np.median(X_arr, axis=0)
        logger.info(f"Set Isolation Forest reference baseline ({len(self.reference_baseline)} features).")

    def explain_instance(
        self,
        X_sample: Union[np.ndarray, pd.DataFrame, pd.Series, Dict[str, Any]],
        top_k: Optional[int] = None,
        **kwargs: Any,
    ) -> ModelExplanation:
        """
        Explain a single Isolation Forest prediction via controlled feature perturbation.
        """
        k = top_k or self.top_k
        start_total = time.perf_counter()

        X_arr = self._ensure_2d_numpy(X_sample)
        num_features = X_arr.shape[1]
        if not self.feature_names or len(self.feature_names) != num_features:
            self.feature_names = resolve_feature_names(self.model.feature_names_, num_features)

        # 1. Base Prediction step
        start_pred = time.perf_counter()
        base_score = float(self.model.compute_anomaly_scores(X_arr)[0])
        pred_latency_ms = (time.perf_counter() - start_pred) * 1000.0

        is_anomaly = bool(base_score >= self.model.anomaly_threshold)
        prediction = "attack" if is_anomaly else "normal"
        severity = classify_severity(base_score)

        # Establish baseline reference vector
        if self.reference_baseline is not None and len(self.reference_baseline) == num_features:
            baseline_vec = self.reference_baseline
        else:
            baseline_vec = np.zeros(num_features, dtype=np.float32)

        # 2. Perturbation Sensitivity Explanation step
        start_exp = time.perf_counter()

        # Construct batch of perturbed samples (one per feature replacing feature j with baseline)
        perturbed_batch = np.repeat(X_arr, num_features, axis=0)
        for j in range(num_features):
            perturbed_batch[j, j] = baseline_vec[j]

        perturbed_scores = self.model.compute_anomaly_scores(perturbed_batch)

        # Delta: score(original) - score(perturbed)
        # If replacing feature j with baseline reduces anomaly score, delta > 0 (feature pushed toward anomaly)
        deltas = base_score - perturbed_scores
        exp_latency_ms = (time.perf_counter() - start_exp) * 1000.0
        total_latency_ms = (time.perf_counter() - start_total) * 1000.0

        # 3. Construct ranked feature contributions
        all_ranked, top_pos, top_neg = build_feature_contributions(
            feature_names=self.feature_names,
            feature_values=X_arr[0],
            contributions=deltas,
            baseline_values=baseline_vec,
            top_k=k,
        )

        # 4. Generate dynamic summary
        summary = generate_natural_language_summary(
            model_name="isolation_forest",
            prediction=prediction,
            risk_score=base_score,
            severity=severity,
            top_pos_features=top_pos,
            top_neg_features=top_neg,
        )

        limitations = get_model_limitations("isolation_forest", self.explanation_method)

        return ModelExplanation(
            model_name="isolation_forest",
            model_version="1.0.0",
            dataset_name=self.dataset_name,
            prediction=prediction,
            is_anomaly=is_anomaly,
            risk_score=base_score,
            severity=severity,
            decision_threshold=self.model.anomaly_threshold,
            explanation_method=self.explanation_method,
            top_k=k,
            feature_contributions=all_ranked,
            top_positive_contributions=top_pos,
            top_negative_contributions=top_neg,
            summary=summary,
            limitations=limitations,
            prediction_latency_ms=round(pred_latency_ms, 3),
            explanation_latency_ms=round(exp_latency_ms, 3),
            total_latency_ms=round(total_latency_ms, 3),
        )
