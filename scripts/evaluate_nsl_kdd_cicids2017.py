#!/usr/bin/env python
"""
Strict Test-Set Evaluation and Benchmarking CLI for NSL-KDD & CICIDS2017.

Evaluates:
1. Isolation Forest
2. Random Forest
3. Dense Autoencoder
4. LSTM Autoencoder
5. 4-Model Ensemble Detector

Across both real benchmark datasets imported from Kaggle:
- NSL-KDD (held-out test split: data/processed/nsl_kdd/X_test.csv)
- CICIDS2017 (held-out test split: data/processed/cicids2017/X_test.csv)

Enforces strict threshold integrity: Uses only thresholds determined during
training and validation. Does NOT tune or optimize thresholds on the test set.
Computes real, un-fabricated metrics:
Accuracy, Precision, Recall, F1, ROC-AUC, PR-AUC, FPR, TPR, TN, FP, FN, TP.
"""

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ml.data.utils.data_utils import ensure_dir, load_dataframe, save_metadata
from backend.app.ml.ensemble.ensemble_detector import EnsembleDetector
from backend.app.ml.models.autoencoder import AutoencoderDetector
from backend.app.ml.models.isolation_forest import IsolationForestDetector
from backend.app.ml.models.lstm_autoencoder import LSTMAutoencoderDetector
from backend.app.ml.models.random_forest import RandomForestClassifierModel


def calculate_metrics_dict(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    continuous_scores: np.ndarray,
    model_name: str,
    dataset_name: str,
    threshold: float,
) -> Dict[str, Any]:
    """
    Calculate full suite of classification and security metrics.
    Guarantees TN + FP + FN + TP == len(y_true).
    """
    y_t = np.asarray(y_true, dtype=int).ravel()
    y_p = np.asarray(y_pred, dtype=int).ravel()
    scores = np.asarray(continuous_scores, dtype=float).ravel()
    n_samples = len(y_t)

    # 1. Confusion Matrix
    cm = confusion_matrix(y_t, y_p, labels=[0, 1])
    tn, fp, fn, tp = int(cm[0, 0]), int(cm[0, 1]), int(cm[1, 0]), int(cm[1, 1])
    assert tn + fp + fn + tp == n_samples, f"Confusion matrix sum {tn + fp + fn + tp} != n_samples {n_samples}"

    # 2. Rates
    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
    tpr = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0

    # 3. Standard Classification Metrics
    acc = float(accuracy_score(y_t, y_p))
    prec = float(precision_score(y_t, y_p, zero_division=0))
    rec = float(recall_score(y_t, y_p, zero_division=0))
    f1 = float(f1_score(y_t, y_p, zero_division=0))

    # 4. ROC-AUC and PR-AUC
    roc_auc = None
    pr_auc = None
    unique_classes = np.unique(y_t)
    if len(unique_classes) > 1 and len(scores) == n_samples and not np.isnan(scores).any():
        try:
            roc_auc = float(roc_auc_score(y_t, scores))
        except Exception as e:
            logger.warning(f"ROC-AUC failed for {model_name}: {e}")
        try:
            pr_auc = float(average_precision_score(y_t, scores))
        except Exception as e:
            logger.warning(f"PR-AUC failed for {model_name}: {e}")

    return {
        "dataset": dataset_name,
        "model": model_name,
        "threshold": float(threshold),
        "accuracy": acc,
        "precision": prec,
        "recall": rec,
        "f1": f1,
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "fpr": fpr,
        "tpr": tpr,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "tp": tp,
        "test_samples": n_samples,
    }


def evaluate_dataset(dataset_name: str) -> List[Dict[str, Any]]:
    """
    Run full 5-target evaluation on the given dataset's held-out test split.
    """
    logger.info("=" * 80)
    logger.info(f"EVALUATING DATASET: {dataset_name.upper()} (HELD-OUT TEST SPLIT)")
    logger.info("=" * 80)

    proc_dir = settings.DATA_DIR / "processed" / dataset_name
    X_test_path = proc_dir / "X_test.csv"
    y_test_path = proc_dir / "y_test.csv"

    if not X_test_path.exists() or not y_test_path.exists():
        raise FileNotFoundError(
            f"Processed test split not found in {proc_dir}. "
            f"Please ensure data has been prepared."
        )

    logger.info(f"Loading test feature matrix from: {X_test_path}")
    X_test_df = load_dataframe(X_test_path)
    X_arr = X_test_df.to_numpy(dtype=np.float32)

    logger.info(f"Loading test ground-truth labels from: {y_test_path}")
    y_test_df = load_dataframe(y_test_path)
    y_true = y_test_df["binary"].to_numpy(dtype=int) if "binary" in y_test_df.columns else y_test_df.iloc[:, 0].to_numpy(dtype=int)

    n_samples = len(y_true)
    logger.info(f"Held-out test split contains {n_samples:,} records (Normal: {np.sum(y_true == 0):,}, Attack: {np.sum(y_true == 1):,})")

    results: List[Dict[str, Any]] = []

    # -------------------------------------------------------------------------
    # 1. Isolation Forest
    # -------------------------------------------------------------------------
    logger.info(f"[1/5] Evaluating Isolation Forest on {dataset_name}...")
    if_path = settings.MODELS_DIR / f"isolation_forest_{dataset_name}_v1.0.0.joblib"
    if not if_path.exists():
        raise FileNotFoundError(f"Isolation Forest artifact not found at {if_path}")
    if_model = IsolationForestDetector.load(if_path)
    if_th = float(getattr(if_model, "anomaly_threshold", 50.0))
    logger.info(f"  Isolation Forest production threshold: {if_th}")

    t0 = time.perf_counter()
    if_scores = if_model.compute_anomaly_scores(X_arr)
    if_pred = (if_scores >= if_th).astype(int)
    t_if = time.perf_counter() - t0
    logger.info(f"  Inference finished in {t_if:.2f}s")

    res_if = calculate_metrics_dict(
        y_true=y_true,
        y_pred=if_pred,
        continuous_scores=if_scores,
        model_name="Isolation Forest",
        dataset_name=dataset_name,
        threshold=if_th,
    )
    results.append(res_if)

    # -------------------------------------------------------------------------
    # 2. Random Forest
    # -------------------------------------------------------------------------
    logger.info(f"[2/5] Evaluating Random Forest on {dataset_name}...")
    rf_path = settings.MODELS_DIR / f"random_forest_{dataset_name}_v1.0.0.joblib"
    if not rf_path.exists():
        raise FileNotFoundError(f"Random Forest artifact not found at {rf_path}")
    rf_model = RandomForestClassifierModel.load(rf_path)
    rf_th = float(getattr(rf_model, "decision_threshold", 0.50))
    logger.info(f"  Random Forest production threshold: {rf_th}")

    t0 = time.perf_counter()
    rf_probs = rf_model.predict_attack_probability(X_arr)
    rf_pred = (rf_probs >= rf_th).astype(int)
    t_rf = time.perf_counter() - t0
    logger.info(f"  Inference finished in {t_rf:.2f}s")

    res_rf = calculate_metrics_dict(
        y_true=y_true,
        y_pred=rf_pred,
        continuous_scores=rf_probs,
        model_name="Random Forest",
        dataset_name=dataset_name,
        threshold=rf_th,
    )
    results.append(res_rf)

    # -------------------------------------------------------------------------
    # 3. Dense Autoencoder
    # -------------------------------------------------------------------------
    logger.info(f"[3/5] Evaluating Dense Autoencoder on {dataset_name}...")
    ae_path = settings.MODELS_DIR / f"autoencoder_{dataset_name}_v1.0.0.pt"
    if not ae_path.exists():
        raise FileNotFoundError(f"Autoencoder artifact not found at {ae_path}")
    ae_model = AutoencoderDetector.load(ae_path)
    ae_th = float(getattr(ae_model, "reconstruction_threshold", 0.05))
    logger.info(f"  Autoencoder production threshold (raw MSE): {ae_th:.6f}")

    t0 = time.perf_counter()
    ae_errs = ae_model.compute_reconstruction_error(X_arr)
    ae_pred = (ae_errs >= ae_th).astype(int)
    t_ae = time.perf_counter() - t0
    logger.info(f"  Inference finished in {t_ae:.2f}s")

    res_ae = calculate_metrics_dict(
        y_true=y_true,
        y_pred=ae_pred,
        continuous_scores=ae_errs,
        model_name="Dense Autoencoder",
        dataset_name=dataset_name,
        threshold=ae_th,
    )
    results.append(res_ae)

    # -------------------------------------------------------------------------
    # 4. LSTM Autoencoder
    # -------------------------------------------------------------------------
    logger.info(f"[4/5] Evaluating LSTM Autoencoder on {dataset_name}...")
    lstm_path = settings.MODELS_DIR / f"lstm_autoencoder_{dataset_name}_v1.0.0.pt"
    if not lstm_path.exists():
        raise FileNotFoundError(f"LSTM Autoencoder artifact not found at {lstm_path}")
    lstm_model = LSTMAutoencoderDetector.load(lstm_path)
    lstm_th = float(getattr(lstm_model, "reconstruction_threshold", 0.05))
    seq_len = getattr(lstm_model, "seq_len", 10)
    logger.info(f"  LSTM Autoencoder production threshold (raw MSE): {lstm_th:.6f}, seq_len: {seq_len}")

    t0 = time.perf_counter()
    pad = np.repeat(X_arr[0:1], seq_len - 1, axis=0)
    padded_X = np.vstack([pad, X_arr])
    windows_3d = np.lib.stride_tricks.sliding_window_view(padded_X, (seq_len, X_arr.shape[1]))[:, 0, :, :]
    batch_sz = 1024
    err_chunks = []
    for b_start in range(0, len(windows_3d), batch_sz):
        b_win = windows_3d[b_start : b_start + batch_sz]
        err_chunks.append(lstm_model.compute_reconstruction_error(b_win))
    lstm_errs = np.concatenate(err_chunks)
    lstm_pred = (lstm_errs >= lstm_th).astype(int)
    t_lstm = time.perf_counter() - t0
    logger.info(f"  Inference finished in {t_lstm:.2f}s")

    res_lstm = calculate_metrics_dict(
        y_true=y_true,
        y_pred=lstm_pred,
        continuous_scores=lstm_errs,
        model_name="LSTM Autoencoder",
        dataset_name=dataset_name,
        threshold=lstm_th,
    )
    results.append(res_lstm)

    # -------------------------------------------------------------------------
    # 5. Ensemble Detector (4-Model Weighted Composite)
    # -------------------------------------------------------------------------
    logger.info(f"[5/5] Evaluating 4-Model Ensemble Detector on {dataset_name}...")
    ensemble = EnsembleDetector.load(dataset_name=dataset_name)
    ens_th = float(getattr(ensemble.risk_scorer, "decision_threshold", 50.0))
    logger.info(f"  Ensemble decision threshold: {ens_th}")

    t0 = time.perf_counter()
    ens_pred, ens_scores, _ = ensemble.predict_batch(X_test_df)
    t_ens = time.perf_counter() - t0
    logger.info(f"  Inference finished in {t_ens:.2f}s")

    # Verify predictions
    assert len(ens_pred) == n_samples, f"Ensemble pred length {len(ens_pred)} != {n_samples}"
    assert len(ens_scores) == n_samples, f"Ensemble scores length {len(ens_scores)} != {n_samples}"
    assert not np.isnan(ens_scores).any(), "NaN detected in ensemble risk scores"
    assert not np.isinf(ens_scores).any(), "Inf detected in ensemble risk scores"
    assert np.all((ens_scores >= 0.0) & (ens_scores <= 100.0)), "Risk scores out of [0, 100] bounds"

    res_ens = calculate_metrics_dict(
        y_true=y_true,
        y_pred=ens_pred,
        continuous_scores=ens_scores,
        model_name="Ensemble",
        dataset_name=dataset_name,
        threshold=ens_th,
    )
    results.append(res_ens)

    return results


def format_row(r: Dict[str, Any]) -> str:
    """Format single result dictionary as markdown table row."""
    roc_str = f"{r['roc_auc']:.4f}" if r['roc_auc'] is not None else "N/A"
    pr_str = f"{r['pr_auc']:.4f}" if r['pr_auc'] is not None else "N/A"
    return (
        f"| {r['dataset']:10s} | {r['model']:18s} | "
        f"{r['accuracy']:.4f} | {r['precision']:.4f} | {r['recall']:.4f} | "
        f"{r['f1']:.4f} | {roc_str:>7s} | {pr_str:>7s} | {r['fpr']:.4f} | "
        f"{r['tpr']:.4f} | {r['tn']:6d} | {r['fp']:6d} | {r['fn']:6d} | {r['tp']:6d} |"
    )


def main():
    logger.info("=" * 80)
    logger.info("STARTING COMPLETE NSL-KDD & CICIDS2017 TEST EVALUATION BENCHMARK")
    logger.info("=" * 80)

    all_results: List[Dict[str, Any]] = []

    # 1. NSL-KDD Evaluation
    nsl_results = evaluate_dataset("nsl_kdd")
    all_results.extend(nsl_results)

    # 2. CICIDS2017 Evaluation
    cic_results = evaluate_dataset("cicids2017")
    all_results.extend(cic_results)

    # 3. Print Complete Comparison Table
    print("\n" + "=" * 125)
    print("COMPLETE NSL-KDD & CICIDS2017 ZERO-DAY NIDS BENCHMARK RESULTS (HELD-OUT TEST SPLIT)")
    print("=" * 125)
    headers = [
        "Dataset", "Model", "Accuracy", "Precision", "Recall", "F1",
        "ROC-AUC", "PR-AUC", "FPR", "TPR", "TN", "FP", "FN", "TP"
    ]
    header_line = "| " + " | ".join(headers) + " |"
    sep_line = "| " + " | ".join(["---" if i < 2 else "---:" for i in range(len(headers))]) + " |"
    print(header_line)
    print(sep_line)
    for r in all_results:
        print(format_row(r))
    print("=" * 125 + "\n")

    # 4. Save Results to Disk
    eval_dirs = [
        root_dir / "ml_models" / "evaluation",
        settings.MODELS_DIR / "evaluation",
    ]
    for e_dir in eval_dirs:
        ensure_dir(e_dir)
        nsl_file = e_dir / "nsl_kdd_results.json"
        cic_file = e_dir / "cicids2017_results.json"
        csv_file = e_dir / "combined_results.csv"

        save_metadata({"dataset": "nsl_kdd", "results": nsl_results}, nsl_file)
        save_metadata({"dataset": "cicids2017", "results": cic_results}, cic_file)

        df_combined = pd.DataFrame(all_results)
        df_combined.to_csv(csv_file, index=False)
        logger.info(f"Saved evaluation artifacts to: {e_dir}")
        logger.info(f"  - {nsl_file}")
        logger.info(f"  - {cic_file}")
        logger.info(f"  - {csv_file}")

    print("Evaluation benchmark completed successfully.")


if __name__ == "__main__":
    main()
