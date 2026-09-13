# ZeroDayAI - Detection Pipeline & Lifecycle Design

## Pipeline Flow

```
+--------------------------+
|  1. Network Traffic Data | (Raw PCAP / Synthetic Stream / Flow Logs)
+------------+-------------+
             |
+------------v-------------+
|  2. Data Preprocessing   | (Feature extraction, IP parsing, normalization)
+------------+-------------+
             |
+------------v-------------+
|  3. Feature Extraction   | (Scalar, statistical, and temporal window tensors)
+------------+-------------+
             |
+------------v-------------+
|  4. Multi-Model AI Engine|
|     - Isolation Forest   |
|     - Autoencoder (DL)   |
|     - LSTM Network       |
|     - Random Forest      |
+------------+-------------+
             |
+------------v-------------+
|  5. Consensus & Scoring  | (Ensemble weighting, risk score [0.0 - 1.0])
+------------+-------------+
             |
+------------v-------------+
|  6. Explainability Layer | (Feature attribution & rationale generation)
+------------+-------------+
             |
+------------v-------------+
|  7. Security Alerting    | (Threshold evaluation, event logging)
+------------+-------------+
             |
+------------v-------------+
|  8. Dashboard Analytics  | (Real-time telemetry, threat radar, metrics)
+--------------------------+
```

## Model Strategy for Zero-Day Attacks

Traditional intrusion detection systems rely on static signatures of known attacks.
Zero-day attacks are novel exploits with no preexisting signature.

The ZeroDayAI pipeline leverages:
1. **Unsupervised Anomaly Modeling**:
   - Training on baseline normal network behavior.
   - Any significant statistical divergence is flagged as potential zero-day activity.
2. **Multi-Model Consensus**:
   - Reduces false positives by combining tree-based partitioning (Isolation Forest), structural reconstruction failure (Autoencoder), and sequence temporal dynamics (LSTM).
3. **Transparent Explainability**:
   - Flags exactly which packet metrics (e.g. abnormal byte ratio, burst rate, unexpected port combination) triggered the anomaly flag.
