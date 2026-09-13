# Phase 7: Random Forest Supervised Baseline

## 1. Overview & Architectural Role

The **Random Forest Supervised Baseline** provides a traditional, supervised machine learning reference point for the AI-Based Zero-Day Attack Detection System.

### Model Hierarchy in the Detection Engine:
1. **Isolation Forest** (Phase 4): Unsupervised point-based anomaly detector. Trained strictly on normal network flows ($y = 0$).
2. **Dense Autoencoder** (Phase 5): Reconstruction-based anomaly detector. Captures non-linear cross-feature relationships of normal baseline behavior.
3. **LSTM Autoencoder** (Phase 6): Sequential reconstruction anomaly detector. Learns temporal dependencies and multi-step attack patterns.
4. **Random Forest** (Phase 7): Supervised ensemble classifier. Trained with labeled normal ($y = 0$) and known attack ($y = 1$) data.

> **CRITICAL ARCHITECTURAL DISTINCTION**:
> Random Forest is included strictly as a **supervised benchmark/baseline** and **NOT** as a zero-day detector. Supervised models excel at recognizing previously seen attack signatures, but their decision boundaries are fundamentally bounded by known training distributions. They serve to demonstrate the performance degradation of supervised classifiers when encountering novel, unobserved attack classes (Zero-Day Proxy evaluation) versus unsupervised/reconstruction anomaly detectors.

---

## 2. Supervised vs. Anomaly Detection Paradigm

| Aspect | Isolation Forest / Autoencoders (Phases 4–6) | Random Forest (Phase 7 Baseline) |
|---|---|---|
| **Learning Paradigm** | Unsupervised / Semi-supervised Anomaly Detection | Supervised Binary Classification |
| **Training Labels Used** | Normal traffic only ($y = 0$) | Normal ($y = 0$) + Known Attacks ($y = 1$) |
| **Assumed Knowledge** | Only benign system/network state | Complete signature set of known attack classes |
| **Zero-Day Resilience** | Flags any significant deviation from normal profile | Struggles when zero-day attacks do not project onto known attack feature clusters |
| **Decision Boundary** | Encloses normal distribution | Discriminative hyperplane partitioning known classes |
| **Feature Attribution** | Reconstruction error / Isolation tree depth | Gini impurity decrease / Tree splitting variance |

---

## 3. Data Split & Zero-Day Proxy Evaluation

To rigorously compare supervised classifiers against anomaly detectors, two evaluation methodologies are supported:

### A. Standard Supervised Evaluation
- **Training Set**: $80\%$ normal flows + $80\%$ known attack flows.
- **Validation Set**: $10\%$ normal flows + $10\%$ known attack flows (used for hyperparameter validation and decision threshold optimization).
- **Test Set**: $10\%$ normal flows + $10\%$ known attack flows.

### B. Unseen Attack (Zero-Day Proxy) Evaluation
- **Training Set**: Normal flows + Subset of attack categories (e.g., `DoS`, `PortScan`).
- **Test Set**: Normal flows + Completely withheld attack categories (e.g., `Zero-Day Exploit`, `Infiltration`).
- **Objective**: Measure the false negative rate (FNR) and degradation of detection confidence when a supervised classifier encounters traffic patterns absent from its training distribution.

---

## 4. Binary Label Transformation

Network intrusion datasets (NSL-KDD, CIC-IDS-2017, UNSW-NB15) contain multi-class attack categories. For Phase 7:
- **Normal / Benign**: Explicitly mapped to `0` (`is_anomaly: false`).
- **Attack / Malicious**: Mapped to `1` (`is_anomaly: true`).
- Original attack subcategories (e.g., `neptune`, `smurf`, `PortScan`, `Generic`) are preserved in record metadata for granular post-classification breakdown.

---

## 5. Model Architecture & Hyperparameters

The `RandomForestClassifierModel` wraps Scikit-Learn's `RandomForestClassifier` with safety, scoring normalization, and metric extraction utilities.

### Configurable Hyperparameters (`app.core.config.Settings`):
- `RF_N_ESTIMATORS`: Number of decision trees in the forest (default: `100`).
- `RF_MAX_DEPTH`: Maximum depth of each tree (default: `None` / unbounded).
- `RF_MIN_SAMPLES_SPLIT`: Minimum samples required to split an internal node (default: `2`).
- `RF_MIN_SAMPLES_LEAF`: Minimum samples required at a leaf node (default: `1`).
- `RF_MAX_FEATURES`: Number of features to consider per split (`"sqrt"`).
- `RF_CLASS_WEIGHT`: Class weighting scheme (`"balanced"` for imbalanced intrusion datasets).
- `RF_THRESHOLD`: Attack probability decision threshold (default: `0.5`, auto-calibrated on validation split).
- `RF_RANDOM_SEED`: Random seed for deterministic reproducibility (default: `42`).
- `RF_N_JOBS`: Parallel CPU workers (default: `-1` for full multi-threading).

---

## 6. Threshold Calibration Strategy

To avoid test-set data leakage, the attack decision threshold is tuned exclusively on the **validation split**:

$$\text{Strategy: } \arg\max_{\tau \in [0.1, 0.9]} F_1(\tau; X_{\text{val}}, y_{\text{val}})$$

If the validation set has insufficient attack diversity, the default fallback threshold ($0.5$) is retained.

---

## 7. Prediction Schema & Normalized Scores

Each prediction conforms to the standardized system schema:

```json
{
  "model_name": "random_forest",
  "model_version": "1.0.0",
  "prediction": "attack",
  "is_anomaly": true,
  "raw_score": 0.88,
  "anomaly_score": 88.0,
  "confidence_score": 0.88,
  "processing_time_ms": 0.42,
  "metadata": {
    "class_probability_normal": 0.12,
    "class_probability_attack": 0.88,
    "decision_threshold": 0.5,
    "threshold_strategy": "f1_optimal_val_0.50"
  }
}
```

### Score Normalization & Confidence:
- **Attack Probability**: $P(\text{attack}) = \text{predict\_proba}(X)[:, 1]$
- **Anomaly Score** ($[0, 100]$): $\text{clip}(100.0 \times P(\text{attack}), 0.0, 100.0)$
- **Confidence Score**: $\max(P(\text{normal}), P(\text{attack})) \in [0.5, 1.0]$

---

## 8. Feature Importance (Gini Impurity)

The model extracts and ranks normalized Gini feature importances across all trees:
- Saved in model metadata JSON.
- Visualized as horizontal bar charts in `ml_models/experiments/plots/feature_importance_rf_<dataset>.png`.
- Serves as the foundation for future Explainable AI (XAI / SHAP) comparisons in Phase 10.

---

## 9. Model Registry & Service Integration

Random Forest is registered in `ml_models/model_registry.json` alongside `isolation_forest`, `autoencoder`, and `lstm_autoencoder`:

```python
from backend.app.ml.registry.model_registry import model_registry
from backend.app.ml.models.random_forest import RandomForestClassifierModel

# Discover registered model
rf_meta = model_registry.get_active_model("random_forest")

# Load model artifact
rf_model = RandomForestClassifierModel.load(rf_meta["artifact_path"])
```

Via `ModelManager`:
```python
from backend.app.ml.model_manager import model_manager

# ModelManager reports status of all 4 models:
status = model_manager.get_model_status()
# -> {'isolation_forest': True, 'autoencoder': True, 'lstm_autoencoder': True, 'random_forest': True}
```

---

## 10. CLI Usage

### Train Random Forest:
```powershell
backend\.venv\Scripts\python.exe scripts/train_random_forest.py --dataset synthetic --n-estimators 100 --class-weight balanced
```

### Evaluate Random Forest:
```powershell
backend\.venv\Scripts\python.exe scripts/evaluate_random_forest.py --dataset synthetic
```

Outputs:
- Metric summary (Accuracy, Balanced Accuracy, Precision, Recall, F1, ROC-AUC, PR-AUC, FPR, FNR, Specificity).
- Zero-day vs. known attack class breakdown.
- Diagnostic visualization plots in `ml_models/experiments/plots/`:
  - `cm_rf_<dataset>.png` (Confusion Matrix)
  - `roc_rf_<dataset>.png` (ROC Curve & AUC)
  - `pr_curve_rf_<dataset>.png` (Precision-Recall Curve & PR-AUC)
  - `feature_importance_rf_<dataset>.png` (Top Gini Feature Importances)
  - `score_dist_rf_<dataset>.png` (Predicted Probability Distributions)
- JSON experiment report in `ml_models/experiments/random_forest_<dataset>_evaluation.json`.
