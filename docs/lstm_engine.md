# Phase 6: Sequential LSTM Autoencoder Anomaly Detection Engine

## 1. Overview & Purpose
The **LSTM Autoencoder Anomaly Detection Engine** serves as the primary temporal/sequential deep learning detection component in the Zero-Day Attack Detection System. While point-based models (such as Isolation Forest and Dense Autoencoders) evaluate individual network packets or connection flows in isolation, the LSTM Autoencoder models temporal transitions across ordered sequences of events to detect subtle multi-stage attacks, scanning behavior, slow-and-low infiltration, and sequential protocol anomalies.

---

## 2. Sequence Construction & Windowing (`SequenceBuilder`)

### Sliding Sequence Windows
Preprocessed 2D tabular feature matrices are converted into 3D sequential tensors:
$$\mathbf{X} \in \mathbb{R}^{N \times D} \xrightarrow{\text{SequenceBuilder}} \mathbf{X}_{\text{seq}} \in \mathbb{R}^{M \times T \times D}$$
Where:
- $N$: Number of tabular records
- $D$: Number of selected preprocessed features (from Phase 3)
- $T$: Configurable sequence window length (`sequence_length`, default: 10)
- $M$: Resulting sequence count ($M = \lfloor (N - T) / \text{stride} \rfloor + 1$)
- $\text{stride}$: Step size between consecutive sliding windows (default: 1)

### Temporal Ordering & Boundary Protection
1. **Strict Temporal Isolation**: Sequence window generation occurs **independently after train/val/test splitting**. Sliding windows never cross split boundaries, preventing data leakage.
2. **Tabular Dataset Semantics**: Tabular intrusion datasets (NSL-KDD, CICIDS 2017, UNSW-NB15) represent connection records. Sequence windowing reflects the sequential order of recorded network flows. True physical timestamps are preserved when present in raw captures.
3. **Label Aggregation Rules**:
   - `any` (Default): A sequence is labeled an anomaly ($1$) if *any* flow in the window is an attack.
   - `last`: Label is assigned based on the terminal record of the sequence.
   - `majority`: Label is $1$ if $>50\%$ of records in the window are attacks.

---

## 3. Neural Network Architecture

The PyTorch LSTM Autoencoder employs an encoder-bottleneck-decoder sequential compression and reconstruction pipeline:

```
Input Sequence Window (Batch, T timesteps, D features)
       │
       ▼
LSTM Encoder Layer (hidden_size=encoder_units, num_layers=1, dropout=0.1)
       │
       ▼
Bottleneck Latent Projection (Linear: encoder_units -> latent_dim)
       │
       ▼
Latent Vector Z (Batch, latent_dim)
       │
       ▼
Repeat / Temporal Expansion (Expand Z across T timesteps -> Batch, T, latent_dim)
       │
       ▼
LSTM Decoder Layer (hidden_size=decoder_units, num_layers=1, dropout=0.1)
       │
       ▼
TimeDistributed Linear Layer (decoder_units -> D features per timestep)
       │
       ▼
Reconstructed Sequence Window (Batch, T timesteps, D features)
```

### Key Configuration Parameters:
- `input_dim` ($D$): Dynamically resolved from preprocessed features.
- `seq_len` ($T$): Sequence window length (Default: 10).
- `encoder_units`: Encoder LSTM hidden dimensions (Default: 64).
- `latent_dim`: Latent bottleneck representation (Default: 16).
- `decoder_units`: Decoder LSTM hidden dimensions (Default: 64).
- `num_layers`: Number of stacked LSTM layers (Default: 1).
- `dropout_rate`: Regularization rate (Default: 0.1).
- `learning_rate`: Adam optimizer learning rate (Default: 0.001).
- `early_stopping_patience`: Validation loss patience before early termination (Default: 8).

---

## 4. Training Strategy: Normal-Only Baseline

1. **Unsupervised Anomaly Detection Rationale**: Because zero-day attack sequences are unknown during model development, the LSTM Autoencoder is trained **exclusively on benign/normal sequence windows** ($y=0$).
2. **Manifold Learning**: The network optimizes parameters $\theta$ to minimize reconstruction error on normal sequence transitions:
   $$\mathcal{L}(\theta) = \frac{1}{M \times T \times D} \sum_{i=1}^{M} \sum_{t=1}^{T} \sum_{j=1}^{D} \left(S_{i, t, j} - \hat{S}_{i, t, j}\right)^2$$
3. **Hostile Sequences**: Abnormal traffic bursts, scan patterns, and novel exploit chains fail to conform to learned transition manifolds and yield elevated reconstruction error.

---

## 5. Sequence Reconstruction Error & Scoring

### Sequence Mean Squared Error (MSE)
For an input sequence $S \in \mathbb{R}^{T \times D}$ and reconstructed sequence $\hat{S} \in \mathbb{R}^{T \times D}$:
$$\text{MSE}(S, \hat{S}) = \frac{1}{T \times D} \sum_{t=1}^{T} \sum_{j=1}^{D} (S_{t, j} - \hat{S}_{t, j})^2$$

### Timestep Error Breakdown
Per-timestep error vectors $\mathbf{e} \in \mathbb{R}^T$ identify the specific point within the sliding window that triggered the anomaly:
$$e_t = \frac{1}{D} \sum_{j=1}^{D} (S_{t, j} - \hat{S}_{t, j})^2$$

### Normalized Anomaly Score ($0 - 100$)
$$\text{Anomaly Score} = \text{clip}\left(100.0 \times \frac{\text{MSE} - \text{MSE}_{\min}}{\text{MSE}_{\max} - \text{MSE}_{\min}}, 0.0, 100.0\right)$$

---

## 6. Threshold Selection Strategy
Decision thresholds are calibrated strictly on **normal validation sequence windows**:
$$\tau = \text{Percentile}(\text{MSE}_{\text{val\_normal\_seq}}, 95.0)$$
- If $\text{MSE}(S, \hat{S}) \ge \tau \implies \text{prediction} = \text{"anomaly"}\; (\text{is\_anomaly} = \text{True})$
- If $\text{MSE}(S, \hat{S}) < \tau \implies \text{prediction} = \text{"normal"}\; (\text{is\_anomaly} = \text{False})$

---

## 7. Model Artifacts & Registry Integration

- **Model Weights**: `ml_models/trained/lstm_autoencoder_<dataset>_v<version>.pt`
- **Model Metadata**: `ml_models/trained/lstm_autoencoder_<dataset>_v<version>_metadata.json`
- **Registry Integration**: Enrolled in `ml_models/model_registry.json` under `model_name="lstm_autoencoder"`.
- **Diagnostic Visualizations**:
  - `ml_models/experiments/plots/cm_lstm_<dataset>.png` (Sequence confusion matrix)
  - `ml_models/experiments/plots/roc_lstm_<dataset>.png` (Sequence ROC curve)
  - `ml_models/experiments/plots/recon_dist_lstm_<dataset>.png` (Reconstruction error distribution)
  - `ml_models/experiments/plots/loss_curve_lstm_<dataset>.png` (Training loss convergence)

---

## 8. Sequence-Level vs Record-Level Semantics

- **Sequence-Level Metrics**: Evaluates whether the sliding window containing $T$ events is anomalous as a collective group.
- **Traceability**: `SequenceWindow` metadata (`start_row_idx`, `end_row_idx`) and timestep error vectors $\mathbf{e}$ map sequence anomalies back to individual contributing event records.

---

## 9. Limitations & Zero-Day Proxy Considerations
1. **Zero-Day Proxy Scope**: Withheld attack categories simulate zero-day conditions but do not guarantee detection of arbitrary unseen exploit mechanisms.
2. **Computational Overhead**: Sequential windowing and recurrent updates require higher computational resources than stateless point detectors; batch inference and early stopping are enforced to optimize throughput.
3. **Dataset Ordering**: When true session IDs or timestamps are absent, sequence models rely on capture arrival order.
