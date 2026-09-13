# Explainable AI (XAI) Architecture & Operational Guide

## 1. Overview & Core Philosophy

In zero-day attack detection, machine learning models frequently make mission-critical security decisions based on complex, non-linear relationships across high-dimensional network flow spaces. An unexplainable "black box" prediction impedes security analyst triage, undermines trust, and delays incident response.

The **Phase 10 Explainable AI (XAI) Layer** provides practical, rigorous, model-appropriate explanations for:
1. **Supervised Random Forest baseline predictions** (via exact additive SHAP values).
2. **Unsupervised Isolation Forest anomaly isolations** (via controlled feature perturbation sensitivity).
3. **Dense Autoencoder topological anomalies** (via per-feature squared reconstruction errors $(x_j - \hat{x}_j)^2$).
4. **LSTM Autoencoder temporal sequence anomalies** (via hierarchical timestep and feature reconstruction error decomposition).
5. **Unified Ensemble risk scoring decisions** (via weighted model risk contributions, consensus analysis, and safe cross-model feature attribution fusion).

> [!IMPORTANT]
> **Fundamental Non-Causality Principle**:
> Explainability mathematically articulates *why a specific model or ensemble produced a particular numerical output or classification given its learned representations*. It **does not prove** that a specific network attribute physically caused the underlying security event or cyber incident in the real world.

---

## 2. Architecture & File Structure

The XAI subsystem resides in `backend/app/ml/explainability/` with dedicated explainer modules decoupled from API routes and presentation layers:

```
backend/app/ml/explainability/
├── __init__.py                     # Package exports
├── schemas.py                      # Standardized Pydantic XAI schemas
├── base_explainer.py               # Abstract base explainer interface with latency tracking
├── feature_attribution.py          # Preprocessing-aware feature mapping & dynamic summaries
├── random_forest_explainer.py      # SHAP TreeExplainer implementation
├── isolation_forest_explainer.py   # Perturbation sensitivity explainer
├── autoencoder_explainer.py        # Per-feature reconstruction error explainer
├── lstm_explainer.py               # Hierarchical timestep & feature reconstruction explainer
└── ensemble_explainer.py           # Multi-model risk contribution & fused feature explainer

backend/app/services/
└── explainer_service.py            # Decoupled service layer for sync/async on-demand XAI

scripts/
└── explain_prediction.py           # Unified CLI interface for sample/batch explanations
```

---

## 3. Model-Appropriate Explanation Methodologies

### 3.1 Random Forest (SHAP TreeExplainer)
- **Method Name**: `shap_tree`
- **Mathematics**: Computes Shapley values using `shap.TreeExplainer(model.model)` based on game-theoretic conditional expectations:
  $$\hat{y}(x) = \phi_0 + \sum_{j=1}^D \phi_j(x)$$
  where $\phi_0$ is the base expected model output and $\phi_j(x)$ is the SHAP attribution of feature $j$.
- **Contribution Direction**:
  - $\phi_j(x) > 0 \implies$ `increases_risk` (pushes probability toward attack class).
  - $\phi_j(x) < 0 \implies$ `decreases_risk` (pushes probability toward benign/normal class).
- **Ranking**: Features ranked by $|\phi_j(x)|$ descending.

### 3.2 Isolation Forest (Feature Perturbation Sensitivity)
- **Method Name**: `isolation_forest_perturbation`
- **Methodology**: Isolation Forest splits space randomly; applying native tree SHAP would produce misleading pseudo-causal values. We evaluate sensitivity by measuring the shift in application anomaly score when resetting feature $j$ to a benign reference baseline $x_{\text{base}}$:
  $$\Delta S_j = S(x) - S(x^{(j \leftarrow x_{\text{base}, j})})$$
- **Contribution Direction**:
  - $\Delta S_j > 0 \implies$ `increases_risk` (resetting feature $j$ to baseline makes the score more normal, meaning feature $j$ was isolating the sample).
  - $\Delta S_j < 0 \implies$ `decreases_risk` (resetting feature $j$ increases anomaly score, meaning feature $j$ was anchoring the sample in benign space).

### 3.3 Dense Autoencoder (Feature Reconstruction Error)
- **Method Name**: `autoencoder_reconstruction_error`
- **Mathematics**: Measures the elementwise squared error between original input vector $x$ and reconstructed output $\hat{x} = \text{Decoder}(\text{Encoder}(x))$:
  $$e_j = (x_j - \hat{x}_j)^2, \quad \text{MSE}(x) = \frac{1}{D} \sum_{j=1}^D e_j$$
- **Relative Share & Contribution**:
  $$c_j = e_j - \bar{e}, \quad \text{where } \bar{e} = \frac{1}{D} \sum_{k=1}^D e_k$$
- **Interpretation**: Features with high residual error indicate that their observed combination falls outside the normal topological manifold learned during benign training.

### 3.4 LSTM Autoencoder (Hierarchical Temporal Decomposition)
- **Method Name**: `lstm_hierarchical_reconstruction`
- **Mathematics**: For a sliding sequence window $S \in \mathbb{R}^{T \times D}$ and reconstructed sequence $\hat{S} \in \mathbb{R}^{T \times D}$:
  1. **Timestep Anomaly Decomposition**:
     $$E_t = \frac{1}{D} \sum_{j=1}^D (S_{t, j} - \hat{S}_{t, j})^2, \quad R_t = \frac{E_t}{\sum_{k=0}^{T-1} E_k + \epsilon}$$
     Identifies the peak anomalous timestep $t^* = \arg\max_t E_t$ in the sequence.
  2. **Feature Anomaly Decomposition**:
     $$F_j = \frac{1}{T} \sum_{t=0}^{T-1} (S_{t, j} - \hat{S}_{t, j})^2$$
     Identifies which network features suffered the greatest temporal distortion across the sequence window.

### 3.5 Unified Ensemble Engine (Multi-Model Risk Attribution)
- **Method Name**: `ensemble_risk_attribution`
- **Mathematics**: The composite risk score $R_{\text{ens}} \in [0.0, 100.0]$ is calculated as:
  $$R_{\text{ens}} = \sum_{m \in M_{\text{avail}}} w_m' \cdot S_m$$
  where $w_m'$ is the renormalized effective weight ($\sum w_m' = 1.0$) and $S_m \in [0.0, 100.0]$ is model $m$'s normalized risk score.
- **Ensemble Explanation Fields**:
  - Per-model weighted contribution: $w_m' \cdot S_m$.
  - Model availability & error diagnostics.
  - Model consensus agreement ratio: $\frac{\max(N_{\text{anom}}, N_{\text{norm}})}{N_{\text{avail}}}$.
  - Fused feature attribution: $\sum_{m} w_m' \cdot \tilde{c}_m(j)$, alongside separate per-model feature breakdowns.

---

## 4. Preprocessing-Aware Feature Preservation

Explanations never display opaque array indices (e.g. `feature_17`). The pipeline preserves metadata connecting:

$$\text{Raw Domain Attribute} \longrightarrow \text{Engineered / Transformed Metric} \longrightarrow \text{Model Input Column}$$

When one-hot encoding expands categorical features (e.g. `service` $\rightarrow$ `service_http`, `service_smtp`), the explicit transformed feature name is preserved alongside reference to its raw parent attribute.

---

## 5. Standardized Explanation Schema (`ModelExplanation` & `EnsembleExplanation`)

```json
{
  "explanation_id": "ens-exp-1788853347624",
  "model_name": "ensemble",
  "model_version": "1.0.0",
  "dataset_name": "synthetic",
  "prediction": "attack",
  "is_anomaly": true,
  "risk_score": 53.92,
  "severity": "HIGH",
  "decision_threshold": 50.0,
  "reliability_score": 1.0,
  "model_contributions": {
    "isolation_forest": {
      "is_available": true,
      "prediction": "attack",
      "normalized_risk_score": 100.0,
      "effective_weight": 0.25,
      "weighted_contribution": 25.0,
      "latency_ms": 44.23
    },
    "autoencoder": {
      "is_available": true,
      "prediction": "normal",
      "normalized_risk_score": 19.9,
      "effective_weight": 0.25,
      "weighted_contribution": 4.97,
      "latency_ms": 3.95
    },
    "lstm_autoencoder": {
      "is_available": true,
      "prediction": "normal",
      "normalized_risk_score": 33.5,
      "effective_weight": 0.25,
      "weighted_contribution": 8.39,
      "latency_ms": 13.62
    },
    "random_forest": {
      "is_available": true,
      "prediction": "attack",
      "normalized_risk_score": 62.2,
      "effective_weight": 0.25,
      "weighted_contribution": 15.56,
      "latency_ms": 69.33
    }
  },
  "agreement": {
    "models_total": 4,
    "models_available": 4,
    "models_anomalous": 2,
    "models_normal": 2,
    "agreement_ratio": 0.5,
    "consensus_prediction": "attack"
  },
  "fused_feature_contributions": [
    {
      "feature_name": "service_http",
      "contribution": 0.7500,
      "direction": "increases_risk",
      "absolute_contribution": 0.7500,
      "rank": 1
    },
    {
      "feature_name": "dst_host_srv_count",
      "contribution": 0.3253,
      "direction": "increases_risk",
      "absolute_contribution": 0.3253,
      "rank": 2
    }
  ],
  "summary": "The ensemble classified this network event as HIGH risk (score: 53.9/100.0) because detection engines (isolation_forest, random_forest) flagged anomalous behavior. Elevated risk was primarily driven by prominent network metrics: service_http, dst_host_srv_count. Ensemble consensus agreement ratio is 50.0%.",
  "limitations": [
    "Ensemble explanations reflect the weighted combination of participating models and consensus metrics.",
    "Explainability describes model internal behavior and feature sensitivities; it does not constitute physical proof of real-world cyber attack causality."
  ],
  "total_latency_ms": 737.74
}
```

---

## 6. Performance & On-Demand Execution Strategy

XAI computation is decoupled from high-throughput line-rate packet ingestion:
1. **On-Demand Generation**: Explanations are calculated when an alert is escalated, when requested by a SOC analyst via CLI/API, or for high-severity detections.
2. **Configurable Depth**: Supports `top_k = 5, 10, 20` to control compute and payload size.
3. **Explainer Caching**: Initialized explainers (including SHAP TreeExplainer trees and pre-allocated network graphs) are cached in `ExplainerService` across requests.
4. **Latency Measurement**: Every explanation isolates `prediction_latency_ms` from `explanation_latency_ms` and `total_latency_ms`.

---

## 7. Command Line Interface (CLI)

Use `scripts/explain_prediction.py` to inspect and explain any model or ensemble output:

```powershell
# Explain Random Forest via SHAP
backend\.venv\Scripts\python.exe scripts/explain_prediction.py --model random_forest --dataset synthetic --sample-index 0 --top-k 5 --save-plot

# Explain Isolation Forest via Perturbation Sensitivity
backend\.venv\Scripts\python.exe scripts/explain_prediction.py --model isolation_forest --dataset synthetic --sample-index 0 --top-k 5 --save-plot

# Explain Autoencoder via Reconstruction Error
backend\.venv\Scripts\python.exe scripts/explain_prediction.py --model autoencoder --dataset synthetic --sample-index 0 --top-k 5 --save-plot

# Explain LSTM Autoencoder via Timestep & Feature Decomposition
backend\.venv\Scripts\python.exe scripts/explain_prediction.py --model lstm_autoencoder --dataset synthetic --sample-index 0 --top-k 5 --save-plot

# Explain Unified Ensemble Risk Breakdown & Fused Attribution
backend\.venv\Scripts\python.exe scripts/explain_prediction.py --model ensemble --dataset synthetic --sample-index 0 --top-k 5 --save-plot
```

Generated visualization artifacts are saved automatically to `experiments/explainability/`.
