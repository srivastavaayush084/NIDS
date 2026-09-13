from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ml.ensemble.schemas import (
    ModelContribution,
    ModelAgreement,
    LatencyBreakdown,
    EnsemblePrediction,
)
from backend.app.ml.ensemble.severity import SeverityClassifier


class EnsembleRiskScorer:
    """
    Core Aggregation and Scoring Engine for Multi-Model Anomaly Detection.

    Fuses normalized risk scores via weighted score aggregation, handles dynamic
    model dropouts with weight renormalization, computes model agreement/consensus,
    evaluates heuristic reliability, and maps composite risk to severity tiers.
    """

    DEFAULT_WEIGHTS = {
        "isolation_forest": 0.25,
        "autoencoder": 0.25,
        "lstm_autoencoder": 0.25,
        "random_forest": 0.25,
    }

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        decision_threshold: Optional[float] = None,
        severity_classifier: Optional[SeverityClassifier] = None,
    ):
        self.weights = dict(weights or self._load_default_weights())
        self.decision_threshold = (
            decision_threshold
            if decision_threshold is not None
            else settings.ENSEMBLE_DECISION_THRESHOLD
        )
        self.severity_classifier = severity_classifier or SeverityClassifier()
        self._validate_weights(self.weights)

    def aggregate(
        self,
        model_contributions: Dict[str, ModelContribution],
        aggregation_latency_ms: float = 0.0,
    ) -> EnsemblePrediction:
        """
        Aggregate individual model contributions into a unified EnsemblePrediction.

        Args:
            model_contributions: Dict mapping model_name -> ModelContribution.
            aggregation_latency_ms: Time taken to execute ensemble aggregation.

        Returns:
            EnsemblePrediction with composite risk score, severity, and telemetry.
        """
        available_models: List[str] = []
        missing_models: List[str] = []
        effective_contributions: Dict[str, ModelContribution] = {}

        # 1. Identify Available vs. Missing Models
        all_expected_models = list(self.weights.keys())
        for m_name in all_expected_models:
            contrib = model_contributions.get(m_name)
            if contrib is not None and contrib.is_available and contrib.error is None:
                available_models.append(m_name)
            else:
                missing_models.append(m_name)

        if not available_models:
            logger.error("No valid model predictions available for ensemble aggregation.")
            raise RuntimeError("Cannot compute ensemble prediction: zero participating models.")

        # 2. Dynamic Weight Renormalization
        raw_available_weight = sum(self.weights.get(m, 0.0) for m in available_models)
        if raw_available_weight <= 0:
            # Fallback to equal weighting among available models
            raw_available_weight = len(available_models)
            effective_weights = {m: 1.0 / len(available_models) for m in available_models}
        else:
            effective_weights = {
                m: self.weights.get(m, 0.0) / raw_available_weight for m in available_models
            }

        # 3. Weighted Composite Risk Score & Decisions
        weighted_score_sum = 0.0
        models_anomalous = 0
        models_normal = 0
        latency_breakdown = LatencyBreakdown(ensemble_aggregation_ms=aggregation_latency_ms)

        for m_name, contrib in model_contributions.items():
            if m_name in available_models:
                eff_w = effective_weights[m_name]
                contrib.effective_weight = round(eff_w, 4)
                weighted_score_sum += contrib.normalized_score * eff_w
                effective_contributions[m_name] = contrib

                if contrib.is_anomaly:
                    models_anomalous += 1
                else:
                    models_normal += 1

                # Record per-model latencies
                if m_name == "isolation_forest":
                    latency_breakdown.isolation_forest_ms = contrib.latency_ms
                elif m_name == "autoencoder":
                    latency_breakdown.autoencoder_ms = contrib.latency_ms
                elif m_name == "lstm_autoencoder":
                    latency_breakdown.lstm_autoencoder_ms = contrib.latency_ms
                elif m_name == "random_forest":
                    latency_breakdown.random_forest_ms = contrib.latency_ms
            else:
                contrib.effective_weight = 0.0
                effective_contributions[m_name] = contrib

        total_exec_ms = (
            latency_breakdown.isolation_forest_ms
            + latency_breakdown.autoencoder_ms
            + latency_breakdown.lstm_autoencoder_ms
            + latency_breakdown.random_forest_ms
            + aggregation_latency_ms
        )
        latency_breakdown.total_ms = round(total_exec_ms, 3)

        composite_risk_score = float(np.clip(weighted_score_sum, 0.0, 100.0))

        # 4. Final Classification Decision
        is_anomaly = composite_risk_score >= self.decision_threshold
        prediction_str = "attack" if is_anomaly else "normal"

        # 5. Severity Tier Classification
        severity_tier = self.severity_classifier.classify(composite_risk_score)

        # 6. Model Agreement / Consensus Metrics
        total_avail = len(available_models)
        majority_count = max(models_anomalous, models_normal)
        agreement_ratio = float(majority_count / total_avail) if total_avail > 0 else 1.0
        disagreement_ratio = 1.0 - agreement_ratio
        consensus_pred = "anomaly" if models_anomalous >= models_normal else "normal"

        agreement = ModelAgreement(
            models_total=len(all_expected_models),
            models_available=total_avail,
            models_anomalous=models_anomalous,
            models_normal=models_normal,
            agreement_ratio=round(agreement_ratio, 4),
            disagreement_ratio=round(disagreement_ratio, 4),
            consensus_prediction=consensus_pred,
        )

        # 7. Heuristic Reliability Indicator
        # Combines availability coverage and inter-model consensus
        availability_ratio = total_avail / len(all_expected_models)
        reliability = float(0.6 * availability_ratio + 0.4 * agreement_ratio)

        return EnsemblePrediction(
            model_name="ensemble",
            model_version="1.0.0",
            prediction=prediction_str,
            is_anomaly=is_anomaly,
            risk_score=round(composite_risk_score, 2),
            severity=severity_tier,
            decision_threshold=self.decision_threshold,
            reliability_score=round(reliability, 4),
            agreement=agreement,
            contributions=effective_contributions,
            participating_models=available_models,
            missing_models=missing_models,
            latency=latency_breakdown,
        )

    def _load_default_weights(self) -> Dict[str, float]:
        return {
            "isolation_forest": settings.ENSEMBLE_ISOLATION_FOREST_WEIGHT,
            "autoencoder": settings.ENSEMBLE_AUTOENCODER_WEIGHT,
            "lstm_autoencoder": settings.ENSEMBLE_LSTM_WEIGHT,
            "random_forest": settings.ENSEMBLE_RANDOM_FOREST_WEIGHT,
        }

    def _validate_weights(self, weights: Dict[str, float]) -> None:
        if not weights:
            raise ValueError("Ensemble weights dictionary cannot be empty.")
        for k, v in weights.items():
            if v < 0:
                raise ValueError(f"Ensemble weight for '{k}' must be non-negative, got {v}")
        if sum(weights.values()) <= 0:
            raise ValueError("Sum of ensemble weights must be greater than zero.")
