import time
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd
import torch

from backend.app.core.logging import logger
from backend.app.ml.models.lstm_autoencoder import LSTMAutoencoderDetector
from backend.app.ml.ensemble.severity import classify_severity
from backend.app.ml.sequence.sequence_validator import validate_sequence_data
from backend.app.ml.explainability.base_explainer import BaseExplainer
from backend.app.ml.explainability.schemas import ModelExplanation, TimestepContribution
from backend.app.ml.explainability.feature_attribution import (
    resolve_feature_names,
    build_feature_contributions,
    generate_natural_language_summary,
    get_model_limitations,
)


class LSTMAutoencoderExplainer(BaseExplainer):
    """
    Explainable AI engine for Sequential LSTM Autoencoder anomaly detection.
    Performs hierarchical temporal decomposition across sequence timesteps and feature dimensions.
    """

    def __init__(
        self,
        model: LSTMAutoencoderDetector,
        dataset_name: str = "generic",
        feature_names: Optional[List[str]] = None,
        top_k: int = 10,
    ):
        super().__init__(
            model_name="lstm_autoencoder",
            explanation_method="lstm_hierarchical_reconstruction",
            dataset_name=dataset_name,
            feature_names=feature_names,
            top_k=top_k,
        )
        self.model = model
        self.is_initialized = model.is_trained

    def explain_instance(
        self,
        X_sample: Union[np.ndarray, List[Any]],
        top_k: Optional[int] = None,
        **kwargs: Any,
    ) -> ModelExplanation:
        """
        Explain a single LSTM temporal sequence anomaly prediction.
        Input should be shape (1, seq_len, D) or (seq_len, D).
        """
        k = top_k or self.top_k
        start_total = time.perf_counter()

        # Validate and format sequence window (1, T, D)
        seq_arr = validate_sequence_data(
            X_sample,
            expected_seq_len=self.model.seq_len,
            expected_feat_dim=self.model.input_dim or (np.asarray(X_sample).shape[-1] if hasattr(X_sample, '__len__') else None),
            allow_single_sequence=True,
        )

        seq_len = seq_arr.shape[1]
        num_features = seq_arr.shape[2]
        if not self.feature_names or len(self.feature_names) != num_features:
            self.feature_names = resolve_feature_names(self.feature_names, num_features)

        # 1. Base Prediction step
        start_pred = time.perf_counter()
        risk_score = float(self.model.compute_anomaly_scores(seq_arr)[0])
        seq_mse = float(self.model.compute_reconstruction_error(seq_arr)[0])
        pred_latency_ms = (time.perf_counter() - start_pred) * 1000.0

        is_anomaly = bool(seq_mse >= self.model.reconstruction_threshold)
        prediction = "attack" if is_anomaly else "normal"
        severity = classify_severity(risk_score)

        # 2. Hierarchical Temporal Explanation step
        start_exp = time.perf_counter()
        if not self.model.is_trained or self.model.network is None:
            raise RuntimeError("LSTM Autoencoder model is not trained.")

        self.model.network.eval()
        with torch.no_grad():
            x_tensor = torch.from_numpy(seq_arr).float().to(self.model.device)
            recon_tensor = self.model.network(x_tensor)
            recon_arr = recon_tensor.cpu().numpy()[0]  # Shape (T, D)
            orig_arr = seq_arr[0]                      # Shape (T, D)
            diff_sq = (orig_arr - recon_arr) ** 2      # Shape (T, D)

        # Per-timestep MSE: mean across feature dimension D
        timestep_errors = np.mean(diff_sq, axis=1)     # Shape (T,)
        total_err_sum = float(np.sum(timestep_errors)) + 1e-9
        relative_timestep_contribs = timestep_errors / total_err_sum

        # Rank timesteps by error descending
        timestep_ranks = np.argsort(-timestep_errors)
        timestep_contributions: List[TimestepContribution] = []

        for rank_idx, t in enumerate(timestep_ranks, start=1):
            t_err = float(timestep_errors[t])
            t_rel = float(relative_timestep_contribs[t])
            # Approximate timestep-level score
            t_score = float(np.clip((t_err / (self.model.reconstruction_threshold + 1e-6)) * 50.0, 0.0, 100.0))

            # Feature breakdown for this specific timestep
            t_feat_errs = diff_sq[t]
            t_feat_ranked, _, _ = build_feature_contributions(
                feature_names=self.feature_names,
                feature_values=orig_arr[t],
                contributions=t_feat_errs - np.mean(t_feat_errs),
                reconstructed_values=recon_arr[t],
                reconstruction_errors=t_feat_errs,
                top_k=3,
            )

            timestep_contributions.append(
                TimestepContribution(
                    timestep_index=int(t),
                    timestep_label=f"t_{t}",
                    reconstruction_error=round(t_err, 6),
                    anomaly_score=round(t_score, 2),
                    relative_contribution=round(t_rel, 4),
                    top_features=t_feat_ranked,
                    rank=rank_idx,
                )
            )

        # Re-sort timestep contributions chronologically or keep rank metadata accessible
        # Overall feature-level error across all timesteps: mean across time dimension T
        overall_feature_errors = np.mean(diff_sq, axis=0)  # Shape (D,)
        mean_feat_err = float(np.mean(overall_feature_errors))
        overall_contributions = overall_feature_errors - mean_feat_err

        # Representative feature values: taken from peak anomalous timestep
        peak_t = int(timestep_ranks[0])
        rep_feat_values = orig_arr[peak_t]
        rep_recon_values = recon_arr[peak_t]

        all_ranked, top_pos, top_neg = build_feature_contributions(
            feature_names=self.feature_names,
            feature_values=rep_feat_values,
            contributions=overall_contributions,
            reconstructed_values=rep_recon_values,
            reconstruction_errors=overall_feature_errors,
            top_k=k,
        )

        exp_latency_ms = (time.perf_counter() - start_exp) * 1000.0
        total_latency_ms = (time.perf_counter() - start_total) * 1000.0

        # 3. Generate dynamic summary
        summary = generate_natural_language_summary(
            model_name="lstm_autoencoder",
            prediction=prediction,
            risk_score=risk_score,
            severity=severity,
            top_pos_features=top_pos,
            top_neg_features=top_neg,
        )

        limitations = get_model_limitations("lstm_autoencoder", self.explanation_method)

        return ModelExplanation(
            model_name="lstm_autoencoder",
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
            timestep_contributions=timestep_contributions,
            summary=summary,
            limitations=limitations,
            prediction_latency_ms=round(pred_latency_ms, 3),
            explanation_latency_ms=round(exp_latency_ms, 3),
            total_latency_ms=round(total_latency_ms, 3),
            metadata={
                "sequence_length": seq_len,
                "peak_anomalous_timestep": f"t_{peak_t}",
                "sequence_mse": round(seq_mse, 6),
            },
        )
