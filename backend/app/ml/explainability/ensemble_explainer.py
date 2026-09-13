import time
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd

from backend.app.core.logging import logger
from backend.app.ml.ensemble.ensemble_detector import EnsembleDetector
from backend.app.ml.ensemble.schemas import EnsemblePrediction
from backend.app.ml.explainability.schemas import (
    EnsembleExplanation,
    ModelExplanation,
    FeatureContribution,
)
from backend.app.ml.explainability.random_forest_explainer import RandomForestExplainer
from backend.app.ml.explainability.isolation_forest_explainer import IsolationForestExplainer
from backend.app.ml.explainability.autoencoder_explainer import AutoencoderExplainer
from backend.app.ml.explainability.lstm_explainer import LSTMAutoencoderExplainer
from backend.app.ml.explainability.feature_attribution import (
    generate_natural_language_summary,
    get_model_limitations,
)


class EnsembleExplainer:
    """
    Explainable AI engine for the unified Ensemble Detection and Risk Scoring Engine.
    Explains composite risk scoring via multi-model weighted contributions,
    model agreement analysis, and cross-model feature attribution.
    """

    def __init__(
        self,
        ensemble_detector: EnsembleDetector,
        dataset_name: str = "generic",
        top_k: int = 10,
    ):
        self.detector = ensemble_detector
        self.dataset_name = dataset_name
        self.top_k = top_k
        self.explainers: Dict[str, Any] = {}
        self._initialize_sub_explainers()

    def _initialize_sub_explainers(self) -> None:
        """Initialize dedicated explainers for each loaded constituent model."""
        feat_names = None

        if self.detector.random_forest is not None and getattr(self.detector.random_forest, "is_trained", False):
            feat_names = getattr(self.detector.random_forest, "feature_names_", None)
            self.explainers["random_forest"] = RandomForestExplainer(
                model=self.detector.random_forest,
                dataset_name=self.dataset_name,
                feature_names=feat_names,
                top_k=self.top_k,
            )

        if self.detector.isolation_forest is not None and getattr(self.detector.isolation_forest, "is_trained", False):
            if_feat = getattr(self.detector.isolation_forest, "feature_names_", None) or feat_names
            self.explainers["isolation_forest"] = IsolationForestExplainer(
                model=self.detector.isolation_forest,
                dataset_name=self.dataset_name,
                feature_names=if_feat,
                top_k=self.top_k,
            )

        if self.detector.autoencoder is not None and getattr(self.detector.autoencoder, "is_trained", False):
            self.explainers["autoencoder"] = AutoencoderExplainer(
                model=self.detector.autoencoder,
                dataset_name=self.dataset_name,
                feature_names=feat_names,
                top_k=self.top_k,
            )

        if self.detector.lstm_autoencoder is not None and getattr(self.detector.lstm_autoencoder, "is_trained", False):
            self.explainers["lstm_autoencoder"] = LSTMAutoencoderExplainer(
                model=self.detector.lstm_autoencoder,
                dataset_name=self.dataset_name,
                feature_names=feat_names,
                top_k=self.top_k,
            )

        logger.info(f"EnsembleExplainer initialized with {len(self.explainers)} sub-model explainers.")

    def explain_instance(
        self,
        record: Union[Dict[str, Any], pd.Series, np.ndarray, List[Any]],
        sequence_window: Optional[Union[np.ndarray, List[List[float]]]] = None,
        top_k: Optional[int] = None,
        include_per_model_explanations: bool = True,
    ) -> EnsembleExplanation:
        """
        Generate a comprehensive ensemble explanation for a single flow record.
        """
        k = top_k or self.top_k
        start_total = time.perf_counter()

        # 1. Ensemble prediction pass
        start_pred = time.perf_counter()
        prediction_obj: EnsemblePrediction = self.detector.predict_single(
            features=record,
            sequence_window=sequence_window,
        )
        pred_latency_ms = (time.perf_counter() - start_pred) * 1000.0

        # 2. Extract model-level risk contribution breakdown
        start_exp = time.perf_counter()
        model_contribs_dict: Dict[str, Dict[str, Any]] = {}
        for m_name, c in prediction_obj.contributions.items():
            model_contribs_dict[m_name] = {
                "model_name": m_name,
                "is_available": c.is_available,
                "prediction": c.prediction,
                "is_anomaly": c.is_anomaly,
                "native_score": round(c.native_score, 4),
                "normalized_risk_score": round(c.normalized_score, 2),
                "configured_weight": round(c.configured_weight, 4),
                "effective_weight": round(c.effective_weight, 4),
                "weighted_contribution": round(c.effective_weight * c.normalized_score, 2),
                "decision_threshold": round(c.decision_threshold, 4),
                "latency_ms": round(c.latency_ms, 3),
                "error": c.error,
            }

        # 3. Generate per-model explanations if requested
        per_model_explanations: Dict[str, ModelExplanation] = {}
        if include_per_model_explanations:
            for m_name, explainer in self.explainers.items():
                if m_name in prediction_obj.participating_models:
                    try:
                        if m_name == "lstm_autoencoder":
                            if sequence_window is not None:
                                per_model_explanations[m_name] = explainer.explain_instance(sequence_window, top_k=k)
                        else:
                            per_model_explanations[m_name] = explainer.explain_instance(record, top_k=k)
                    except Exception as e:
                        logger.warning(f"Could not generate sub-explanation for '{m_name}': {e}")

        # 4. Fused feature attribution
        fused_contributions = self._compute_fused_feature_attributions(
            per_model_explanations=per_model_explanations,
            contributions=prediction_obj.contributions,
            top_k=k,
        )

        exp_latency_ms = (time.perf_counter() - start_exp) * 1000.0
        total_latency_ms = (time.perf_counter() - start_total) * 1000.0

        # 5. Dynamic natural language summary
        top_pos = [f for f in fused_contributions if f.direction == "increases_risk"][:3]
        top_neg = [f for f in fused_contributions if f.direction == "decreases_risk"][:2]

        summary = generate_natural_language_summary(
            model_name="ensemble",
            prediction=prediction_obj.prediction,
            risk_score=prediction_obj.risk_score,
            severity=prediction_obj.severity,
            top_pos_features=top_pos,
            top_neg_features=top_neg,
            agreement_ratio=prediction_obj.agreement.agreement_ratio,
            participating_models=prediction_obj.participating_models,
        )

        limitations = get_model_limitations("ensemble", "ensemble_risk_attribution")

        return EnsembleExplanation(
            explanation_id=f"ens-exp-{int(time.time() * 1000)}",
            model_name="ensemble",
            model_version=prediction_obj.model_version,
            dataset_name=self.dataset_name,
            prediction=prediction_obj.prediction,
            is_anomaly=prediction_obj.is_anomaly,
            risk_score=prediction_obj.risk_score,
            severity=prediction_obj.severity,
            decision_threshold=prediction_obj.decision_threshold,
            reliability_score=prediction_obj.reliability_score,
            model_contributions=model_contribs_dict,
            participating_models=prediction_obj.participating_models,
            missing_models=prediction_obj.missing_models,
            agreement=prediction_obj.agreement.model_dump(),
            per_model_explanations=per_model_explanations,
            fused_feature_contributions=fused_contributions,
            summary=summary,
            limitations=limitations,
            prediction_latency_ms=round(pred_latency_ms, 3),
            explanation_latency_ms=round(exp_latency_ms, 3),
            total_latency_ms=round(total_latency_ms, 3),
        )

    def _compute_fused_feature_attributions(
        self,
        per_model_explanations: Dict[str, ModelExplanation],
        contributions: Dict[str, Any],
        top_k: int = 10,
    ) -> List[FeatureContribution]:
        """
        Safely fuse normalized feature attributions across participating models weighted by effective weight.
        """
        if not per_model_explanations:
            return []

        feature_scores: Dict[str, float] = {}
        feature_raw_names: Dict[str, str] = {}
        feature_values: Dict[str, Any] = {}

        for m_name, exp in per_model_explanations.items():
            contrib_info = contributions.get(m_name)
            weight = contrib_info.effective_weight if contrib_info else (1.0 / len(per_model_explanations))

            # Normalize model's feature contributions so maximum absolute impact is 1.0
            max_abs = max([f.absolute_contribution for f in exp.feature_contributions] or [1.0])
            if max_abs <= 0:
                max_abs = 1.0

            for fc in exp.feature_contributions:
                fname = fc.feature_name
                norm_c = (fc.contribution / max_abs) * weight
                feature_scores[fname] = feature_scores.get(fname, 0.0) + norm_c
                if fname not in feature_raw_names and fc.raw_feature_name:
                    feature_raw_names[fname] = fc.raw_feature_name
                if fname not in feature_values and fc.feature_value is not None:
                    feature_values[fname] = fc.feature_value

        sorted_feats = sorted(feature_scores.items(), key=lambda x: abs(x[1]), reverse=True)
        results: List[FeatureContribution] = []

        for rank, (fname, score) in enumerate(sorted_feats[:top_k], start=1):
            direction = "increases_risk" if score > 1e-6 else ("decreases_risk" if score < -1e-6 else "neutral")
            results.append(
                FeatureContribution(
                    feature_name=fname,
                    feature_value=feature_values.get(fname, None),
                    contribution=round(score, 6),
                    direction=direction,
                    absolute_contribution=round(abs(score), 6),
                    rank=rank,
                    raw_feature_name=feature_raw_names.get(fname, fname),
                )
            )

        return results
