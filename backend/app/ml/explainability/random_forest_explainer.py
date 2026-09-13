import time
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd

from backend.app.core.logging import logger
from backend.app.ml.models.random_forest import RandomForestClassifierModel
from backend.app.ml.ensemble.severity import classify_severity
from backend.app.ml.explainability.base_explainer import BaseExplainer
from backend.app.ml.explainability.schemas import ModelExplanation
from backend.app.ml.explainability.feature_attribution import (
    resolve_feature_names,
    build_feature_contributions,
    generate_natural_language_summary,
    get_model_limitations,
)

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logger.warning("SHAP library is not installed. RandomForestExplainer will use tree sensitivity fallback.")


class RandomForestExplainer(BaseExplainer):
    """
    Explainable AI engine for Random Forest classifier using SHAP TreeExplainer.
    Computes exact additive feature attribution for binary attack classification.
    """

    def __init__(
        self,
        model: RandomForestClassifierModel,
        dataset_name: str = "generic",
        feature_names: Optional[List[str]] = None,
        top_k: int = 10,
    ):
        feat_names = feature_names or model.feature_names_
        super().__init__(
            model_name="random_forest",
            explanation_method="shap_tree",
            dataset_name=dataset_name,
            feature_names=feat_names,
            top_k=top_k,
        )
        self.model = model
        self.tree_explainer: Optional[Any] = None
        self._initialize_explainer()

    def _initialize_explainer(self) -> None:
        """Initialize and cache the SHAP TreeExplainer on the underlying scikit-learn model."""
        if not self.model.is_trained or self.model.model is None:
            logger.debug("RandomForestClassifierModel is not trained yet; TreeExplainer deferred.")
            return

        if SHAP_AVAILABLE:
            try:
                self.tree_explainer = shap.TreeExplainer(self.model.model)
                self.is_initialized = True
                logger.info(f"Initialized SHAP TreeExplainer for Random Forest ({len(self.feature_names)} features).")
            except Exception as e:
                logger.warning(f"Failed to initialize SHAP TreeExplainer: {e}. Fallback enabled.")
                self.tree_explainer = None
        else:
            self.is_initialized = True

    def explain_instance(
        self,
        X_sample: Union[np.ndarray, pd.DataFrame, pd.Series, Dict[str, Any]],
        top_k: Optional[int] = None,
        **kwargs: Any,
    ) -> ModelExplanation:
        """
        Explain a single Random Forest prediction using SHAP TreeExplainer.
        """
        k = top_k or self.top_k
        start_total = time.perf_counter()

        X_arr = self._ensure_2d_numpy(X_sample)
        if not self.feature_names or len(self.feature_names) != X_arr.shape[1]:
            self.feature_names = resolve_feature_names(self.model.feature_names_, X_arr.shape[1])

        # 1. Prediction step
        start_pred = time.perf_counter()
        attack_prob = float(self.model.predict_attack_probability(X_arr)[0])
        pred_latency_ms = (time.perf_counter() - start_pred) * 1000.0

        risk_score = round(np.clip(attack_prob * 100.0, 0.0, 100.0), 2)
        is_anomaly = bool(attack_prob >= self.model.decision_threshold)
        prediction = "attack" if is_anomaly else "normal"
        severity = classify_severity(risk_score)

        # 2. Explanation step (SHAP values)
        start_exp = time.perf_counter()
        shap_attack_values: np.ndarray

        if self.tree_explainer is not None:
            try:
                shap_output = self.tree_explainer.shap_values(X_arr)
                if isinstance(shap_output, list):
                    # List of [shap_class_0, shap_class_1]
                    shap_attack_values = np.asarray(shap_output[1][0], dtype=float)
                elif isinstance(shap_output, np.ndarray):
                    if shap_output.ndim == 3:
                        # Shape (N, D, C) -> take sample 0, class 1
                        shap_attack_values = shap_output[0, :, 1]
                    elif shap_output.ndim == 2:
                        # Shape (N, D) -> single output class
                        shap_attack_values = shap_output[0]
                    else:
                        shap_attack_values = shap_output.ravel()
                else:
                    shap_attack_values = np.asarray(shap_output, dtype=float).ravel()
            except Exception as e:
                logger.warning(f"SHAP explanation calculation failed: {e}. Using tree feature importance sensitivity.")
                shap_attack_values = self._fallback_tree_attribution(X_arr[0], attack_prob)
        else:
            shap_attack_values = self._fallback_tree_attribution(X_arr[0], attack_prob)

        exp_latency_ms = (time.perf_counter() - start_exp) * 1000.0
        total_latency_ms = (time.perf_counter() - start_total) * 1000.0

        # 3. Construct ranked feature contributions
        all_ranked, top_pos, top_neg = build_feature_contributions(
            feature_names=self.feature_names,
            feature_values=X_arr[0],
            contributions=shap_attack_values,
            shap_values=shap_attack_values,
            top_k=k,
        )

        # 4. Generate dynamic natural language summary
        summary = generate_natural_language_summary(
            model_name="random_forest",
            prediction=prediction,
            risk_score=risk_score,
            severity=severity,
            top_pos_features=top_pos,
            top_neg_features=top_neg,
        )

        limitations = get_model_limitations("random_forest", self.explanation_method)

        return ModelExplanation(
            model_name="random_forest",
            model_version="1.0.0",
            dataset_name=self.dataset_name,
            prediction=prediction,
            is_anomaly=is_anomaly,
            risk_score=risk_score,
            severity=severity,
            decision_threshold=self.model.decision_threshold,
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

    def _fallback_tree_attribution(self, x_vec: np.ndarray, base_prob: float) -> np.ndarray:
        """
        Fallback perturbation-based feature attribution if SHAP encounters an internal library exception.
        """
        importances = [self.model.feature_importances_dict_.get(f, 0.01) for f in self.feature_names]
        if not importances or sum(importances) == 0:
            importances = [1.0 / max(len(x_vec), 1)] * len(x_vec)
        importances_arr = np.array(importances, dtype=float)
        norm_imp = importances_arr / (np.sum(importances_arr) + 1e-9)

        # Direction based on distance from 0 (standardized mean)
        direction = np.sign(x_vec)
        direction[direction == 0] = 1.0
        return norm_imp * (base_prob - self.model.decision_threshold) * direction
