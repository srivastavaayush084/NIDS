import time
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd
import torch

from backend.app.core.logging import logger
from backend.app.ml.models.autoencoder import AutoencoderDetector
from backend.app.ml.ensemble.severity import classify_severity
from backend.app.ml.explainability.base_explainer import BaseExplainer
from backend.app.ml.explainability.schemas import ModelExplanation
from backend.app.ml.explainability.feature_attribution import (
    resolve_feature_names,
    build_feature_contributions,
    generate_natural_language_summary,
    get_model_limitations,
)


class AutoencoderExplainer(BaseExplainer):
    """
    Explainable AI engine for Dense Autoencoder anomaly detection.
    Explains anomalies via per-feature squared reconstruction errors $(x_j - \\hat{x}_j)^2$.
    """

    def __init__(
        self,
        model: AutoencoderDetector,
        dataset_name: str = "generic",
        feature_names: Optional[List[str]] = None,
        top_k: int = 10,
    ):
        super().__init__(
            model_name="autoencoder",
            explanation_method="autoencoder_reconstruction_error",
            dataset_name=dataset_name,
            feature_names=feature_names,
            top_k=top_k,
        )
        self.model = model
        self.is_initialized = model.is_trained

    def explain_instance(
        self,
        X_sample: Union[np.ndarray, pd.DataFrame, pd.Series, Dict[str, Any]],
        top_k: Optional[int] = None,
        **kwargs: Any,
    ) -> ModelExplanation:
        """
        Explain a single Autoencoder anomaly prediction using per-feature reconstruction error.
        """
        k = top_k or self.top_k
        start_total = time.perf_counter()

        X_arr = self._ensure_2d_numpy(X_sample)
        num_features = X_arr.shape[1]
        if not self.feature_names or len(self.feature_names) != num_features:
            self.feature_names = resolve_feature_names(self.feature_names, num_features)

        # 1. Base Prediction step
        start_pred = time.perf_counter()
        risk_score = float(self.model.compute_anomaly_scores(X_arr)[0])
        sample_mse = float(self.model.compute_reconstruction_error(X_arr)[0])
        pred_latency_ms = (time.perf_counter() - start_pred) * 1000.0

        is_anomaly = bool(sample_mse >= self.model.reconstruction_threshold)
        prediction = "attack" if is_anomaly else "normal"
        severity = classify_severity(risk_score)

        # 2. Reconstruction Explanation step
        start_exp = time.perf_counter()
        if not self.model.is_trained or self.model.network is None:
            raise RuntimeError("Autoencoder model is not trained.")

        self.model.network.eval()
        with torch.no_grad():
            x_tensor = torch.from_numpy(X_arr).float().to(self.model.device)
            recon_tensor = self.model.network(x_tensor)
            recon_arr = recon_tensor.cpu().numpy()[0]
            orig_arr = X_arr[0]
            feature_errors = (orig_arr - recon_arr) ** 2

        # Signed contributions: feature error relative to mean feature error
        # Features with above-average error push the reconstruction MSE upward (increases_risk)
        mean_feat_err = float(np.mean(feature_errors))
        contributions = feature_errors - mean_feat_err

        exp_latency_ms = (time.perf_counter() - start_exp) * 1000.0
        total_latency_ms = (time.perf_counter() - start_total) * 1000.0

        # 3. Construct ranked feature contributions
        all_ranked, top_pos, top_neg = build_feature_contributions(
            feature_names=self.feature_names,
            feature_values=orig_arr,
            contributions=contributions,
            reconstructed_values=recon_arr,
            reconstruction_errors=feature_errors,
            top_k=k,
        )

        # 4. Generate dynamic summary
        summary = generate_natural_language_summary(
            model_name="autoencoder",
            prediction=prediction,
            risk_score=risk_score,
            severity=severity,
            top_pos_features=top_pos,
            top_neg_features=top_neg,
        )

        limitations = get_model_limitations("autoencoder", self.explanation_method)

        return ModelExplanation(
            model_name="autoencoder",
            model_version="1.0.0",
            dataset_name=self.dataset_name,
            prediction=prediction,
            is_anomaly=is_anomaly,
            risk_score=risk_score,
            severity=severity,
            decision_threshold=round(self.model.reconstruction_threshold, 6),
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
            metadata={"sample_mse": round(sample_mse, 6)},
        )
