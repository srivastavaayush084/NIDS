# ZeroDayAI - Architectural Overview & System Design

## 1. System Architecture

The ZeroDayAI platform is engineered as a modular, decoupled cybersecurity intelligence system designed for early-stage zero-day network anomaly detection and explainable risk scoring.

```
+-------------------------------------------------------------+
|                      React Web Dashboard                     |
| (Real-time Flow Monitor, Threat Map, Model Analytics, Alerts)|
+------------------------------+------------------------------+
                               | REST APIs / WebSockets
+------------------------------v------------------------------+
|                     FastAPI Backend Layer                   |
|     (CORS, Router, Dependency Injection, Validation)        |
+------+-----------------------+-----------------------+------+
       |                       |                       |
+------v------+         +------v------+         +------v------+
| Detection   |         | Alert       |         | Model       |
| Service     |         | Service     |         | Service     |
+------+------+         +------+------+         +------+------+
       |                       |                       |
+------v-----------------------v------+         +------v------+
|       Detection Engine Pipeline      |         | Model       |
|  - Preprocessing & Scaling           |         | Registry    |
|  - Multi-Model Inference Consensus   |         +------+------+
|  - Risk Scorer & Anomaly Classifier  |                |
|  - Feature Attribution & Explainer   |         +------v------+
+------+-------------------------------+         | Artifacts   |
       |                                         | Storage     |
+------v-------------------------------+         +-------------+
|    Asynchronous MongoDB Storage      |
|  (Flows, Alerts, Model Metadata)     |
+--------------------------------------+
```

---

## 2. Multi-Model AI Detection Ensemble

The platform incorporates 4 specialized models:

1. **Isolation Forest (`isolation_forest.py`)**:
   - **Paradigm**: Unsupervised Tree Ensemble
   - **Role**: Detects isolated network data points and rare zero-day feature anomalies without requiring labeled attack classes.

2. **Deep Autoencoder (`autoencoder.py`)**:
   - **Paradigm**: Unsupervised Deep Reconstruction Neural Network
   - **Role**: Learns the compressed latent manifold of benign network traffic. Novel zero-day patterns exhibit high reconstruction error.

3. **LSTM Recurrent Network (`lstm_detector.py`)**:
   - **Paradigm**: Sequential / Temporal Recurrent Network
   - **Role**: Detects temporal anomalies, slow reconnaissance scanning, and multi-stage lateral movements across sliding time windows.

4. **Random Forest (`baseline_rf.py`)**:
   - **Paradigm**: Supervised Benchmark Classifier
   - **Role**: Serves as the comparison baseline to evaluate detection of known signatures vs. novel zero-day attacks.

---

## 3. Directory Layout

- **`backend/`**: Python FastAPI service with `.venv` isolated environment.
- **`frontend/`**: React + Vite modular dashboard application.
- **`data/`**: Storage for raw, processed, and sample packet datasets.
- **`ml_models/`**: Serialized model weights, scalers, and experiment records.
- **`docs/`**: Architecture and API documentation.
- **`scripts/`**: Convenience startup and environment setup scripts.
