# Phase 5: Deep Learning Autoencoder Anomaly Detection Engine

## 1. Overview & Purpose
The **Autoencoder Anomaly Detection Engine** serves as the primary deep learning unsupervised detection component in the Zero-Day Attack Detection System. Unlike supervised classifiers that require explicit attack signatures, the Autoencoder models the intrinsic manifold topology of **benign network traffic** and identifies zero-day anomalies by measuring reconstruction error (Mean Squared Error).

---

## 2. Neural Architecture

The dense Autoencoder employs a symmetric bottleneck compression and decompression architecture:

```
Input Features (D dimensions)
       │
       ▼
Dense Linear Layer + Activation (ReLU/LeakyReLU/GELU) + Dropout
       │
       ▼
Dense Linear Layer + Activation + Dropout
       │
       ▼
Bottleneck Latent Representation (Z dimensions, e.g., 8-16)
       │
       ▼
Dense Linear Layer + Activation + Dropout
       │
       ▼
Dense Linear Layer + Activation + Dropout
       │
       ▼
Reconstructed Output (D dimensions)
```

### Key Configuration Parameters:
- `input_dim`: Dynamic based on selected feature vector from Phase 3 preprocessing.
- `latent_dim`: Bottleneck latent representation dimension (Default: 8).
- `hidden_dims`: Encoder layer dimensions (Default: `[64, 32]`). Decoder symmetrically mirrors this structure (`[32, 64]`).
- `activation`: Non-linear activation (`relu`, `leaky_relu`, `elu`, `gelu`, `tanh`).
- `dropout_rate`: Regularization rate between dense layers.
- `optimizer`: Adam optimizer with configurable learning rate (Default: `0.001`).
- `early_stopping_patience`: Number of validation loss epochs without improvement before halting (Default: 10).

---

## 3. Training Strategy: Normal-Only Baseline

### Rationale
In real-world enterprise networks, zero-day attacks are by definition unseen and have no labeled signatures in historical training corpora. To detect novel attacks without prior knowledge:
1. The Autoencoder is trained **exclusively on benign/normal network traffic** ($y=0$).
2. The network learns to compress and faithfully reconstruct normal protocol patterns, packet sizes, flow durations, and statistical distributions.
3. When abnormal or hostile traffic ($y=1$) is presented during inference, the autoencoder fails to reconstruct the unfamiliar patterns, yielding a significantly higher reconstruction error (MSE).

---

## 4. Reconstruction Error & Anomaly Score Calibration

### Raw Reconstruction Error (MSE)
For an input vector $\mathbf{x} \in \mathbb{R}^D$ and reconstructed vector $\hat{\mathbf{x}} = f_{\text{decoder}}(f_{\text{encoder}}(\mathbf{x})) \in \mathbb{R}^D$:
$$\text{MSE}(\mathbf{x}, \hat{\mathbf{x}}) = \frac{1}{D} \sum_{j=1}^{D} (x_j - \hat{x}_j)^2$$

### Normalized Anomaly Score ($0 - 100$)
To maintain consistency across diverse detection models (such as Isolation Forest), raw MSE values are normalized onto a calibrated $[0, 100]$ score:
$$\text{Anomaly Score} = \text{clip}\left(100.0 \times \frac{\text{MSE} - \text{MSE}_{\min}}{\text{MSE}_{\max} - \text{MSE}_{\min}}, 0.0, 100.0\right)$$
*Note: The normalized score reflects relative anomalousness and is not a calibrated Bayesian posterior probability.*

---

## 5. Threshold Selection Strategy
To prevent data leakage, decision thresholds are determined strictly on **validation baseline data**:
- **Percentile Thresholding (Default)**: The threshold is set to the 95th percentile of reconstruction errors on benign validation samples:
  $$\tau = \text{Percentile}(\text{MSE}_{\text{val\_normal}}, 95.0)$$
- Samples with $\text{MSE} \ge \tau$ are classified as `anomaly` (`is_anomaly=True`), while samples with $\text{MSE} < \tau$ are classified as `normal` (`is_anomaly=False`).

---

## 6. Preprocessing Integration & Data Leakage Prevention
The Autoencoder directly ingests the transformed feature outputs produced by the Phase 3 `NetworkDataPipeline` (`scaler.joblib`, `encoder.joblib`, `feature_selector.joblib`).
- The model **never** refits scalers or encoders during training or inference.
- Feature names and ordering are frozen and strictly enforced at inference time.

---

## 7. Model Artifacts & Registry

Model weights and companion metadata are versioned and stored under `ml_models/trained/`:
- **Model Checkpoint**: `ml_models/trained/autoencoder_<dataset>_v<version>.pt` (PyTorch state dictionary and network architecture metadata).
- **Metadata Document**: `ml_models/trained/autoencoder_<dataset>_v<version>_metadata.json` (Hyperparameters, threshold metrics, MSE calibration bounds, dataset version, and preprocessing dependencies).
- **Registry Record**: `ml_models/model_registry.json`.

---

## 8. Unseen Zero-Day Proxy Evaluation Methodology
To benchmark zero-day anomaly detection capability without test set contamination:
- Distinct attack categories (e.g., U2R, R2L in NSL-KDD, Botnet in CICIDS 2017, Worms in UNSW-NB15) are withheld from training and validation splits.
- Evaluation calculates:
  1. Standard security metrics (Accuracy, Precision, Recall, F1, ROC-AUC, FPR, FNR).
  2. **Unseen Attack Category Detection Rate** (Zero-Day proxy performance).
  3. **Known Attack Category Detection Rate**.
  4. Diagnostic visual plots (Confusion Matrix, ROC Curve, Reconstruction Error Distribution, Loss Convergence Curve).

---

## 9. Limitations & Practical Considerations
1. **Zero-Day Proxy Limitation**: While withheld attack classes provide a rigorous empirical proxy, high performance on benchmark holdouts does not guarantee 100% detection of all possible real-world zero-day attack patterns.
2. **Benign Drift**: Significant shifts in network topology or software updates may increase false positive rates if benign traffic patterns drift from the training baseline.
3. **Point Anomalies vs Temporal Sequences**: Dense Autoencoders evaluate single flow records independently; temporal sequence patterns are handled in subsequent phases via LSTM temporal modeling.
