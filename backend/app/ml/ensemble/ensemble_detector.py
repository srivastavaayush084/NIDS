import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ml.registry.model_registry import model_registry
from backend.app.ml.models.isolation_forest import IsolationForestDetector
from backend.app.ml.models.autoencoder import AutoencoderDetector
from backend.app.ml.models.lstm_autoencoder import LSTMAutoencoderDetector
from backend.app.ml.models.random_forest import RandomForestClassifierModel
from backend.app.ml.ensemble.schemas import (
    ModelContribution,
    ModelAgreement,
    LatencyBreakdown,
    EnsemblePrediction,
)
from backend.app.ml.ensemble.score_normalizer import ScoreNormalizer
from backend.app.ml.ensemble.risk_scorer import EnsembleRiskScorer
from backend.app.ml.ensemble.severity import SeverityClassifier
from backend.app.ml.sequence.sequence_builder import SequenceBuilder


class EnsembleDetector:
    """
    Unified Ensemble Detection and Risk Scoring Engine.

    Coordinates inference across:
    1. Isolation Forest (Unsupervised Anomaly Detector)
    2. Dense Autoencoder (Deep Learning Reconstruction Detector)
    3. LSTM Autoencoder (Sequential Temporal Reconstruction Detector)
    4. Random Forest (Supervised Baseline Classifier)

    Orchestration Flow:
    1. Feature Input Inspection & Sequence Compatibility Check
    2. Individual Model Inference & Native Metric Extraction
    3. Score Normalization to [0.0, 100.0] Risk Scale
    4. Dynamic Weight Renormalization for Missing/Incompatible Models
    5. Weighted Composite Risk Scoring & Severity Tier Mapping
    6. Consensus / Agreement & Heuristic Reliability Calculation
    """

    def __init__(
        self,
        isolation_forest: Optional[IsolationForestDetector] = None,
        autoencoder: Optional[AutoencoderDetector] = None,
        lstm_autoencoder: Optional[LSTMAutoencoderDetector] = None,
        random_forest: Optional[RandomForestClassifierModel] = None,
        score_normalizer: Optional[ScoreNormalizer] = None,
        risk_scorer: Optional[EnsembleRiskScorer] = None,
        severity_classifier: Optional[SeverityClassifier] = None,
        dataset_name: str = "synthetic",
        feature_names: Optional[List[str]] = None,
    ):
        self.isolation_forest = isolation_forest
        self.autoencoder = autoencoder
        self.lstm_autoencoder = lstm_autoencoder
        self.random_forest = random_forest
        self.dataset_name = dataset_name
        self.feature_names = feature_names or []

        self.normalizer = score_normalizer or ScoreNormalizer()
        self.severity_classifier = severity_classifier or SeverityClassifier()
        self.risk_scorer = risk_scorer or EnsembleRiskScorer(severity_classifier=self.severity_classifier)

    @classmethod
    def load(
        cls,
        dataset_name: str = "synthetic",
        custom_weights: Optional[Dict[str, float]] = None,
        decision_threshold: Optional[float] = None,
    ) -> "EnsembleDetector":
        """
        Factory method that discovers and loads all active registered model artifacts
        for the specified dataset from the central ModelRegistry.
        """
        logger.info(f"Instantiating EnsembleDetector for dataset='{dataset_name}'")
        
        feature_names: List[str] = []

        # 1. Discover & Load Isolation Forest
        if_det = None
        if_meta = model_registry.get_model("isolation_forest", dataset=dataset_name)
        if if_meta and Path(if_meta.get("artifact_path", "")).exists():
            try:
                if_det = IsolationForestDetector.load(if_meta["artifact_path"])
                if if_meta.get("feature_names"):
                    feature_names = if_meta["feature_names"]
                logger.info(f"Loaded Isolation Forest artifact: {if_meta['artifact_path']}")
            except Exception as e:
                logger.warning(f"Could not load Isolation Forest: {e}")

        # 2. Discover & Load Autoencoder
        ae_det = None
        ae_meta = model_registry.get_model("autoencoder", dataset=dataset_name)
        if ae_meta and Path(ae_meta.get("artifact_path", "")).exists():
            try:
                ae_det = AutoencoderDetector.load(ae_meta["artifact_path"])
                if not feature_names and ae_meta.get("feature_names"):
                    feature_names = ae_meta["feature_names"]
                logger.info(f"Loaded Autoencoder artifact: {ae_meta['artifact_path']}")
            except Exception as e:
                logger.warning(f"Could not load Autoencoder: {e}")

        # 3. Discover & Load LSTM Autoencoder
        lstm_det = None
        lstm_meta = model_registry.get_model("lstm_autoencoder", dataset=dataset_name)
        if lstm_meta and Path(lstm_meta.get("artifact_path", "")).exists():
            try:
                lstm_det = LSTMAutoencoderDetector.load(lstm_meta["artifact_path"])
                if not feature_names and lstm_meta.get("feature_names"):
                    feature_names = lstm_meta["feature_names"]
                logger.info(f"Loaded LSTM Autoencoder artifact: {lstm_meta['artifact_path']}")
            except Exception as e:
                logger.warning(f"Could not load LSTM Autoencoder: {e}")

        # 4. Discover & Load Random Forest
        rf_det = None
        rf_meta = model_registry.get_model("random_forest", dataset=dataset_name)
        if rf_meta and Path(rf_meta.get("artifact_path", "")).exists():
            try:
                rf_det = RandomForestClassifierModel.load(rf_meta["artifact_path"])
                if not feature_names and rf_meta.get("feature_names"):
                    feature_names = rf_meta["feature_names"]
                logger.info(f"Loaded Random Forest artifact: {rf_meta['artifact_path']}")
            except Exception as e:
                logger.warning(f"Could not load Random Forest: {e}")

        # If feature_names still empty, check model attributes
        if not feature_names:
            feature_names = getattr(rf_det, "feature_names_", []) or getattr(if_det, "feature_names_", [])

        # 5. Load Calibration State if available
        calib_file = settings.PREPROCESSING_DIR / dataset_name / "ensemble_calibration.json"
        normalizer = ScoreNormalizer.load_calibration(calib_file) if calib_file.exists() else ScoreNormalizer()

        scorer = EnsembleRiskScorer(
            weights=custom_weights,
            decision_threshold=decision_threshold,
        )

        return cls(
            isolation_forest=if_det,
            autoencoder=ae_det,
            lstm_autoencoder=lstm_det,
            random_forest=rf_det,
            score_normalizer=normalizer,
            risk_scorer=scorer,
            dataset_name=dataset_name,
            feature_names=feature_names,
        )

    def predict_single(
        self,
        features: Union[np.ndarray, List[float], pd.Series, Dict[str, float]],
        sequence_window: Optional[Union[np.ndarray, List[List[float]]]] = None,
    ) -> EnsemblePrediction:
        """
        Execute unified ensemble detection on a single network flow record.

        Args:
            features: 1D feature array, Series, or dict representing tabular flow attributes.
            sequence_window: Optional 2D temporal sequence window (shape: [T, n_features])
                             for sequential models like LSTM Autoencoder.

        Returns:
            Standardized EnsemblePrediction object.
        """
        # Format 2D array of shape (1, n_features)
        if isinstance(features, dict):
            if self.feature_names and any(k in features for k in self.feature_names):
                feature_vals = [float(features.get(k, 0.0)) for k in self.feature_names]
                X_2d = np.array([feature_vals], dtype=np.float32)
            else:
                X_2d = np.array([list(features.values())], dtype=np.float32)
        elif isinstance(features, pd.DataFrame):
            if self.feature_names and any(c in features.columns for c in self.feature_names):
                aligned = features.reindex(columns=self.feature_names, fill_value=0.0)
                X_2d = aligned.to_numpy(dtype=np.float32)
            else:
                X_2d = features.to_numpy().reshape(1, -1).astype(np.float32)
        elif isinstance(features, pd.Series):
            if self.feature_names and any(c in features.index for c in self.feature_names):
                aligned = features.reindex(self.feature_names, fill_value=0.0)
                X_2d = aligned.to_numpy(dtype=np.float32).reshape(1, -1)
            else:
                X_2d = features.to_numpy().reshape(1, -1).astype(np.float32)
        else:
            X_2d = np.asarray(features, dtype=np.float32).reshape(1, -1)

        contributions: Dict[str, ModelContribution] = {}

        # 1. Isolation Forest Inference
        t_start = time.perf_counter()
        if self.isolation_forest is not None and getattr(self.isolation_forest, "is_trained", False):
            try:
                raw_score = float(self.isolation_forest.score_samples(X_2d)[0])
                anom_score = float(self.isolation_forest.compute_anomaly_scores(X_2d)[0])
                th = getattr(self.isolation_forest, "anomaly_threshold", 50.0)
                is_anom = anom_score >= th
                norm_score = self.normalizer.normalize("isolation_forest", anom_score, th)
                lat_ms = (time.perf_counter() - t_start) * 1000.0

                contributions["isolation_forest"] = ModelContribution(
                    model_name="isolation_forest",
                    prediction="attack" if is_anom else "normal",
                    is_anomaly=is_anom,
                    native_score=raw_score,
                    normalized_score=norm_score,
                    configured_weight=self.risk_scorer.weights.get("isolation_forest", 0.25),
                    effective_weight=0.0,  # Computed by risk_scorer
                    decision_threshold=th,
                    latency_ms=round(lat_ms, 3),
                    is_available=True,
                )
            except Exception as e:
                logger.error(f"Isolation Forest inference error: {e}")
                contributions["isolation_forest"] = self._error_contribution("isolation_forest", str(e))
        else:
            contributions["isolation_forest"] = self._missing_contribution("isolation_forest", "Model not loaded or not trained")

        # 2. Dense Autoencoder Inference
        t_start = time.perf_counter()
        if self.autoencoder is not None and getattr(self.autoencoder, "is_trained", False):
            try:
                raw_err = float(self.autoencoder.compute_reconstruction_error(X_2d)[0])
                th = getattr(self.autoencoder, "reconstruction_threshold", 0.05)
                is_anom = raw_err >= th
                norm_score = self.normalizer.normalize("autoencoder", raw_err, th)
                lat_ms = (time.perf_counter() - t_start) * 1000.0

                contributions["autoencoder"] = ModelContribution(
                    model_name="autoencoder",
                    prediction="attack" if is_anom else "normal",
                    is_anomaly=is_anom,
                    native_score=raw_err,
                    normalized_score=norm_score,
                    configured_weight=self.risk_scorer.weights.get("autoencoder", 0.25),
                    effective_weight=0.0,
                    decision_threshold=th,
                    latency_ms=round(lat_ms, 3),
                    is_available=True,
                )
            except Exception as e:
                logger.error(f"Autoencoder inference error: {e}")
                contributions["autoencoder"] = self._error_contribution("autoencoder", str(e))
        else:
            contributions["autoencoder"] = self._missing_contribution("autoencoder", "Model not loaded or not trained")

        # 3. LSTM Autoencoder Inference
        t_start = time.perf_counter()
        if sequence_window is not None:
            if self.lstm_autoencoder is not None and getattr(self.lstm_autoencoder, "is_trained", False):
                try:
                    seq_arr = np.asarray(sequence_window, dtype=np.float32)
                    if seq_arr.ndim == 2:
                        seq_3d = np.expand_dims(seq_arr, axis=0)  # Shape (1, T, n_features)
                    else:
                        seq_3d = seq_arr
                    
                    raw_seq_err = float(self.lstm_autoencoder.compute_reconstruction_error(seq_3d)[0])
                    th = getattr(self.lstm_autoencoder, "reconstruction_threshold", 0.05)
                    is_anom = raw_seq_err >= th
                    norm_score = self.normalizer.normalize("lstm_autoencoder", raw_seq_err, th)
                    lat_ms = (time.perf_counter() - t_start) * 1000.0

                    contributions["lstm_autoencoder"] = ModelContribution(
                        model_name="lstm_autoencoder",
                        prediction="attack" if is_anom else "normal",
                        is_anomaly=is_anom,
                        native_score=raw_seq_err,
                        normalized_score=norm_score,
                        configured_weight=self.risk_scorer.weights.get("lstm_autoencoder", 0.25),
                        effective_weight=0.0,
                        decision_threshold=th,
                        latency_ms=round(lat_ms, 3),
                        is_available=True,
                    )
                except Exception as e:
                    logger.error(f"LSTM Autoencoder inference error: {e}")
                    contributions["lstm_autoencoder"] = self._error_contribution("lstm_autoencoder", str(e))
            else:
                contributions["lstm_autoencoder"] = self._missing_contribution("lstm_autoencoder", "Model not loaded or not trained")
        else:
            # Single-record evaluation: sequence not provided, mark explicitly as unavailable without fabricating sequences
            contributions["lstm_autoencoder"] = self._missing_contribution(
                "lstm_autoencoder",
                "Single-record input: temporal sequence window not provided",
            )

        # 4. Random Forest Inference
        t_start = time.perf_counter()
        if self.random_forest is not None and getattr(self.random_forest, "is_trained", False):
            try:
                probs = self.random_forest.predict_proba(X_2d)
                prob_attack = float(probs[0, 1])
                th = getattr(self.random_forest, "decision_threshold", 0.50)
                is_anom = prob_attack >= th
                norm_score = self.normalizer.normalize("random_forest", prob_attack, th)
                lat_ms = (time.perf_counter() - t_start) * 1000.0

                contributions["random_forest"] = ModelContribution(
                    model_name="random_forest",
                    prediction="attack" if is_anom else "normal",
                    is_anomaly=is_anom,
                    native_score=prob_attack,
                    normalized_score=norm_score,
                    configured_weight=self.risk_scorer.weights.get("random_forest", 0.25),
                    effective_weight=0.0,
                    decision_threshold=th,
                    latency_ms=round(lat_ms, 3),
                    is_available=True,
                )
            except Exception as e:
                logger.error(f"Random Forest inference error: {e}")
                contributions["random_forest"] = self._error_contribution("random_forest", str(e))
        else:
            contributions["random_forest"] = self._missing_contribution("random_forest", "Model not loaded or not trained")

        # 5. Ensemble Risk Aggregation & Scoring
        t_agg = time.perf_counter()
        prediction = self.risk_scorer.aggregate(
            model_contributions=contributions,
            aggregation_latency_ms=round((time.perf_counter() - t_agg) * 1000.0, 3),
        )
        return prediction

    def predict_batch(
        self,
        X_test: Union[np.ndarray, pd.DataFrame, List[Dict[str, Any]]],
        X_seq: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, np.ndarray, List[EnsemblePrediction]]:
        """
        Execute batch ensemble prediction across multiple flow records with vectorized multi-model evaluation.

        Args:
            X_test: 2D feature matrix of shape (N_records, n_features), DataFrame, or list of dicts.
            X_seq: Optional 3D sequence array for LSTM. If None, builds sequences if X_test allows.

        Returns:
            Tuple of:
            - y_pred: 1D binary prediction array (0 = Normal, 1 = Attack)
            - risk_scores: 1D continuous risk score array [0.0, 100.0]
            - predictions_list: List of detailed EnsemblePrediction objects
        """
        if isinstance(X_test, pd.DataFrame):
            if self.feature_names and any(c in X_test.columns for c in self.feature_names):
                aligned = X_test.reindex(columns=self.feature_names, fill_value=0.0)
                X_arr = aligned.to_numpy(dtype=np.float32)
            else:
                X_arr = X_test.to_numpy(dtype=np.float32)
        elif isinstance(X_test, list) and len(X_test) > 0 and isinstance(X_test[0], dict):
            if self.feature_names:
                rows = [[float(d.get(k, 0.0)) for k in self.feature_names] for d in X_test]
                X_arr = np.array(rows, dtype=np.float32)
            else:
                rows = [list(d.values()) for d in X_test]
                X_arr = np.array(rows, dtype=np.float32)
        else:
            X_arr = np.asarray(X_test, dtype=np.float32)

        n_samples = len(X_arr)
        if n_samples == 0:
            return np.array([], dtype=int), np.array([], dtype=float), []

        # Ensure 2D
        if X_arr.ndim == 1:
            X_arr = X_arr.reshape(1, -1)
            n_samples = 1

        # 1. Isolation Forest Vectorized Inference
        if_available = self.isolation_forest is not None and getattr(self.isolation_forest, "is_trained", False)
        if_raw_scores = np.zeros(n_samples, dtype=np.float32)
        if_anom_scores = np.zeros(n_samples, dtype=np.float32)
        if_norm_scores = np.zeros(n_samples, dtype=np.float32)
        if_lat_each = 0.0
        if_th = getattr(self.isolation_forest, "anomaly_threshold", 50.0) if self.isolation_forest else 50.0
        if if_available:
            try:
                t0 = time.perf_counter()
                if_raw_scores = self.isolation_forest.score_samples(X_arr)
                if_anom_scores = self.isolation_forest.compute_anomaly_scores(X_arr)
                if_th = getattr(self.isolation_forest, "anomaly_threshold", 50.0)
                if_norm_scores = np.array([self.normalizer.normalize("isolation_forest", float(s), if_th) for s in if_anom_scores], dtype=np.float32)
                if_lat_each = ((time.perf_counter() - t0) * 1000.0) / n_samples
            except Exception as e:
                logger.error(f"Vectorized Isolation Forest batch error: {e}")
                if_available = False

        # 2. Autoencoder Vectorized Inference
        ae_available = self.autoencoder is not None and getattr(self.autoencoder, "is_trained", False)
        ae_raw_errs = np.zeros(n_samples, dtype=np.float32)
        ae_norm_scores = np.zeros(n_samples, dtype=np.float32)
        ae_lat_each = 0.0
        ae_th = getattr(self.autoencoder, "reconstruction_threshold", 0.05) if self.autoencoder else 0.05
        if ae_available:
            try:
                t0 = time.perf_counter()
                ae_raw_errs = self.autoencoder.compute_reconstruction_error(X_arr)
                ae_th = getattr(self.autoencoder, "reconstruction_threshold", 0.05)
                ae_norm_scores = np.array([self.normalizer.normalize("autoencoder", float(e), ae_th) for e in ae_raw_errs], dtype=np.float32)
                ae_lat_each = ((time.perf_counter() - t0) * 1000.0) / n_samples
            except Exception as e:
                logger.error(f"Vectorized Autoencoder batch error: {e}")
                ae_available = False

        # 3. Random Forest Vectorized Inference
        rf_available = self.random_forest is not None and getattr(self.random_forest, "is_trained", False)
        rf_probs = np.zeros(n_samples, dtype=np.float32)
        rf_norm_scores = np.zeros(n_samples, dtype=np.float32)
        rf_lat_each = 0.0
        rf_th = getattr(self.random_forest, "decision_threshold", 0.50) if self.random_forest else 0.50
        if rf_available:
            try:
                t0 = time.perf_counter()
                probs = self.random_forest.predict_proba(X_arr)
                rf_probs = probs[:, 1]
                rf_th = getattr(self.random_forest, "decision_threshold", 0.50)
                rf_norm_scores = np.array([self.normalizer.normalize("random_forest", float(p), rf_th) for p in rf_probs], dtype=np.float32)
                rf_lat_each = ((time.perf_counter() - t0) * 1000.0) / n_samples
            except Exception as e:
                logger.error(f"Vectorized Random Forest batch error: {e}")
                rf_available = False

        # 4. LSTM Vectorized Inference (precomputed for batch throughput)
        seq_len = getattr(self.lstm_autoencoder, "seq_len", 10) if self.lstm_autoencoder else 10
        can_build_seq = len(X_arr) >= seq_len and self.lstm_autoencoder is not None
        lstm_available = self.lstm_autoencoder is not None and getattr(self.lstm_autoencoder, "is_trained", False)
        lstm_raw_errs = np.zeros(n_samples, dtype=np.float32)
        lstm_norm_scores = np.zeros(n_samples, dtype=np.float32)
        lstm_has_pred = np.zeros(n_samples, dtype=bool)
        lstm_th = getattr(self.lstm_autoencoder, "reconstruction_threshold", 0.05) if self.lstm_autoencoder else 0.05
        lstm_lat_each = 0.0

        if lstm_available:
            try:
                t0_lstm = time.perf_counter()
                if X_seq is not None and len(X_seq) > 0:
                    seq_3d = np.asarray(X_seq, dtype=np.float32)
                    raw_errs_all = self.lstm_autoencoder.compute_reconstruction_error(seq_3d)
                    limit = min(n_samples, len(raw_errs_all))
                    lstm_raw_errs[:limit] = raw_errs_all[:limit]
                    lstm_norm_scores[:limit] = [self.normalizer.normalize("lstm_autoencoder", float(e), lstm_th) for e in raw_errs_all[:limit]]
                    lstm_has_pred[:limit] = True
                    lstm_lat_each = ((time.perf_counter() - t0_lstm) * 1000.0) / limit
                elif can_build_seq:
                    pad = np.repeat(X_arr[0:1], seq_len - 1, axis=0)
                    padded_X = np.vstack([pad, X_arr])
                    windows_3d = np.lib.stride_tricks.sliding_window_view(padded_X, (seq_len, X_arr.shape[1]))[:, 0, :, :]
                    batch_sz = 1024
                    err_chunks = []
                    for b_start in range(0, len(windows_3d), batch_sz):
                        b_win = windows_3d[b_start : b_start + batch_sz]
                        err_chunks.append(self.lstm_autoencoder.compute_reconstruction_error(b_win))
                    raw_errs_all = np.concatenate(err_chunks)
                    lstm_raw_errs[:] = raw_errs_all
                    lstm_norm_scores[:] = [self.normalizer.normalize("lstm_autoencoder", float(e), lstm_th) for e in raw_errs_all]
                    lstm_has_pred[:] = True
                    lstm_lat_each = ((time.perf_counter() - t0_lstm) * 1000.0) / len(windows_3d)
            except Exception as e:
                logger.error(f"Vectorized LSTM batch error: {e}")

        y_preds = np.zeros(n_samples, dtype=int)
        risk_scores = np.zeros(n_samples, dtype=float)
        pred_objs: List[EnsemblePrediction] = []

        for i in range(n_samples):
            contributions: Dict[str, ModelContribution] = {}

            if if_available:
                is_anom = if_anom_scores[i] >= if_th
                contributions["isolation_forest"] = ModelContribution(
                    model_name="isolation_forest",
                    prediction="attack" if is_anom else "normal",
                    is_anomaly=bool(is_anom),
                    native_score=float(if_raw_scores[i]),
                    normalized_score=float(if_norm_scores[i]),
                    configured_weight=self.risk_scorer.weights.get("isolation_forest", 0.25),
                    effective_weight=0.0,
                    decision_threshold=if_th,
                    latency_ms=round(if_lat_each, 3),
                    is_available=True,
                )
            else:
                contributions["isolation_forest"] = self._missing_contribution("isolation_forest", "Model not loaded or not trained")

            if ae_available:
                is_anom = ae_raw_errs[i] >= ae_th
                contributions["autoencoder"] = ModelContribution(
                    model_name="autoencoder",
                    prediction="attack" if is_anom else "normal",
                    is_anomaly=bool(is_anom),
                    native_score=float(ae_raw_errs[i]),
                    normalized_score=float(ae_norm_scores[i]),
                    configured_weight=self.risk_scorer.weights.get("autoencoder", 0.25),
                    effective_weight=0.0,
                    decision_threshold=ae_th,
                    latency_ms=round(ae_lat_each, 3),
                    is_available=True,
                )
            else:
                contributions["autoencoder"] = self._missing_contribution("autoencoder", "Model not loaded or not trained")

            if rf_available:
                is_anom = rf_probs[i] >= rf_th
                contributions["random_forest"] = ModelContribution(
                    model_name="random_forest",
                    prediction="attack" if is_anom else "normal",
                    is_anomaly=bool(is_anom),
                    native_score=float(rf_probs[i]),
                    normalized_score=float(rf_norm_scores[i]),
                    configured_weight=self.risk_scorer.weights.get("random_forest", 0.25),
                    effective_weight=0.0,
                    decision_threshold=rf_th,
                    latency_ms=round(rf_lat_each, 3),
                    is_available=True,
                )
            else:
                contributions["random_forest"] = self._missing_contribution("random_forest", "Model not loaded or not trained")

            # LSTM sequence window
            if lstm_has_pred[i]:
                raw_err = float(lstm_raw_errs[i])
                is_anom = raw_err >= lstm_th
                norm_score = float(lstm_norm_scores[i])
                contributions["lstm_autoencoder"] = ModelContribution(
                    model_name="lstm_autoencoder",
                    prediction="attack" if is_anom else "normal",
                    is_anomaly=bool(is_anom),
                    native_score=raw_err,
                    normalized_score=norm_score,
                    configured_weight=self.risk_scorer.weights.get("lstm_autoencoder", 0.25),
                    effective_weight=0.0,
                    decision_threshold=lstm_th,
                    latency_ms=round(lstm_lat_each, 3),
                    is_available=True,
                )
            else:
                contributions["lstm_autoencoder"] = self._missing_contribution("lstm_autoencoder", "Single-record input: temporal sequence window not provided")

            t_agg = time.perf_counter()
            pred = self.risk_scorer.aggregate(
                model_contributions=contributions,
                aggregation_latency_ms=round((time.perf_counter() - t_agg) * 1000.0, 3),
            )
            y_preds[i] = 1 if pred.is_anomaly else 0
            risk_scores[i] = pred.risk_score
            pred_objs.append(pred)

        return y_preds, risk_scores, pred_objs

    def _missing_contribution(self, model_name: str, reason: str) -> ModelContribution:
        return ModelContribution(
            model_name=model_name,
            prediction="normal",
            is_anomaly=False,
            native_score=0.0,
            normalized_score=0.0,
            configured_weight=self.risk_scorer.weights.get(model_name, 0.25),
            effective_weight=0.0,
            decision_threshold=50.0,
            latency_ms=0.0,
            is_available=False,
            error=reason,
        )

    def _error_contribution(self, model_name: str, error_msg: str) -> ModelContribution:
        return ModelContribution(
            model_name=model_name,
            prediction="normal",
            is_anomaly=False,
            native_score=0.0,
            normalized_score=0.0,
            configured_weight=self.risk_scorer.weights.get(model_name, 0.25),
            effective_weight=0.0,
            decision_threshold=50.0,
            latency_ms=0.0,
            is_available=False,
            error=error_msg,
        )
