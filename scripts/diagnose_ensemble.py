import sys
import traceback
from pathlib import Path
import numpy as np

from backend.app.ml.ensemble.ensemble_detector import EnsembleDetector
from backend.app.ml.registry.model_registry import model_registry

print("=== Model Registry Query ===")
for name in ["isolation_forest", "autoencoder", "lstm_autoencoder", "random_forest"]:
    meta = model_registry.get_model(name, dataset="synthetic")
    print(f"Registry for {name}: {meta is not None}")
    if meta:
        p = Path(meta.get("artifact_path", ""))
        print(f"  artifact_path: {p}")
        print(f"  exists: {p.exists()}")

print("\n=== Instantiating EnsembleDetector.load('synthetic') ===")
try:
    det = EnsembleDetector.load("synthetic")
    print("IF detector:", det.isolation_forest, "is_trained:", getattr(det.isolation_forest, 'is_trained', None))
    print("AE detector:", det.autoencoder, "is_trained:", getattr(det.autoencoder, 'is_trained', None))
    print("LSTM detector:", det.lstm_autoencoder, "is_trained:", getattr(det.lstm_autoencoder, 'is_trained', None))
    print("RF detector:", det.random_forest, "is_trained:", getattr(det.random_forest, 'is_trained', None))
    
    dummy_feat = np.zeros(26, dtype=np.float32)
    pred = det.predict_single(dummy_feat)
    print("\nPrediction successful!")
    print(f"Prediction: {pred.ensemble_prediction}, Risk Score: {pred.unified_risk_score}")
    for name, contrib in pred.model_contributions.items():
        print(f"  {name}: is_available={contrib.is_available}, score={contrib.normalized_score}, status={contrib.status_note}")
except Exception as e:
    print(f"ERROR: {e}")
    traceback.print_exc()
