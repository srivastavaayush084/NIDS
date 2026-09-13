import time
from datetime import datetime, timezone
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
from backend.app.ml.ensemble.ensemble_detector import EnsembleDetector
from backend.app.ml.sequence.sequence_builder import SequenceBuilder
from backend.app.ml.evaluation.metrics import StandardizedMetricsCalculator, StandardizedMetrics
from backend.app.ml.data.utils.data_utils import ensure_dir, save_metadata, load_metadata


class UnifiedModelEvaluator:
    """
    Standardized, multi-architecture evaluation engine capable of evaluating
    Isolation Forest, Dense Autoencoder, LSTM Autoencoder, Random Forest, and Ensemble
    across Standard, Known Attack, and Unseen Attack (Zero-Day Proxy) scenarios.
    """

    SUPPORTED_MODELS = [
        "isolation_forest",
        "autoencoder",
        "lstm_autoencoder",
        "lstm",
        "random_forest",
        "ensemble",
    ]

    SUPPORTED_EVAL_TYPES = [
        "standard",
        "known_attack",
        "unseen_attack",
        "zero_day_proxy",
        "all",
    ]

    @classmethod
    def normalize_model_name(cls, model_name: str) -> str:
        """Normalize model name alias to canonical identifier."""
        m = model_name.lower().strip()
        if m in ("lstm", "lstm_autoencoder", "lstm_detector"):
            return "lstm_autoencoder"
        if m in ("rf", "random_forest", "random_forest_baseline"):
            return "random_forest"
        if m in ("if", "isolation_forest", "iforest"):
            return "isolation_forest"
        if m in ("ae", "autoencoder", "dense_autoencoder"):
            return "autoencoder"
        if m in ("ensemble", "ensemble_detector", "ensemble_model"):
            return "ensemble"
        return m

    @classmethod
    def load_model(
        cls,
        model_name: str,
        dataset: str = "synthetic",
        version: Optional[str] = None,
        artifact_path: Optional[Union[str, Path]] = None,
    ) -> Any:
        """
        Dynamically load a trained model instance via ModelRegistry or explicit path.
        """
        canonical_name = cls.normalize_model_name(model_name)
        if canonical_name == "ensemble":
            return EnsembleDetector.load(dataset_name=dataset)
        
        if artifact_path:
            path = Path(artifact_path)
        else:
            meta = model_registry.get_model(canonical_name, dataset=dataset, version=version)
            if meta and Path(meta.get("artifact_path", "")).exists():
                path = Path(meta["artifact_path"])
            else:
                ext = ".pt" if canonical_name in ("autoencoder", "lstm_autoencoder") else ".joblib"
                v = version or "1.0.0"
                path = settings.MODELS_DIR / f"{canonical_name}_{dataset}_v{v}{ext}"

        if not path.exists():
            raise FileNotFoundError(f"Model artifact not found for '{canonical_name}' at {path}")

        logger.info(f"Loading {canonical_name} artifact from {path}")
        if canonical_name == "isolation_forest":
            return IsolationForestDetector.load(path)
        elif canonical_name == "autoencoder":
            return AutoencoderDetector.load(path)
        elif canonical_name == "lstm_autoencoder":
            return LSTMAutoencoderDetector.load(path)
        elif canonical_name == "random_forest":
            return RandomForestClassifierModel.load(path)
        else:
            raise ValueError(f"Unsupported model name: {model_name}")

    @classmethod
    def evaluate_model(
        cls,
        model: Union[str, Any],
        X_test: Union[np.ndarray, pd.DataFrame],
        y_test_binary: Union[np.ndarray, pd.Series],
        y_test_category: Optional[Union[np.ndarray, pd.Series]] = None,
        unseen_categories: Optional[List[str]] = None,
        dataset_name: str = "synthetic",
        evaluation_type: str = "all",
        threshold: Optional[float] = None,
        model_version: str = "1.0.0",
        output_dir: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate any supported model on test data under chosen evaluation scenario(s).
        """
        eval_type = evaluation_type.lower().strip()
        if eval_type == "zero_day_proxy":
            eval_type = "unseen_attack"

        # 1. Resolve Model Instance & Type
        if isinstance(model, str):
            canonical_name = cls.normalize_model_name(model)
            model_obj = cls.load_model(canonical_name, dataset=dataset_name, version=model_version)
        else:
            model_obj = model
            if isinstance(model_obj, IsolationForestDetector):
                canonical_name = "isolation_forest"
            elif isinstance(model_obj, AutoencoderDetector):
                canonical_name = "autoencoder"
            elif isinstance(model_obj, LSTMAutoencoderDetector):
                canonical_name = "lstm_autoencoder"
            elif isinstance(model_obj, RandomForestClassifierModel):
                canonical_name = "random_forest"
            elif isinstance(model_obj, EnsembleDetector):
                canonical_name = "ensemble"
            else:
                canonical_name = getattr(model_obj, "model_name", "unknown_model")

        # 2. Data Leakage & Integrity Validation
        cls._validate_data_integrity(X_test, y_test_binary)

        # 3. Model Inference & Raw Score Extraction
        t0 = time.perf_counter()
        inference_results = cls._run_inference(
            model=model_obj,
            model_type=canonical_name,
            X_test=X_test,
            y_test_binary=y_test_binary,
            y_test_category=y_test_category,
            threshold_override=threshold,
        )
        t1 = time.perf_counter()
        total_time_ms = (t1 - t0) * 1000.0

        y_true = inference_results["y_true"]
        y_pred = inference_results["y_pred"]
        raw_scores = inference_results["raw_scores"]
        anomaly_scores = inference_results["anomaly_scores"]
        probabilities = inference_results.get("probabilities")
        y_cat = inference_results.get("y_category")
        threshold_used = inference_results["threshold_used"]
        input_unit = inference_results["input_unit"]
        sample_count = len(y_true)

        # 4. Standard Scenario Metrics
        std_metrics = StandardizedMetricsCalculator.calculate_metrics(
            y_true=y_true,
            y_pred=y_pred,
            continuous_scores=anomaly_scores if anomaly_scores is not None else raw_scores,
            inference_time_ms=total_time_ms,
            unit_name=input_unit,
        )

        # 5. Scenario Splits (Known Attack vs Unseen Zero-Day Proxy)
        unseen_set = set([c.lower().strip() for c in (unseen_categories or [])])
        scenarios_results: Dict[str, Any] = {}

        if y_cat is not None and len(y_cat) == len(y_true):
            y_cat_series = pd.Series(y_cat).astype(str).str.lower().str.strip()
            unseen_mask = y_cat_series.isin(unseen_set).to_numpy()
            normal_mask = (y_true == 0)
            known_attack_mask = ((y_true == 1) & (~unseen_mask))

            # A. Known Attack Split (Normal + Known Attacks)
            known_eval_mask = (normal_mask | known_attack_mask)
            if np.any(known_eval_mask):
                known_metrics = StandardizedMetricsCalculator.calculate_metrics(
                    y_true=y_true[known_eval_mask],
                    y_pred=y_pred[known_eval_mask],
                    continuous_scores=anomaly_scores[known_eval_mask] if anomaly_scores is not None else raw_scores[known_eval_mask],
                    inference_time_ms=(total_time_ms * np.sum(known_eval_mask) / sample_count),
                    unit_name=input_unit,
                )
                scenarios_results["known_attack"] = known_metrics.to_dict()

            # B. Unseen Zero-Day Proxy Split (Normal + Unseen Attacks)
            unseen_eval_mask = (normal_mask | unseen_mask)
            if np.any(unseen_eval_mask):
                unseen_metrics = StandardizedMetricsCalculator.calculate_metrics(
                    y_true=y_true[unseen_eval_mask],
                    y_pred=y_pred[unseen_eval_mask],
                    continuous_scores=anomaly_scores[unseen_eval_mask] if anomaly_scores is not None else raw_scores[unseen_eval_mask],
                    inference_time_ms=(total_time_ms * np.sum(unseen_eval_mask) / sample_count),
                    unit_name=input_unit,
                )
                scenarios_results["unseen_attack"] = unseen_metrics.to_dict()

            # C. Per-Category Breakdown
            category_breakdown: Dict[str, Dict[str, Any]] = {}
            for cat in y_cat_series.unique():
                cat_mask = (y_cat_series == cat).to_numpy()
                cat_total = int(np.sum(cat_mask))
                cat_detected = int(np.sum(y_pred[cat_mask] == 1))
                cat_rate = float(cat_detected / cat_total) if cat_total > 0 else 0.0
                cat_fnr = 1.0 - cat_rate if cat != "normal" else None

                category_breakdown[cat] = {
                    "samples": cat_total,
                    "detected_as_attack": cat_detected,
                    "detection_rate": round(cat_rate, 4),
                    "false_negative_rate": round(cat_fnr, 4) if cat_fnr is not None else None,
                    "is_unseen_during_training": cat in unseen_set,
                    "status_label": "UNSEEN DURING TRAINING" if cat in unseen_set else "KNOWN",
                }
        else:
            category_breakdown = {}

        # 6. Assemble Final Standardized Result
        experiment_id = f"eval_{canonical_name}_{dataset_name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        
        result = {
            "experiment_id": experiment_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model_name": canonical_name,
            "model_version": model_version,
            "dataset": dataset_name,
            "evaluation_type": eval_type,
            "input_unit": input_unit,
            "sample_count": sample_count,
            "threshold_used": threshold_used,
            "unseen_categories": list(unseen_set),
            "standard_metrics": std_metrics.to_dict(),
            "scenario_metrics": scenarios_results,
            "category_breakdown": category_breakdown,
            "predictions_summary": {
                "normal_predictions": int(np.sum(y_pred == 0)),
                "attack_predictions": int(np.sum(y_pred == 1)),
                "actual_normal": int(np.sum(y_true == 0)),
                "actual_attack": int(np.sum(y_true == 1)),
            },
            "raw_predictions": {
                "y_true": y_true.tolist(),
                "y_pred": y_pred.tolist(),
                "raw_scores": raw_scores.tolist(),
                "anomaly_scores": anomaly_scores.tolist() if anomaly_scores is not None else None,
                "probabilities": probabilities.tolist() if probabilities is not None else None,
            },
        }

        # 7. Persist to Output Directory if requested
        if output_dir:
            out_p = Path(output_dir)
            ensure_dir(out_p)
            save_path = out_p / f"{canonical_name}_{dataset_name}_{eval_type}_result.json"
            save_metadata(result, save_path)
            logger.info(f"Saved evaluation result to: {save_path}")

        return result

    @classmethod
    def _run_inference(
        cls,
        model: Any,
        model_type: str,
        X_test: Union[np.ndarray, pd.DataFrame],
        y_test_binary: Union[np.ndarray, pd.Series],
        y_test_category: Optional[Union[np.ndarray, pd.Series]] = None,
        threshold_override: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Execute model-specific inference, sequence translation if needed, and thresholding.
        """
        if model_type == "lstm_autoencoder":
            # LSTM sequential processing
            seq_len = getattr(model, "seq_len", 10)
            X_arr = X_test.to_numpy() if isinstance(X_test, pd.DataFrame) else np.asarray(X_test)
            y_arr = y_test_binary.to_numpy() if isinstance(y_test_binary, pd.Series) else np.asarray(y_test_binary)
            y_cat_arr = (
                y_test_category.to_numpy() if isinstance(y_test_category, pd.Series)
                else np.asarray(y_test_category) if y_test_category is not None else None
            )

            # Build sliding sequences
            seq_builder = SequenceBuilder(sequence_length=seq_len, stride=1, label_aggregation="any")
            X_seq, y_seq, y_cat_seq, _ = seq_builder.build_sequences(
                X=X_arr,
                y_binary=y_arr,
                y_category=y_cat_arr,
                raise_if_insufficient=False,
            )

            # Fallback if dataset is smaller than seq_len
            if len(X_seq) == 0:
                logger.warning(f"Test split ({len(X_arr)} rows) < seq_len ({seq_len}). Padding sequence.")
                # Pad to shape (1, seq_len, n_feats)
                n_feats = X_arr.shape[1]
                pad_rows = np.zeros((seq_len - len(X_arr), n_feats))
                padded_X = np.vstack([pad_rows, X_arr])
                X_seq = np.expand_dims(padded_X, axis=0)
                y_seq = np.array([int(np.any(y_arr == 1))])
                y_cat_seq = np.array([str(y_cat_arr[-1])]) if y_cat_arr is not None else None

            th = threshold_override if threshold_override is not None else getattr(model, "reconstruction_threshold", 0.05)
            raw_scores = model.compute_reconstruction_error(X_seq)
            anomaly_scores = model.compute_anomaly_scores(X_seq)
            y_pred = (raw_scores >= th).astype(int)

            return {
                "y_true": y_seq,
                "y_pred": y_pred,
                "raw_scores": raw_scores,
                "anomaly_scores": anomaly_scores,
                "probabilities": None,
                "y_category": y_cat_seq,
                "threshold_used": th,
                "input_unit": "sequences",
            }

        elif model_type == "autoencoder":
            th = threshold_override if threshold_override is not None else getattr(model, "reconstruction_threshold", 0.05)
            raw_scores = model.compute_reconstruction_error(X_test)
            anomaly_scores = model.compute_anomaly_scores(X_test)
            y_pred = (raw_scores >= th).astype(int)
            y_true = np.asarray(y_test_binary, dtype=int).ravel()
            y_cat_arr = np.asarray(y_test_category).ravel() if y_test_category is not None else None

            return {
                "y_true": y_true,
                "y_pred": y_pred,
                "raw_scores": raw_scores,
                "anomaly_scores": anomaly_scores,
                "probabilities": None,
                "y_category": y_cat_arr,
                "threshold_used": th,
                "input_unit": "samples",
            }

        elif model_type == "isolation_forest":
            th = threshold_override if threshold_override is not None else getattr(model, "anomaly_threshold", 50.0)
            raw_scores = model.score_samples(X_test)
            anomaly_scores = model.compute_anomaly_scores(X_test)
            y_pred = (anomaly_scores >= th).astype(int)
            y_true = np.asarray(y_test_binary, dtype=int).ravel()
            y_cat_arr = np.asarray(y_test_category).ravel() if y_test_category is not None else None

            return {
                "y_true": y_true,
                "y_pred": y_pred,
                "raw_scores": raw_scores,
                "anomaly_scores": anomaly_scores,
                "probabilities": None,
                "y_category": y_cat_arr,
                "threshold_used": th,
                "input_unit": "samples",
            }

        elif model_type == "random_forest":
            th = threshold_override if threshold_override is not None else getattr(model, "decision_threshold", 0.5)
            probs = model.predict_proba(X_test)
            prob_attack = probs[:, 1]
            anomaly_scores = np.clip(100.0 * prob_attack, 0.0, 100.0)
            y_pred = (prob_attack >= th).astype(int)
            y_true = np.asarray(y_test_binary, dtype=int).ravel()
            y_cat_arr = np.asarray(y_test_category).ravel() if y_test_category is not None else None

            return {
                "y_true": y_true,
                "y_pred": y_pred,
                "raw_scores": prob_attack,
                "anomaly_scores": anomaly_scores,
                "probabilities": probs,
                "y_category": y_cat_arr,
                "threshold_used": th,
                "input_unit": "samples",
            }

        elif model_type == "ensemble":
            th = threshold_override if threshold_override is not None else getattr(model.risk_scorer, "decision_threshold", 50.0)
            y_pred, risk_scores, _ = model.predict_batch(X_test)
            y_true = np.asarray(y_test_binary, dtype=int).ravel()
            y_cat_arr = np.asarray(y_test_category).ravel() if y_test_category is not None else None

            return {
                "y_true": y_true,
                "y_pred": y_pred,
                "raw_scores": risk_scores,
                "anomaly_scores": risk_scores,
                "probabilities": None,
                "y_category": y_cat_arr,
                "threshold_used": th,
                "input_unit": "samples",
            }

        else:
            raise ValueError(f"Unknown model_type: {model_type}")

    @classmethod
    def _validate_data_integrity(
        cls,
        X: Union[np.ndarray, pd.DataFrame],
        y: Union[np.ndarray, pd.Series],
    ) -> None:
        """Verify absence of target leakage and feature dimensionality integrity."""
        if isinstance(X, pd.DataFrame):
            forbidden = {"label", "binary", "category", "target", "class", "is_attack", "is_anomaly"}
            overlap = forbidden.intersection(set(X.columns.str.lower()))
            if overlap:
                raise ValueError(f"DATA LEAKAGE DETECTED: Feature matrix X contains target column(s): {overlap}")
        if len(X) == 0:
            raise ValueError("Test feature matrix X is empty.")
        if len(y) != len(X):
            raise ValueError(f"Length mismatch between X ({len(X)}) and y ({len(y)})")
