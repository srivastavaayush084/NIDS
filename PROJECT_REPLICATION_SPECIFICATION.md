# ZeroDayAI — Comprehensive Master System Specification & Replication Blueprint
**Target Audience:** Autonomous AI Coding Agents, Software Architects, and Lead Security Engineers  
**Goal:** Build, train, test, and deploy the exact ZeroDayAI multi-model Network Intrusion Detection System (NIDS) & SOC platform from scratch with 100% architectural and algorithmic parity.

---

## 1. System Vision & Problem Formulation

### 1.1 The Zero-Day Challenge in Modern NIDS
Traditional signature-based Network Intrusion Detection Systems (e.g., Snort, Suricata, legacy firewalls) match incoming packets against known attack signatures (CVE patterns, known malicious payload hashes, rigid port rules). When novel "zero-day" exploits or polymorphic attack variants emerge, signatures do not exist, leading to 0% detection of unknown attacks until signatures are manually reverse-engineered and deployed.

### 1.2 The ZeroDayAI Hybrid Multi-Model Solution
ZeroDayAI addresses this fundamental limitation through a **hybrid multi-model AI ensemble** combining:
1. **Unsupervised Anomaly Detection (Isolation Forest)**: Isolates rare multidimensional feature outliers without requiring attack labels.
2. **Deep Latent Space Reconstruction (PyTorch Dense Autoencoder)**: Compresses normal network baseline traffic into a low-dimensional manifold; unseen zero-day attacks fail to reconstruct, exhibiting high Mean Squared Error (MSE).
3. **Temporal Sequential Modeling (PyTorch LSTM Autoencoder)**: Captures sequential dependencies across sliding time windows of network flows to detect multi-stage zero-day attacks, slow reconnaissance port scans, and command-and-control beacons.
4. **Supervised Baseline Classifier (Random Forest)**: Accurately classifies known attack signatures (e.g., DoS, Probe, R2L, U2R) while serving as the benchmark comparator.
5. **Weighted Consensus Fusion & Dynamic Risk Scoring Engine**: Renormalizes individual continuous detector outputs into a normalized 0.0–100.0 Threat Risk Score, categorized into actionable operational severity tiers (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
6. **Explainable AI (XAI)**: Generates feature-level attribution explaining *why* an alert fired (via SHAP and reconstruction error delta attribution).
7. **Production Alert Lifecycle Engine**: Dynamic fingerprinting and cooldown deduplication to prevent SOC alert fatigue.
8. **React 19 Security Operations Center (SOC) Dashboard**: Glassmorphic dark-theme monitoring station with live packet capture, PCAP replay, interactive alert triage, model registry comparisons, and system health diagnostics.

---

## 2. Global Technology Stack & Environment Requirements

### 2.1 Backend Environment
- **Runtime:** Python 3.11+ / Python 3.14 compatible
- **API Framework:** FastAPI 0.115.x + Uvicorn (ASGI server with `--reload` in dev)
- **Deep Learning Framework:** PyTorch 2.14+ (CPU and CUDA compatible)
- **Machine Learning & Preprocessing:** Scikit-Learn 1.5+, NumPy 2.0+, Pandas 2.2+, Joblib 1.4+
- **Database Driver:** Motor 3.5+ (AsyncIO MongoDB driver) & PyMongo 4.8+
- **Packet Ingestion & Analysis:** Scapy 2.5+ (with Npcap driver on Windows / libpcap on Linux)
- **Security & Authentication:** PyJWT 2.8+ (HS256), Passlib/Bcrypt 4.0+ (Salted password hashing), Pydantic v2 Settings
- **Testing Engine:** Pytest 8.3+, Pytest-AsyncIO 0.24+, HTTPX 0.27+

### 2.2 Frontend Environment
- **Runtime & Tooling:** Node.js 20+, Vite 8.x
- **Framework:** React 19 (Single Page Application)
- **Iconography:** Lucide React
- **Styling Paradigm:** Custom Vanilla CSS Design System with Dark-Mode Tokens, Glassmorphism, and responsive CSS Grid/Flexbox (no external Tailwind dependency)
- **Testing Engine:** Vitest 5.0+

### 2.3 Database
- **Engine:** MongoDB 7.0+ (Standalone, Replica Set, or MongoDB Atlas Cloud)

---

## 3. High-Level Architecture & End-to-End Data Pipeline

```
                               ┌─────────────────────────────────────────┐
                               │   Raw Network Traffic Ingestion Source  │
                               │  (Live Scapy Sniffing / PCAP File Replay│
                               └────────────────────┬────────────────────┘
                                                    │ Raw Packets
                                                    ▼
                               ┌─────────────────────────────────────────┐
                               │       Scapy Packet Dissection           │
                               │  (Ethernet, IP, IPv6, TCP, UDP, ICMP)   │
                               └────────────────────┬────────────────────┘
                                                    │ Parsed Packets
                                                    ▼
                               ┌─────────────────────────────────────────┐
                               │  Bidirectional 5-Tuple Flow Aggregator  │
                               │ (src_ip, dst_ip, src_port, dst_port,    │
                               │  protocol, TCP state flags, windowing)  │
                               └────────────────────┬────────────────────┘
                                                    │ Completed Flows
                                                    ▼
                               ┌─────────────────────────────────────────┐
                               │    42-Metric Flow Feature Extractor     │
                               │ (duration, byte/pkt ratios, rates, etc.)│
                               └────────────────────┬────────────────────┘
                                                    │ Flow Features
                                                    ▼
                               ┌─────────────────────────────────────────┐
                               │   Preprocessing & Mapping Pipeline      │
                               │ (RobustScaler / StandardScaler / OneHot)│
                               └────────────────────┬────────────────────┘
                                                    │ Normalized Vector (26/41 dims)
                     ┌──────────────────────────────┼──────────────────────────────┐
                     │                              │                              │
                     ▼                              ▼                              ▼
          ┌──────────────────────┐       ┌──────────────────────┐       ┌──────────────────────┐
          │   Isolation Forest   │       │   Dense Autoencoder  │       │   LSTM Autoencoder   │
          │ (Unsupervised Trees) │       │ (Reconstruction MSE) │       │ (Sequential Sliding) │
          └──────────┬───────────┘       └──────────┬───────────┘       └──────────┬───────────┘
                     │                              │                              │
                     └──────────────────────────────┼──────────────────────────────┘
                                                    │
                                                    ▼
                               ┌─────────────────────────────────────────┐
                               │   Supervised Baseline (Random Forest)   │
                               │       (Known Attack Probabilities)      │
                               └────────────────────┬────────────────────┘
                                                    │ Individual Model Scores
                                                    ▼
                               ┌─────────────────────────────────────────┐
                               │   Ensemble Weighted Risk Scorer         │
                               │  - Continuous Normalization (0 - 100)   │
                               │  - Dynamic Weight Renormalization       │
                               │  - Model Consensus & Agreement Voting   │
                               │  - Severity Classification (4 Tiers)    │
                               └────────────────────┬────────────────────┘
                                                    │ Threat Level & Decision
                                                    ▼
                               ┌─────────────────────────────────────────┐
                               │      Explainable AI (XAI) Engine        │
                               │ (SHAP Attribution + Error Delta Vectors)│
                               └────────────────────┬────────────────────┘
                                                    │ Top Features + Risk Score
                                                    ▼
                               ┌─────────────────────────────────────────┐
                               │      Security Alert Lifecycle Engine    │
                               │  - Threshold & Rule Validation          │
                               │  - SHA-256 Fingerprint Deduplication    │
                               │  - 300s Cooldown Window Management      │
                               └────────────────────┬────────────────────┘
                                                    │ Alerts & Detections
                     ┌──────────────────────────────┴──────────────────────────────┐
                     │                                                             │
                     ▼                                                             ▼
       ┌───────────────────────────┐                                 ┌───────────────────────────┐
       │   Asynchronous MongoDB    │                                 │   FastAPI REST Layer      │
       │ (users, logs, detections, │                                 │ (RBAC, Rate Limits, Auth) │
       │  alerts, events, audits)  │                                 └─────────────┬─────────────┘
       └───────────────────────────┘                                               │
                                                                                   ▼
                                                                     ┌───────────────────────────┐
                                                                     │   React 19 SOC Dashboard  │
                                                                     │ (Real-time Triage & Feed) │
                                                                     └───────────────────────────┘
```

---

## 4. Machine Learning Models & Mathematics

### 4.1 Model 1: Isolation Forest (`IsolationForestDetector`)
- **Objective:** Unsupervised isolation of anomalous network flow vectors without training on attack labels.
- **Mathematical Principle:** Anomalies are "few and different", meaning they require significantly fewer tree splits (shorter path lengths $h(x)$) to isolate in randomized decision trees.
- **Anomaly Score Formulation:**
  $$s(x, n) = 2^{-\frac{E(h(x))}{c(n)}}$$
  where $c(n) = 2 \ln(n - 1) + 0.5772156649 - \frac{2(n - 1)}{n}$ is the average path length of unsuccessful searches in a Binary Search Tree (BST).
- **Hyperparameters:**
  - `n_estimators`: 100
  - `contamination`: 0.05
  - `max_samples`: "auto" (min(256, n_samples))
  - `random_state`: 42
- **Score Normalization:** Raw scores $\in [-0.5, 0.5]$ are mapped to a continuous $[0.0, 100.0]$ scale using min-max threshold scaling:
  $$\text{Score}_{\text{norm}} = \text{clip}\left( \frac{\text{raw} - \text{min}}{\text{max} - \text{min}} \times 100.0, 0.0, 100.0 \right)$$

### 4.2 Model 2: PyTorch Dense Autoencoder (`AutoencoderDetector`)
- **Objective:** Unsupervised deep latent reconstruction. Trained exclusively on benign network baseline flows.
- **Network Architecture:**
  - **Encoder:** Input Dimension $\to$ Linear(64) $\to$ BatchNorm1d $\to$ LeakyReLU(0.2) $\to$ Dropout(0.1) $\to$ Linear(32) $\to$ LeakyReLU(0.2) $\to$ Linear(Latent=8)
  - **Decoder:** Linear(Latent=8) $\to$ LeakyReLU(0.2) $\to$ Linear(32) $\to$ LeakyReLU(0.2) $\to$ Linear(64) $\to$ LeakyReLU(0.2) $\to$ Linear(Input Dimension)
- **Loss Function:** Mean Squared Error (MSE) across all feature dimensions:
  $$\mathcal{L}_{\text{MSE}}(x, \hat{x}) = \frac{1}{D} \sum_{j=1}^{D} (x_j - \hat{x}_j)^2$$
- **Anomaly Scoring & Thresholding:**
  - Baseline validation error distribution is recorded.
  - Anomaly threshold $\theta_{\text{AE}}$ is set to the 95th percentile of normal validation errors.
  - Continuous score:
    $$\text{Score} = \text{clip}\left( \frac{\text{MSE}}{\theta_{\text{AE}}} \times 50.0, 0.0, 100.0 \right)$$
    (An error exactly at threshold maps to 50.0).
- **Training Hyperparameters:**
  - Optimizer: Adam (`lr=0.001`, `weight_decay=1e-5`)
  - Batch Size: 64, Epochs: 50
  - Early Stopping: Patience = 10 epochs on validation loss.

### 4.3 Model 3: PyTorch LSTM Autoencoder (`LSTMAutoencoderDetector`)
- **Objective:** Sequential temporal anomaly detection. Detects reconnaissance scans, brute-force bursts, and slow data exfiltration spanning across consecutive time intervals.
- **Sequence Formation:** Sliding window sequence buffer with `window_size = 10`, `stride = 1`. Input shape: `(batch_size, 10, feature_dim)`.
- **Network Architecture:**
  - **Encoder:** `nn.LSTM(input_size=D, hidden_size=64, num_layers=1, batch_first=True, dropout=0.1)` $\to$ Latent representation = last hidden state $h_T$ projected via `Linear(64, 16)`.
  - **Decoder:** Project latent back to `Linear(16, 64)` $\to$ Repeat vector 10 times $\to$ `nn.LSTM(hidden_size=64, num_layers=1, batch_first=True)` $\to$ `Linear(64, D)`.
- **Sequence Reconstruction Loss:**
  $$\mathcal{L}_{\text{Seq}}(X, \hat{X}) = \frac{1}{T \times D} \sum_{t=1}^{T} \sum_{j=1}^{D} (X_{t,j} - \hat{X}_{t,j})^2$$
- **Threshold & Normalization:** Threshold set at 95th percentile of validation sequence errors. Scaled to $[0.0, 100.0]$.

### 4.4 Model 4: Supervised Random Forest Baseline (`RandomForestClassifierModel`)
- **Objective:** Benchmark classifier for known attack patterns and probability calibration.
- **Architecture:** `RandomForestClassifier(n_estimators=100, criterion="gini", max_features="sqrt", class_weight="balanced", random_state=42, n_jobs=-1)`
- **Score Formulation:** Output probability of attack:
  $$\text{Score}_{\text{RF}} = P(y = \text{Attack} \mid x) \times 100.0$$

### 4.5 Model 5: Ensemble Weighted Consensus Engine (`EnsembleRiskScorer`)
- **Model Weights Configuration:**
  - Isolation Forest: $w_1 = 0.25$
  - Dense Autoencoder: $w_2 = 0.25$
  - LSTM Autoencoder: $w_3 = 0.25$
  - Random Forest: $w_4 = 0.25$
- **Dynamic Weight Renormalization:**
  If any model $k$ is unavailable or fails (e.g. sequence buffer not filled yet for LSTM):
  $$w_i^{\text{renorm}} = \frac{w_i}{\sum_{j \in \text{Available}} w_j}$$
- **Composite Risk Score Calculation:**
  $$\text{RiskScore} = \sum_{i \in \text{Available}} w_i^{\text{renorm}} \times \text{Score}_i$$
- **Decision Threshold:** If $\text{RiskScore} \ge 50.0$, the flow is flagged as an `ANOMALY`.
- **Severity Classification Mapping:**
  - `LOW`: $0.0 \le \text{RiskScore} \le 24.99$ (Emerald Green `#10B981`)
  - `MEDIUM`: $25.0 \le \text{RiskScore} \le 49.99$ (Amber `#F59E0B`)
  - `HIGH`: $50.0 \le \text{RiskScore} \le 74.99$ (Orange `#F97316`)
  - `CRITICAL`: $75.0 \le \text{RiskScore} \le 100.0$ (Crimson Red `#EF4444`)
- **Model Agreement Metric:**
  $$\text{Agreement} = \frac{\max(\text{Votes}_{\text{Anomaly}}, \text{Votes}_{\text{Normal}})}{N_{\text{models}}} \times 100\%$$

---

## 5. Explainable AI (XAI) Subsystem

Security analysts cannot act on black-box alerts. ZeroDayAI integrates dual XAI attribution:
1. **Tree Attribution (SHAP / TreeSensitivity):**
   - For Random Forest and Isolation Forest, calculates feature Shapley values $\phi_j(x)$ representing the marginal contribution of each feature to the divergence from the baseline.
   - Fallback engine computes feature-path sensitivity deltas if SHAP library is not present.
2. **Reconstruction Error Delta Attribution (Autoencoders):**
   - For Dense Autoencoder and LSTM Autoencoder, calculates the exact per-feature squared error:
     $$\Delta_j = (x_j - \hat{x}_j)^2$$
   - Features with the highest reconstruction error indicate the precise network anomaly characteristics (e.g. abnormally high `dst_bytes`, unusual `serror_rate`, unexpected port).
3. **Unified Output Schema:**
   Top-K (default 10) feature attributions are returned with:
   - `feature_name`: Exact metric name.
   - `attribution_score`: Normalized contribution percentage (0.0 to 1.0).
   - `observed_value`: Feature value extracted from the live flow.
   - `description`: Human-readable explanation of why this feature is abnormal.

---

## 6. Real-Time Network Monitoring & Flow Aggregation

### 6.1 Scapy Live Sniffer (`LivePacketSniffer`)
- Utilizes Scapy `AsyncSniffer` running in a dedicated background daemon thread.
- Dynamically enumerates available host adapters (Wi-Fi, Ethernet, Loopback) using `scapy.all.ifaces` and selects the adapter with a valid non-loopback IP address.
- Supports Berkeley Packet Filters (BPF), e.g. `"tcp or udp"`.

### 6.2 Bidirectional 5-Tuple Flow Aggregator (`FlowAggregator`)
Network packets are atomic; intrusions occur in **flows**. The aggregator groups raw packets into bidirectional flows keyed by:
$$\text{FlowKey} = (\min(\text{src\_ip}, \text{dst\_ip}), \max(\text{src\_ip}, \text{dst\_ip}), \min(\text{src\_port}, \text{dst\_port}), \max(\text{src\_port}, \text{dst\_port}), \text{protocol})$$
- **Flow Lifecycles:**
  - Idle timeout: 30 seconds of inactivity triggers flow expiration.
  - Active timeout: Flows exceeding 1,000 packets are flushed.
  - Explicit termination: TCP `FIN` or `RST` packets mark immediate flow closure.

### 6.3 42-Feature Extraction Engine (`FlowFeatures`)
Computes comprehensive statistical metrics from each flow:
1. **Time & Volume:** `duration`, `total_bytes`, `src_bytes`, `dst_bytes`, `total_packets`, `src_packets`, `dst_packets`.
2. **Ratios & Rates:** `byte_ratio` ($\frac{\text{src\_bytes}}{\text{dst\_bytes}}$), `packet_ratio`, `bytes_per_second`, `packets_per_second`, `src_byte_rate`, `dst_byte_rate`.
3. **TCP Flags & Connection State:** `serror_rate` (SYN error rate), `rerror_rate` (REJ error rate), `same_srv_rate`, `diff_srv_rate`, `tcp_state` (`SF`, `S0`, `REJ`, `RSTO`, etc.).
4. **Window Statistics:** `dst_host_count`, `dst_host_srv_count`.
5. **One-Hot Mapping:** Maps categorical features (`protocol`, `service`, `flag`) to match trained model input vectors.

---

## 7. Security Alert Engine & Deduplication

### 7.1 Alert Generation Trigger
An alert is generated if:
1. `EnsemblePrediction.prediction == "anomaly"` AND
2. `EnsemblePrediction.composite_risk_score >= ALERT_MIN_RISK_SCORE` (default 50.0) AND
3. The severity level is enabled in settings (`ALERT_HIGH_ENABLED=True`, `ALERT_CRITICAL_ENABLED=True`).

### 7.2 SHA-256 Fingerprint Deduplication
To prevent flooding the SOC with thousands of alerts during a continuous DoS or brute-force attack, each alert is fingerprinted:
$$\text{Fingerprint} = \text{SHA256}(\text{src\_ip} \parallel \text{dst\_ip} \parallel \text{src\_port} \parallel \text{dst\_port} \parallel \text{protocol} \parallel \text{alert\_type})$$
- **Cooldown Window:** 300 seconds (configurable via `ALERT_DEDUP_WINDOW_SECONDS`).
- **Behavior on Duplicate:**
  - If an alert with the same fingerprint was generated within the cooldown window, a new alert is **not** created.
  - The existing alert's `duplicate_count` is incremented.
  - `last_seen` timestamp is updated in the database.
  - `risk_score` is updated to the maximum observed.

### 7.3 Alert Lifecycle States
- `OPEN`: Newly generated alert awaiting analyst review.
- `ACKNOWLEDGED`: Analyst has claimed the incident for triage.
- `RESOLVED`: Threat mitigated or verified harmless.
- `DISMISSED`: Flagged as a false positive.

---

## 8. Database Architecture & MongoDB Collections

Database Name: `zero_day_detection`  
Async Driver: `motor.motor_asyncio.AsyncIOMotorClient`

### 8.1 Collections & Schemas

#### 1. `users` Collection
- Fields: `user_id` (string UUID), `username` (string, unique), `email` (string, unique), `hashed_password` (string bcrypt), `full_name` (string), `role` (`admin` | `analyst` | `viewer`), `is_active` (bool), `created_at` (datetime), `last_login_at` (datetime).
- Indexes:
  - `idx_users_username_unique`: `{"username": 1}`, unique
  - `idx_users_email_unique`: `{"email": 1}`, unique
  - `idx_users_role`: `{"role": 1}`

#### 2. `network_logs` Collection
- Fields: `log_id` (UUID), `timestamp` (datetime), `source_ip` (string), `destination_ip` (string), `source_port` (int), `destination_port` (int), `protocol` (string), `packet_count` (int), `byte_count` (int), `raw_features` (dict).
- Indexes:
  - `idx_netlog_timestamp`: `{"timestamp": -1}`
  - `idx_netlog_flow_compound`: `{"source_ip": 1, "destination_ip": 1, "timestamp": -1}`

#### 3. `detection_results` Collection
- Fields: `detection_id` (UUID), `timestamp` (datetime), `model_name` (string), `prediction` (`normal` | `anomaly`), `anomaly_score` (float 0-100), `severity` (`LOW` | `MEDIUM` | `HIGH` | `CRITICAL`), `processing_time_ms` (float), `model_contributions` (dict), `xai_attribution` (list).
- Indexes:
  - `idx_det_timestamp`: `{"timestamp": -1}`
  - `idx_det_severity`: `{"severity": 1}`
  - `idx_det_anomaly_score`: `{"anomaly_score": -1}`

#### 4. `alerts` Collection
- Fields: `alert_id` (UUID, `alt-...`), `timestamp` (datetime), `severity` (string), `priority` (string), `status` (`OPEN` | `ACKNOWLEDGED` | `RESOLVED` | `DISMISSED`), `risk_score` (float), `source` (`{ip, port}`), `destination` (`{ip, port}`), `protocol` (string), `deduplication` (`{fingerprint, duplicate_count, first_seen, last_seen}`), `models_involved` (list), `xai_top_features` (list), `assigned_to` (string), `audit_history` (list).
- Indexes:
  - `idx_alert_id_unique`: `{"alert_id": 1}`, unique
  - `idx_alert_timestamp`: `{"timestamp": -1}`
  - `idx_alert_severity`: `{"severity": 1}`
  - `idx_alert_status`: `{"status": 1}`
  - `idx_alert_dedup_fingerprint`: `{"deduplication.fingerprint": 1}`

#### 5. `system_events` Collection
- Fields: `event_id` (UUID), `timestamp` (datetime), `event_type` (string), `level` (`INFO` | `WARNING` | `ERROR` | `CRITICAL`), `component` (string), `message` (string), `details` (dict).
- Indexes:
  - `idx_event_timestamp`: `{"timestamp": -1}`
  - `idx_event_level`: `{"level": 1}`

#### 6. `audit_logs` Collection
- Fields: `audit_id` (UUID), `timestamp` (datetime), `user_id` (string), `action` (string, e.g. `USER_LOGIN`, `ALERT_TRIAGE`, `CONFIG_UPDATE`), `resource` (string), `resource_id` (string), `status` (`SUCCESS` | `FAILED`), `client_ip` (string), `metadata` (dict).
- Indexes:
  - `idx_audit_timestamp`: `{"timestamp": -1}`
  - `idx_audit_user_id`: `{"user_id": 1}`
  - `idx_audit_action`: `{"action": 1}`

---

## 9. Backend API Architecture & Security Layer

### 9.1 REST API Routes Structure (`/api/v1`)
- `/api/v1/auth`:
  - `POST /login`: Authenticates username/password, issues access token & refresh token.
  - `POST /refresh`: Issues new access token from valid refresh token.
  - `POST /logout`: Invalidation and audit logging.
  - `GET /me`: Returns current authenticated user profile and permissions.
- `/api/v1/detection`:
  - `POST /predict`: Single network flow inference through multi-model ensemble.
  - `POST /predict-batch`: Batch flow inference (up to 500 records).
  - `POST /predict-sequence`: Sequential window inference for LSTM autoencoder.
  - `GET /history`: Paginated historical detection ledger.
- `/api/v1/monitoring`:
  - `POST /start`: Starts live packet sniffing or PCAP streaming.
  - `POST /stop`: Stops sniffing and flushes flow pipeline.
  - `GET /status`: Real-time packets/sec, flow throughput, buffer fill percentage.
  - `GET /interfaces`: Lists network adapters and capture driver readiness.
  - `POST /test-pcap`: Isolated PCAP inspection and analytical replay benchmark.
- `/api/v1/alerts`:
  - `GET /`: Paginated security alerts with multi-criteria filtering.
  - `GET /{alert_id}`: Granular alert details with XAI explanations.
  - `PATCH /{alert_id}/status`: Transition status (`OPEN`, `ACKNOWLEDGED`, `RESOLVED`, `DISMISSED`).
  - `POST /{alert_id}/notes`: Append triage investigation notes.
- `/api/v1/statistics`:
  - `GET /summary`: Top-level SOC KPIs (total detections, anomalies, active models, alert counts).
  - `GET /alerts`: 24-hour alert distribution by severity and status.
  - `GET /models`: Multi-model operational benchmark metrics.
- `/api/v1/models`:
  - `GET /`: Lists all models in registry with versions, hyperparameters, and active flags.
  - `POST /{model_name}/toggle`: Dynamically activate or deactivate models in the ensemble.
- `/api/v1/users` (Admin Only):
  - `GET /`: Lists all security platform users.
  - `POST /`: Provisions new users with specific RBAC roles.
  - `PATCH /{user_id}`: Updates user roles or active status.
  - `DELETE /{user_id}`: Deactivates accounts (with guard against deleting the last active admin).
- `/health` and `/api/health`:
  - Unauthenticated health probe returning live MongoDB ping latency, ML engine status, and memory stats.

### 9.2 Enterprise Security Middlewares
1. **`SecurityHeadersMiddleware`**:
   Injects hardening headers on every response:
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: DENY`
   - `X-XSS-Protection: 1; mode=block`
   - `Strict-Transport-Security: max-age=31536000; includeSubDomains` (when HTTPS enabled)
   - `Content-Security-Policy: default-src 'self'`
2. **`RequestSizeLimitMiddleware`**:
   Enforces maximum request payload sizes (10 MB default, 50 MB for PCAP uploads) returning `413 Payload Too Large`.
3. **`ApiRateLimiterMiddleware`**:
   Sliding window in-memory token bucket rate limiter. Blocks abuse and brute-force attempts while keeping health probes exempt.
4. **`RequestIDMiddleware`**:
   Generates a unique `X-Request-ID` (`req-...`) for every request, logging execution latency in `X-Process-Time`.

---

## 10. Frontend Architecture & SOC Dashboard Design

### 10.1 Theme & Aesthetics
- **Color Palette:** Curated Cyber-SOC Dark Theme
  - Background: `#0B0F19` (Deep Obsidian Void)
  - Surface Card: `rgba(17, 24, 39, 0.7)` with `backdrop-filter: blur(16px)`
  - Borders: `1px solid rgba(255, 255, 255, 0.08)`
  - Accent Cyan: `#06B6D4`, Indigo: `#6366F1`
  - Severity Alerts: Emerald (`#10B981`), Amber (`#F59E0B`), Orange (`#F97316`), Crimson (`#EF4444`)
- **Typography:** Modern clean sans-serif font stack (Inter / system fonts) with monospace styling for IPs, hashes, ports, and timestamps.

### 10.2 Frontend Application Pages
1. **SOC Command Dashboard (`Dashboard.jsx`)**:
   - 4 Primary KPI metric tiles (Total Flows Monitored, Threat Detections, Active Security Incidents, Active AI Models).
   - Real-time 24-Hour Severity Threat Distribution Donut Chart.
   - 24-Hour Threat Detection Timeline Area Chart.
   - Live AI Model Status indicators with latency indicators.
2. **Real-Time Traffic Monitor (`Monitoring.jsx`)**:
   - Adapter selection dropdown with live driver status.
   - Start / Stop Live Capture button with pulsing operational radar indicator.
   - Drag-and-drop PCAP file replay harness with progress bar and execution benchmark summary.
   - Live streaming flow table with automatic scroll and severity color tags.
3. **Security Incident Alerts Center (`Alerts.jsx`)**:
   - Multi-filter toolbar (Severity, Status, Model consensus, Time window).
   - Paginated incident table showing fingerprint, source/destination endpoints, risk score gauge, and status pill.
   - Quick triage action buttons (Acknowledge, Resolve, Dismiss).
4. **Deep-Dive Alert Investigation Modal (`AlertDetails.jsx`)**:
   - Per-feature XAI attribution horizontal bar chart highlighting top-10 anomalous features.
   - Raw flow telemetry viewer (protocols, TCP flags, byte distribution).
   - Audit event trail showing history of modifications and notes.
5. **AI Model Registry & Performance Comparison (`Models.jsx`)**:
   - Model cards with version, dataset trained on, latency (ms), throughput (rec/s).
   - Radar comparison chart plotting Accuracy, Precision, Recall, F1, and Zero-Day Detection Rate.
   - Active ensemble toggle switch.
6. **Flow Detection History Ledger (`DetectionHistory.jsx`)**:
   - Searchable, auditable ledger of all analyzed network flows with individual detector score votes.
7. **System Health & Telemetry Diagnostics (`SystemHealth.jsx`)**:
   - Live MongoDB connection pool status, ping latency graph, memory usage, API latency.
8. **User & Access Management (`Users.jsx`)**:
   - Admin-only management portal to invite analysts, configure roles, reset passwords, or deactivate accounts.
9. **Authentication Clearance (`Login.jsx`)**:
   - Hardened login form with animated cybersecurity shield banner, error handling, and demo account credential buttons.

---

## 11. Testing & Validation Strategy

The project implements a **two-tier testing suite**:

### 11.1 Backend Pytest Suite (210 Tests)
- `test_isolation_forest.py`: Unsupervised training, threshold calculation, score bounding $[0, 100]$, artifact saving/loading.
- `test_autoencoder.py`: PyTorch network forward pass, reconstruction error computation, 95th percentile thresholding, early stopping.
- `test_lstm.py`: Sliding window tensor shaping `(B, 10, D)`, sequential reconstruction, temporal anomaly detection.
- `test_random_forest.py`: Supervised training, probability calibration, feature importance extraction.
- `test_model_comparison.py`: Data leakage prevention, standardized metrics calculation (Accuracy, Precision, Recall, F1, Specificity, Zero-Day proxy detection rate).
- `test_monitoring.py`: Scapy packet parsing, bidirectional 5-tuple flow aggregation, idle/active expiration, PCAP replay.
- `test_security.py`: Security headers validation, CORS preflight verification, JWT token expiration and forgery rejection, password hashing, rate limiting, request size limits.
- `test_rbac.py`: Role enforcement (`VIEWER` read-only, `ANALYST` triage permitted, `ADMIN` full management).
- `test_users.py`: User CRUD operations, last admin deletion guard.
- `test_schemas_validation.py`: Pydantic v2 document constraints and type safety.

### 11.2 Frontend Vitest Suite (16 Tests)
- `auth.test.js`: Token persistence, session clearance on 401, role permission mapping.
- `api_client.test.js`: Axios/Fetch wrapper, bearer token injection, timeout handling, error response mapping.
- `formatters.test.js`: Timestamp formatting, byte/rate unit conversion (KB/s, MB/s), risk score color coding.

---

## 12. Reproduction Step-by-Step Guide for an Agent

To build this exact project from scratch, execute the following steps in sequence:

### Step 1: Initialize Project Directory Structure
Create the following directory tree:
```
ZERO/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/
│   │   ├── auth/
│   │   ├── core/
│   │   ├── database/
│   │   ├── alerts/
│   │   ├── detection/
│   │   ├── ml/
│   │   │   ├── models/
│   │   │   ├── training/
│   │   │   ├── inference/
│   │   │   ├── evaluation/
│   │   │   ├── explainability/
│   │   │   ├── ensemble/
│   │   │   ├── data/
│   │   │   └── registry/
│   │   ├── monitoring/
│   │   │   ├── capture/
│   │   │   ├── parsing/
│   │   │   ├── flow/
│   │   │   ├── features/
│   │   │   └── buffer/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   └── tests/
├── frontend/
│   └── src/
│       ├── api/
│       ├── components/
│       ├── context/
│       ├── pages/
│       └── __tests__/
├── data/
│   ├── raw/
│   ├── processed/
│   └── sample/
├── ml_models/
│   ├── trained/
│   ├── preprocessing/
│   └── explainers/
├── scripts/
├── docs/
└── docker-compose.yml
```

### Step 2: Implement Backend Core & Database Layer
1. Write `backend/app/core/config.py` using `pydantic_settings.BaseSettings` supporting `.env` cascading.
2. Write `backend/app/database/connection.py` initializing `AsyncIOMotorClient` with connection pooling (`minPoolSize=10`, `maxPoolSize=50`, `serverSelectionTimeoutMS=5000`).
3. Write `backend/app/database/indexes.py` defining compound indexes for all 6 collections.
4. Implement `backend/app/database/repository.py` implementing generic CRUD and domain repositories.

### Step 3: Implement Authentication & Security Middlewares
1. Implement password hashing using `bcrypt` and JWT token creation/verification using `pyjwt`.
2. Write dependency functions: `get_current_user`, `require_admin`, `require_analyst_or_admin`, `require_any_authenticated`.
3. Implement `SecurityHeadersMiddleware`, `ApiRateLimiterMiddleware`, `RequestSizeLimitMiddleware`, and `RequestIDMiddleware`.

### Step 4: Implement the Machine Learning Subsystem
1. Implement `IsolationForestDetector` using scikit-learn.
2. Implement PyTorch `DenseAutoencoderNetwork` and `AutoencoderDetector`.
3. Implement PyTorch `LSTMAutoencoderNetwork` and `LSTMAutoencoderDetector`.
4. Implement `RandomForestClassifierModel`.
5. Implement `EnsembleRiskScorer` with dynamic weight renormalization and 4-tier severity mapping.
6. Implement `FeatureAttributor` for SHAP and reconstruction error delta attribution.
7. Implement `ModelRegistry` persisting to `ml_models/model_registry.json`.

### Step 5: Implement Network Monitoring & Ingestion
1. Write `PacketParser` parsing Ethernet/IP/TCP/UDP/ICMP packets with Scapy.
2. Write `FlowAggregator` aggregating packets into bidirectional flows with 30s timeout and TCP FIN/RST tracking.
3. Write `FlowFeatures` computing the 42 statistical flow metrics.
4. Write `LiveCaptureSource` with Scapy `AsyncSniffer` and `PcapCaptureSource` with `PcapReader`.
5. Write `MonitoringManager` coordinating capture, feature extraction, detection inference, and alert triggering.

### Step 6: Implement Alert Engine & Business Services
1. Implement `AlertRuleEngine` and `AlertDeduplicator` with SHA-256 fingerprinting and 300s cooldown.
2. Implement `AlertService`, `DetectionService`, `AuthService`, and `StatisticsService`.

### Step 7: Build FastAPI Router Layer
1. Register routers for `/auth`, `/detection`, `/monitoring`, `/alerts`, `/statistics`, `/models`, `/users`, and `/health`.
2. Connect `lifespan` handler to initialize MongoDB, load trained models from disk, and print console status.

### Step 8: Build React 19 Frontend Dashboard
1. Initialize React + Vite project with `lucide-react`.
2. Create `index.css` defining the cyber-dark design tokens and glassmorphism styling.
3. Implement `AuthContext` managing token storage, Axios interceptors, and user session state.
4. Implement the 8 views: `Dashboard`, `Monitoring`, `Alerts`, `AlertDetailsModal`, `Models`, `DetectionHistory`, `SystemHealth`, `Users`, and `Login`.

### Step 9: Seed Initial Users & Run Verification
1. Run user seeding script `scripts/seed_users.py --non-interactive` to provision `admin`, `analyst`, and `viewer`.
2. Execute full test suite `pytest backend/tests -v` and `npm test` in `frontend/`.
3. Verify all 210 backend tests and 16 frontend tests pass with 0 failures.
4. Launch backend and frontend and verify real-time monitoring and alert triage on `http://localhost:5173`.

---

## 13. Summary Checklist for 100% Replication Fidelity

- [x] PyTorch Dense & LSTM Autoencoders with reconstruction MSE thresholding
- [x] Scikit-Learn Isolation Forest with normalized $[0, 100]$ anomaly scores
- [x] Random Forest supervised benchmark classifier
- [x] Dynamic weighted ensemble fusion with model dropout resilience
- [x] 42-metric statistical flow aggregator from raw Scapy packets
- [x] XAI feature attribution via SHAP and reconstruction error deltas
- [x] SHA-256 fingerprint deduplication with 300s sliding cooldown
- [x] Role-Based Access Control (`ADMIN`, `ANALYST`, `VIEWER`)
- [x] Motor Async MongoDB persistence with 6 indexed collections
- [x] Security hardening (Rate limiting, Security headers, 10MB payload cap)
- [x] React 19 glassmorphic dark-mode SOC dashboard
- [x] 210 backend automated tests + 16 frontend tests
