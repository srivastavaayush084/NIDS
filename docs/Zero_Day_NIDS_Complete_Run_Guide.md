# ZERO-DAY NIDS: Complete Project Run Guide & Local Deployment Manual

> **Document Version:** 1.0.0  
> **Target System:** Zero-Day Network Intrusion Detection System (ZeroDayAI)  
> **Deployment Scope:** Local Development & Evaluation Machine  
> **Operating System:** Microsoft Windows 10 / 11 (with Linux/macOS cross-reference)  
> **Target Audience:** Security Engineers, Developers, Evaluators, and System Operators

---

## Table of Contents

1. [Executive Overview & System Architecture](#1-executive-overview--system-architecture)
2. [Prerequisites & System Requirements](#2-prerequisites--system-requirements)
3. [Project Directory Structure](#3-project-directory-structure)
4. [Python Virtual Environment Policy](#4-python-virtual-environment-policy)
5. [Database Setup (MongoDB)](#5-database-setup-mongodb)
6. [Environment Variables Configuration](#6-environment-variables-configuration)
7. [Backend Setup & Installation](#7-backend-setup--installation)
8. [Database Seeding & RBAC User Management](#8-database-seeding--rbac-user-management)
9. [Backend Server Startup & Verification](#9-backend-server-startup--verification)
10. [Frontend Setup & Installation](#10-frontend-setup--installation)
11. [Frontend Server Startup & Access](#11-frontend-server-startup--access)
12. [Quick Start Guide (Zero to Running)](#12-quick-start-guide-zero-to-running)
13. [End-to-End Application Workflow & Operations](#13-end-to-end-application-workflow--operations)
14. [Real-Time Network Monitoring & Live Sniffing](#14-real-time-network-monitoring--live-sniffing)
15. [PCAP File Ingestion & Replay Testing](#15-pcap-file-ingestion--replay-testing)
16. [SOC Dashboard Telemetry & Analytics](#16-soc-dashboard-telemetry--analytics)
17. [Security Incident Alert Management](#17-security-incident-alert-management)
18. [Detection History & Zero-Day Analytics](#18-detection-history--zero-day-analytics)
19. [AI Ensemble Model Registry](#19-ai-ensemble-model-registry)
20. [System Health Diagnostics](#20-system-health-diagnostics)
21. [User Management (Admin Console)](#21-user-management-admin-console)
22. [Verification, Quality Assurance & Test Commands](#22-verification-quality-assurance--test-commands)
23. [Comprehensive Troubleshooting Manual](#23-comprehensive-troubleshooting-manual)
24. [Common Windows Administration Commands](#24-common-windows-administration-commands)
25. [Daily Operations: Startup & Orderly Shutdown](#25-daily-operations-startup--orderly-shutdown)
26. [Security Best Practices & Production Hardening](#26-security-best-practices--production-hardening)
27. [Known Limitations & Operational Boundaries](#27-known-limitations--operational-boundaries)

---

## 1. Executive Overview & System Architecture

The **Zero-Day Network Intrusion Detection System (ZeroDayAI)** is an enterprise-grade, real-time cyber defense platform architected to detect known cyber attacks as well as previously unseen (zero-day) network anomalies. It utilizes a **4-model hybrid AI ensemble**, a calibrated risk-scoring engine, Explainable AI (XAI) feature attribution, and a high-performance React SOC monitoring interface.

### End-to-End Processing Architecture

```
                                [ Network Traffic Ingestion ]
                                  │                     │
                        (Live Network Sniffing)    (PCAP Replay)
                                  │                     │
                                  ▼                     ▼
                        [ Packet Dissection & Flow Aggregation ]
                                  │
                                  ▼
                        [ 42-Feature Extraction & Mapping ]
                                  │
                                  ▼
                        [ Preprocessing & StandardScaler ]
                                  │
         ┌────────────────────────┼────────────────────────┬────────────────────────┐
         ▼                        ▼                        ▼                        ▼
[ Isolation Forest ]     [ Deep Autoencoder ]     [ LSTM Autoencoder ]     [ Random Forest ]
  (Tree Partition)      (Reconstruction MSE)     (Temporal Sequences)      (Supervised Flow)
         │                        │                        │                        │
         └────────────────────────┼────────────────────────┴────────────────────────┘
                                  ▼
                    [ Ensemble Risk Scoring Engine ]
                   (Normalized Calibrated Score: 0-100)
                                  │
                                  ▼
               [ Severity Classifier & XAI Explainer ]
               (Low / Medium / High / Critical + SHAP)
                                  │
                                  ▼
                     [ Security Alert Engine ]
                (Deduplication & Cooldown Dispatch)
                                  │
                                  ▼
                   [ MongoDB Asynchronous Storage ]
              (users, logs, detections, alerts, events)
                                  │
                                  ▼
                     [ FastAPI Asynchronous Core ]
                                  │
                                  ▼
                   [ React SOC Operations Console ]
```

### Core Subsystems

| Subsystem | Technology | Primary Function |
|:---|:---|:---|
| **API Server** | FastAPI (Python 3.10+) | High-throughput asynchronous REST API, security middleware, JWT authentication, and RBAC control. |
| **Database** | MongoDB 6.0+ / 7.0+ | Document storage for telemetry, detection results, deduplicated alerts, audit trails, and user credentials. |
| **ML Engine** | PyTorch, Scikit-Learn, Joblib | 4-model ensemble (Isolation Forest, Dense Autoencoder, LSTM Autoencoder, Random Forest). |
| **XAI Engine** | SHAP & Perturbation | Generates explainable feature attribution weights and contextual plain-English security summaries. |
| **Traffic Engine** | Scapy & Custom Flow Aggregator | Real-time live packet sniffing and PCAP replay with 42-feature extraction. |
| **SOC Dashboard** | React 19, Vite, Lucide Icons | Real-time security analyst dashboard, triage workflows, alert life-cycle controls, and health probes. |

---

## 2. Prerequisites & System Requirements

Before setting up the project, ensure your workstation satisfies the software and hardware requirements.

### Hardware Requirements
- **CPU:** Dual-core 2.0 GHz or higher (Quad-core recommended for PyTorch LSTM training)
- **RAM:** 8 GB minimum (16 GB recommended)
- **Disk Space:** 5 GB free disk space for dependencies, ML models, and packet traces

### Software Requirements & Verification

| Software | Minimum Version | Verified Version | Verification Command |
|:---|:---|:---|:---|
| **Operating System** | Windows 10 / 11 | Windows 11 Pro 64-bit | `cmd /c ver` |
| **Python** | 3.10.x | 3.14.3 / 3.11.x | `python --version` |
| **Node.js** | 18.x LTS | 24.14.0 | `node --version` |
| **npm** | 9.x | 10.9.0 | `npm --version` |
| **MongoDB Server** | 6.0+ Community / Atlas | 7.0.x / Atlas M0+ | `mongosh --version` |
| **Git** | 2.30+ | 2.40+ | `git --version` |
| **Web Browser** | Modern Chromium / Firefox | Chrome / Edge / Firefox | UI Access |

### Version Check Commands

Run the following commands in **PowerShell** or **Command Prompt** to verify prerequisites:

```powershell
python --version
node --version
npm --version
git --version
```

Expected output example:
```
Python 3.14.3
v24.14.0
10.9.0
git version 2.45.0.windows.1
```

---

## 3. Project Directory Structure

The project follows a structured repository layout separating the backend server, frontend application, pre-trained AI artifacts, dataset splits, and maintenance scripts.

```
ZERO/
├── backend/                              # FastAPI Python Backend
│   ├── .env                              # Active backend environment configuration
│   ├── .env.example                      # Template environment variables
│   ├── .venv/                            # Mandatory Python virtual environment
│   ├── requirements.txt                  # Python dependencies manifest
│   ├── README.md                         # Backend developer readme
│   ├── app/                              # Application source tree
│   │   ├── main.py                       # FastAPI entrypoint & lifespan lifecycle
│   │   ├── api/                          # HTTP endpoints & middleware
│   │   │   ├── middleware.py             # Rate limit, security headers, request ID
│   │   │   ├── errors.py                 # Centralized exception handlers
│   │   │   └── v1/                       # API Version 1 routers
│   │   │       ├── api.py                # Main v1 router assembly
│   │   │       └── endpoints/            # Individual domain endpoints
│   │   │           ├── auth.py           # Login, refresh token, user me
│   │   │           ├── users.py          # Admin RBAC user management
│   │   │           ├── health.py         # MongoDB & system health probes
│   │   │           ├── detection.py      # Single/batch/sequence ML inference
│   │   │           ├── alerts.py         # Security incident alert triage
│   │   │           ├── models.py         # AI model registry & metrics
│   │   │           ├── monitoring.py     # Live sniff & PCAP replay engine
│   │   │           └── statistics.py     # SOC telemetry aggregation
│   │   ├── auth/                         # JWT token creation & password hashing
│   │   ├── core/                         # Configuration settings & logging
│   │   ├── database/                     # MongoDB connection, client, indexes
│   │   ├── ml/                           # ML model loaders, ensemble, XAI
│   │   ├── monitoring/                   # Scapy packet sniffer & flow engine
│   │   ├── schemas/                      # Pydantic request/response schemas
│   │   └── services/                     # Business logic & alert engine
│   └── tests/                            # 210+ Pytest unit & integration tests
├── frontend/                             # React 19 Single Page Application
│   ├── .env                              # Active frontend environment configuration
│   ├── .env.example                      # Frontend environment template
│   ├── package.json                      # npm dependencies and script hooks
│   ├── vite.config.js                    # Vite bundler configuration
│   ├── index.html                        # Application entry HTML
│   ├── src/                              # React component source code
│   │   ├── App.jsx                       # Routing & master layout wrapper
│   │   ├── main.jsx                      # React DOM mount point
│   │   ├── index.css                     # Global design tokens & CSS variables
│   │   ├── api/                          # Centralized fetch API client
│   │   ├── components/                   # Reusable UI widgets & status badges
│   │   ├── context/                      # AuthContext & RBAC session state
│   │   ├── hooks/                        # Custom polling hooks (useHealth, useAlerts)
│   │   ├── layouts/                      # MainLayout with header, sidebar, footer
│   │   ├── pages/                        # Route pages (Dashboard, Alerts, etc.)
│   │   └── utils/                        # Data formatters & date transformers
│   └── dist/                             # Compiled production bundle
├── data/                                 # Datasets & sample network captures
│   ├── processed/                        # Cleaned & scaled CSV datasets
│   ├── raw/                              # Original raw traffic captures
│   ├── sample/                           # Test PCAP files for ingestion
│   └── splits/                           # Train, test, and zero-day attack splits
├── ml_models/                            # Serialized Machine Learning Artifacts
│   ├── model_registry.json               # Metadata & thresholds for all 4 models
│   ├── trained/                          # Serialized .joblib & .pt model weights
│   ├── preprocessing/                    # Serialized StandardScaler & label encoders
│   └── explainers/                       # Serialized SHAP explainers
├── scripts/                              # Setup, seeding, and execution scripts
│   ├── setup_env.bat                     # Automated Windows venv setup script
│   ├── start_backend.bat                 # One-click backend startup script
│   ├── start_frontend.bat                # One-click frontend startup script
│   ├── test_backend.bat                  # Automated pytest test runner
│   ├── seed_users.py                     # Initial RBAC account seeding script
│   ├── test_mongo_verification.py        # Database connectivity diagnostic
│   └── run_phase18_performance_benchmarks.py # Benchmark suite
└── docs/                                 # Technical architecture specifications
```

---

## 4. Python Virtual Environment Policy

> [!IMPORTANT]
> **MANDATORY PYTHON RUNTIME REQUIREMENT:**  
> All Python operations, scripts, servers, tests, and training workflows **MUST** execute exclusively inside the isolated virtual environment: `backend/.venv`.  
> **DO NOT** install dependencies into your global Python environment.

### Why backend/.venv is Mandatory
1. **Dependency Isolation:** Avoids version conflicts with existing packages (e.g., PyTorch 2.x, NumPy 2.x, Scikit-Learn).
2. **Deterministic Execution:** Guarantees that exact pinned versions in `requirements.txt` are active.
3. **Reproducibility:** Ensures seamless cross-developer onboarding without environment pollution.

### Creating the Virtual Environment (Fresh Machine)

Open a terminal at the project root (`ZERO/`) and execute:

```powershell
cd backend
python -m venv .venv
```

### Activating the Virtual Environment

#### On Windows (PowerShell):
```powershell
.\backend\.venv\Scripts\Activate.ps1
```
*(If execution of scripts is disabled on PowerShell, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first).*

#### On Windows (Command Prompt):
```cmd
backend\.venv\Scripts\activate.bat
```

#### On Linux / macOS:
```bash
source backend/.venv/bin/activate
```

### Direct Python Invocation (Without Shell Activation)

You can execute any project script directly using the absolute binary path:

```powershell
.\backend\.venv\Scripts\python.exe <script_path.py>
```

---

## 5. Database Setup (MongoDB)

ZeroDayAI utilizes **MongoDB** as its primary document datastore. The system automatically creates collections and builds compound performance indexes on server startup.

- **Default Database Name:** `zero_day_detection`
- **Default Local Connection URI:** `mongodb://localhost:27017`

### 6 Core Database Collections

1. **`users`**: RBAC user accounts, hashed passwords, active states, and audit timestamps.
2. **`network_logs`**: Ingested raw network flow features, IPs, ports, protocols, and packet counts.
3. **`detection_results`**: AI model inference scores, anomaly flags, severity ratings, and latencies.
4. **`alerts`**: Deduplicated security incidents, priority ratings, triage states, and XAI summaries.
5. **`system_events`**: Component lifecycle logs, monitoring state transitions, and system errors.
6. **`audit_logs`**: Tamper-evident record of user actions (logins, user creations, alert triage).

---

### Option A: Running Local MongoDB (Windows Service)

If MongoDB Server 6.0+ or 7.0+ is installed on your Windows machine:

1. Open **PowerShell as Administrator**.
2. Check the status of the MongoDB service:
   ```powershell
   Get-Service -Name MongoDB
   ```
3. Start the service:
   ```powershell
   Start-Service -Name MongoDB
   ```
   *(Or using Command Prompt: `net start MongoDB`)*
4. Verify the service is running:
   ```powershell
   Get-Service -Name MongoDB
   ```
   Expected status: `Running`.

---

### Option B: Running Local MongoDB (Standalone Process)

If MongoDB is installed without a Windows service:

```powershell
"C:\Program Files\MongoDB\Server\7.0\bin\mongod.exe" --dbpath "C:\data\db"
```
*(Ensure `C:\data\db` directory exists before running).*

---

### Option C: Using MongoDB Atlas (Cloud Database)

If using a remote MongoDB Atlas cluster:
1. Obtain your connection string from MongoDB Cloud Atlas.
2. Format: `mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/`
3. Update `MONGODB_URI` in `backend/.env`.

---

### Verifying MongoDB Connectivity

To verify that the database is reachable and all 6 collections are accessible, run the direct verification tool:

```powershell
.\backend\.venv\Scripts\python.exe scripts/test_mongo_verification.py
```

Expected output:
```
============================================================
ZeroDayAI MongoDB Direct Verification Test
============================================================
Target Database : zero_day_detection
Connection URI  : [localhost:27017]
Environment     : development
------------------------------------------------------------
Ping Result     : SUCCESS (ok=1.0)
Ping Latency    : 2.15 ms
MongoDB Status  : CONNECTED
MongoDB Version : 7.0.12
Server Type     : Standalone
Accessible DB   : zero_day_detection
------------------------------------------------------------
Checking Required Collections:
  - users               : Accessible (doc count: 3)
  - network_logs        : Accessible (doc count: 120)
  - detection_results   : Accessible (doc count: 120)
  - alerts              : Accessible (doc count: 14)
  - system_events       : Accessible (doc count: 45)
  - audit_logs          : Accessible (doc count: 18)
============================================================
RESULT: MongoDB is ACTUALLY connected and fully functional.
============================================================
```

---

## 6. Environment Variables Configuration

ZeroDayAI requires environment files for both the backend and frontend. Templates (`.env.example`) are provided in the repository.

### Backend Environment Configuration (`backend/.env`)

Create `backend/.env` by copying `backend/.env.example`:

```powershell
# From project root:
Copy-Item backend\.env.example backend\.env
```

#### Backend Environment Variables Reference Table

| Variable | Required | Default Value | Description |
|:---|:---:|:---|:---|
| `PROJECT_NAME` | No | `"ZeroDayAI - Zero-Day Attack Detection Platform"` | Display title of the application |
| `ENVIRONMENT` | Yes | `"development"` | Environment mode: `development`, `testing`, or `production` |
| `DEBUG` | No | `True` | Enables detailed error traces and auto-reload |
| `LOG_LEVEL` | No | `"INFO"` | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `API_HOST` | Yes | `"0.0.0.0"` | Network interface host binding |
| `API_PORT` | Yes | `8000` | Port for FastAPI HTTP server |
| `FRONTEND_URL` | Yes | `"http://localhost:5173"` | URL of the frontend for CORS policy |
| `CORS_ORIGINS` | Yes | `"http://localhost:3000,http://localhost:5173,http://127.0.0.1:5173"` | Comma-separated list of allowed origins |
| `MONGODB_URI` | Yes | `"mongodb://localhost:27017"` | MongoDB connection URI string |
| `MONGODB_DATABASE` | Yes | `"zero_day_detection"` | Target database name |
| `MONGODB_MIN_POOL_SIZE` | No | `10` | Minimum connection pool size |
| `MONGODB_MAX_POOL_SIZE` | No | `50` | Maximum concurrent connections |
| `MONGODB_TIMEOUT_MS` | No | `2500` | Server selection timeout in milliseconds |
| `MODEL_DIRECTORY` | Yes | `"./ml_models/trained"` | Path to serialized ML model weights |
| `DATA_DIRECTORY` | Yes | `"./data"` | Path to datasets and PCAP directory |
| `PREPROCESSING_DIR` | Yes | `"./ml_models/preprocessing"` | Path to scalers and encoders |
| `DEFAULT_ANOMALY_THRESHOLD` | No | `0.65` | Decision boundary for anomaly detection |
| `HIGH_RISK_THRESHOLD` | No | `0.85` | Threshold triggering HIGH severity |
| `CRITICAL_RISK_THRESHOLD`| No | `0.95` | Threshold triggering CRITICAL severity |
| `JWT_SECRET_KEY` | Yes | `"dev-insecure-secret-key-change-in-production-1234567890"` | Secret key used for signing JWTs (>= 32 chars in prod) |
| `JWT_ALGORITHM` | No | `"HS256"` | Cryptographic algorithm for JWT signatures |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `60` | Lifespan of access token in minutes |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `7` | Lifespan of refresh token in days |
| `AUTH_RATE_LIMIT_MAX_ATTEMPTS` | No | `5` | Maximum failed logins per window |
| `AUTH_RATE_LIMIT_WINDOW_SECONDS`| No | `60` | Login rate limiter window in seconds |
| `API_RATE_LIMIT_DEFAULT_PER_MINUTE` | No | `10000` | General API rate limit threshold |
| `MAX_REQUEST_BODY_BYTES` | No | `10485760` | Max HTTP request size (10 MB) |
| `MAX_PCAP_FILE_BYTES` | No | `52428800` | Max PCAP upload size (50 MB) |

> [!WARNING]
> In production environments, `JWT_SECRET_KEY` must be replaced with a cryptographically secure random string of at least 32 characters. Never commit production `.env` files to source control.

---

### Frontend Environment Configuration (`frontend/.env`)

Create `frontend/.env` by copying `frontend/.env.example`:

```powershell
# From project root:
Copy-Item frontend\.env.example frontend\.env
```

#### Frontend Environment Variables Reference Table

| Variable | Required | Default Value | Description |
|:---|:---:|:---|:---|
| `VITE_API_BASE_URL` | Yes | `http://localhost:8000` | Base URL of the backend FastAPI service |
| `VITE_POLLING_INTERVAL_MS` | No | `5000` | Refresh rate in milliseconds for telemetry polling |

---

## 7. Backend Setup & Installation

Follow these exact steps to prepare the backend on a fresh machine.

### Step 1: Open Terminal & Navigate to Project Root
```powershell
cd C:\Users\Win\Desktop\ZERO
```

### Step 2: Navigate to Backend Directory
```powershell
cd backend
```

### Step 3: Create the Python Virtual Environment
```powershell
python -m venv .venv
```

### Step 4: Upgrade Pip inside the Virtual Environment
```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

### Step 5: Install Python Dependencies from requirements.txt
```powershell
.\.venv\Scripts\pip.exe install -r requirements.txt
```

### Step 6: Install ReportLab for Documentation Rendering
```powershell
.\.venv\Scripts\pip.exe install reportlab
```

### Step 7: Configure Environment File
```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

*(Alternatively, you can run the provided automated batch setup script: `..\scripts\setup_env.bat`)*

---

## 8. Database Seeding & RBAC User Management

ZeroDayAI implements Role-Based Access Control (RBAC) with 3 distinct tiers:

1. **`ADMIN`**: Full administrative access including User Management, triage, and system controls.
2. **`ANALYST`**: Security operations triage access (Acknowledge, Resolve, Dismiss alerts) and monitoring.
3. **`VIEWER`**: Read-only observation access to telemetry, dashboard, detections, and health status.

Passwords are cryptographically salted and hashed using **`bcrypt`** before storage; plaintext credentials are never written to disk or database.

### Running the User Seeding Script

Execute the seeding script using `backend/.venv`:

```powershell
# From project root:
.\backend\.venv\Scripts\python.exe scripts/seed_users.py --non-interactive
```

### Development Accounts Seeded

| Role | Username | Email | Development Password | Permissions Summary |
|:---|:---|:---|:---|:---|
| **ADMIN** | `admin` | `admin@zeroday.local` | `Admin12345!` | Full system & user administration |
| **ANALYST** | `analyst` | `analyst@zeroday.local` | `Analyst12345!` | Incident triage & alert resolution |
| **VIEWER** | `viewer` | `viewer@zeroday.local` | `Viewer12345!` | Read-only telemetry viewing |

### Interactive Mode (Custom Passwords)

To provide custom secure passwords interactively during seeding:

```powershell
.\backend\.venv\Scripts\python.exe scripts/seed_users.py
```

### Updating Existing Passwords

To update passwords for accounts that already exist in MongoDB:

```powershell
.\backend\.venv\Scripts\python.exe scripts/seed_users.py --update-passwords --non-interactive
```

---

## 9. Backend Server Startup & Verification

Start the FastAPI application using Uvicorn with the virtual environment Python interpreter.

### Exact Backend Startup Command

```powershell
# From project root:
.\backend\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

*(Or double-click `scripts\start_backend.bat`)*

### Expected Terminal Startup Output

```
======================================================
ZERO-DAY NIDS BACKEND
======================================================
[OK] Configuration loaded
[OK] MongoDB connected successfully
[OK] Database: zero_day_detection
[OK] Connection type: Standalone
[OK] MongoDB ping: 2.1 ms
[OK] ML models available (4/4 loaded)
[OK] Security headers & rate limiting active
[OK] Monitoring subsystem ready
[OK] API ready
======================================================
Server running on http://0.0.0.0:8000
```

### Available Backend URLs

| Resource | URL | Purpose |
|:---|:---|:---|
| **API Base** | `http://localhost:8000` | Root service health check |
| **Interactive Docs (Swagger)** | `http://localhost:8000/docs` | Interactive OpenAPI testing console |
| **Alternative Docs (ReDoc)** | `http://localhost:8000/redoc` | Formatted API reference specification |
| **OpenAPI Schema** | `http://localhost:8000/openapi.json` | Raw OpenAPI JSON schema |
| **Health Probe Endpoint** | `http://localhost:8000/api/v1/health` | Comprehensive subsystem status |

---

## 10. Frontend Setup & Installation

The frontend is built using **React 19** and **Vite**.

### Step 1: Open a New Terminal & Navigate to Frontend Directory
```powershell
cd C:\Users\Win\Desktop\ZERO\frontend
```

### Step 2: Install Node Dependencies
```powershell
npm install
```

### Step 3: Configure Frontend Environment
```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

### Step 4: Verify Frontend Build
```powershell
npm run build
```
*(Confirms that all JSX templates and CSS compile cleanly without errors).*

---

## 11. Frontend Server Startup & Access

Start the Vite development server:

### Exact Frontend Startup Command

```powershell
# In frontend directory:
npm run dev
```

*(Or from project root: `scripts\start_frontend.bat`)*

### Expected Terminal Output

```
  VITE v8.2.2  ready in 240 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```

### Browser Access

Open your web browser and navigate to:
👉 **`http://localhost:5173`**

You will be presented with the **ZeroDayAI Security Operations Center Login Portal**.

---

## 12. Quick Start Guide (Zero to Running)

For an experienced engineer on an already-configured workstation, use this minimal 3-terminal sequence:

```
┌────────────────────────────────────────────────────────────────────────────┐
│ TERMINAL 1: MongoDB Service (Admin Shell)                                  │
│   Start-Service -Name MongoDB                                              │
├────────────────────────────────────────────────────────────────────────────┤
│ TERMINAL 2: Backend API Server                                             │
│   cd C:\Users\Win\Desktop\ZERO                                             │
│   .\backend\.venv\Scripts\python.exe -m uvicorn backend.app.main:app       │
│                                      --host 0.0.0.0 --port 8000 --reload  │
├────────────────────────────────────────────────────────────────────────────┤
│ TERMINAL 3: Frontend Development Server                                    │
│   cd C:\Users\Win\Desktop\ZERO\frontend                                    │
│   npm run dev                                                              │
├────────────────────────────────────────────────────────────────────────────┤
│ BROWSER ACCESS:                                                            │
│   Open http://localhost:5173                                               │
│   Log in with: admin / Admin12345!                                         │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 13. End-to-End Application Workflow & Operations

Once the system is active, security operations proceed through the following lifecycle:

```
[ Step 1: Login ] ──► Enter credentials (ADMIN, ANALYST, or VIEWER) at /login
        │
[ Step 2: SOC Dashboard ] ──► Review high-level risk score, active alerts, and model readiness
        │
[ Step 3: Traffic Ingestion ] ──► Start Live Monitoring or Replay PCAP sample traces
        │
[ Step 4: AI Ensemble Scoring ] ──► 4 AI models generate anomaly metrics; Ensemble computes risk (0-100)
        │
[ Step 5: Explainable AI ] ──► SHAP extracts top 10 contributing features for any high-risk anomaly
        │
[ Step 6: Incident Alerting ] ──► Alert Engine deduplicates events and raises triage tickets
        │
[ Step 7: Analyst Triage ] ──► Acknowledge, investigate evidence, resolve, or dismiss alerts
        │
[ Step 8: User Administration ] ──► (ADMIN only) Provision and manage analyst permissions at /users
```

---

## 14. Real-Time Network Monitoring & Live Sniffing

The **Monitoring** page (`/monitoring`) provides live network packet capture and continuous anomaly detection.

### Operational Procedure

1. Navigate to **Monitoring** via the sidebar navigation.
2. Under **Capture Source Configuration**, select **Live Interface Sniffing**.
3. (Optional) Set the **Packet Filter** (default: `tcp or udp`).
4. Click **Start Live Monitoring**.
5. Observe live telemetry stream:
   - **Packet Count & Capture Rate (pkts/sec)**
   - **Active Network Flows Aggregated**
   - **Real-Time Detections Counter**
   - **Security Alerts Raised**
6. Click **Stop Monitoring** when testing concludes.

> [!NOTE]
> **Operating System Permissions for Live Capture:**  
> Live packet capture on Windows requires the **Npcap** driver with administrative privileges. If Npcap is not installed or permissions are restricted, use **PCAP Ingestion Mode** for automated testing.

---

## 15. PCAP File Ingestion & Replay Testing

PCAP ingestion enables deterministic evaluation of intrusion detection models using historical or synthetic network packet captures.

### Operational Procedure

1. Place your `.pcap` or `.pcapng` capture files into the allowed data directory:
   `C:\Users\Win\Desktop\ZERO\data\sample\`
2. Navigate to **Monitoring** (`/monitoring`).
3. Select **PCAP File Ingestion Mode**.
4. Choose the target capture file from the dropdown (e.g., `sample_attack_traffic.pcap`).
5. Set replay rate (packets per second) and click **Start PCAP Replay**.
6. Monitor the real-time detection table as flows are extracted, normalized, and classified.

### Generating a Synthetic Test PCAP

If you do not have an existing PCAP capture, generate a valid test file using Scapy:

```powershell
.\backend\.venv\Scripts\python.exe scripts/create_sample_pcap.py
```

---

## 16. SOC Dashboard Telemetry & Analytics

The **Dashboard** (`/dashboard`) serves as the central command console for security operators:

- **Total Ingested Detections:** Real-time count of all processed network flows.
- **Anomalies Identified:** Flows flagged above the anomaly threshold.
- **Open Security Alerts:** Unresolved alerts requiring analyst triage.
- **Critical Incidents:** High-severity threats with risk scores >= 75.0.
- **Average Network Risk Gauge:** Dynamic 0-100 risk needle.
- **Severity Distribution Breakdown:** Categorized bar charts for Low, Medium, High, and Critical events.
- **AI Model Status Grid:** Online health cards for all 4 detection engines.
- **Recent Alerts Stream:** Live feed of newly detected security events.

---

## 17. Security Incident Alert Management

The **Alerts** console (`/alerts`) allows security personnel to inspect and triage security incidents.

### Alert Severity Tiers

| Severity | Risk Score Range | Automatic Action | XAI Generation |
|:---|:---:|:---|:---:|
| **LOW** | 0.00 – 24.99 | Logged for statistical baseline | Disabled |
| **MEDIUM** | 25.00 – 49.99 | Filterable in detection history | Optional |
| **HIGH** | 50.00 – 74.99 | Generates Open Alert incident | **Enabled** |
| **CRITICAL** | 75.00 – 100.00 | Immediate priority incident notification | **Enabled (Full SHAP)** |

### Alert Lifecycle Actions
- **Acknowledge:** Transitions status from `OPEN` to `ACKNOWLEDGED`, marking the incident as under active investigation.
- **Resolve:** Transitions incident to `RESOLVED`, adding remediation notes.
- **Dismiss:** Marks false positives as `DISMISSED` with analyst justification.

### Inspecting Alert Details (`/alerts/:alertId`)
Clicking on any alert card opens the comprehensive forensics view:
1. **Source & Destination Socket Breakdown:** IP addresses, ports, protocol, and flow duration.
2. **Multi-Model Consensus Radar:** Individual anomaly scores from Isolation Forest, Autoencoder, LSTM, and Random Forest.
3. **XAI Top Contributing Features:** Visual bar charts showing the top network parameters (e.g., `flow_duration`, `packet_count`, `syn_flag_count`) responsible for the anomaly score.
4. **Recommended Mitigation Playbook:** Contextual guidance (e.g., block source IP, inspect firewall rules).

---

## 18. Detection History & Zero-Day Analytics

The **Detections** page (`/detections`) maintains an immutable audit log of all individual network flows evaluated by the machine learning pipeline.

### Zero-Day Proxy Explanation

> [!IMPORTANT]
> **SCIENTIFIC METHODOLOGY CLARIFICATION:**  
> In intrusion detection benchmarks, evaluation against "unseen attacks" is conducted using held-out attack category splits (e.g., training exclusively on normal traffic and known exploits, then testing against held-out classes like PortScan, DoS, or Botnet).  
> This represents a valid **zero-day proxy metric**, but does **NOT** provide a mathematical guarantee of detecting every real-world novel exploit.

---

## 19. AI Ensemble Model Registry

The **Models** page (`/models`) provides transparent diagnostics on the 4 underlying detection engines:

| Model Name | Model Type | Core Strength / Contribution | Default Weight |
|:---|:---|:---|:---:|
| **Isolation Forest** | Unsupervised Tree Ensemble | Rapid outlier isolation in high-dimensional feature space. | 25% |
| **Dense Autoencoder** | Unsupervised Neural Network | Non-linear feature compression; detects anomalies via reconstruction loss. | 25% |
| **LSTM Autoencoder** | Sequential Deep Learning | Temporal recurrent architecture; detects multi-step sequential attacks. | 25% |
| **Random Forest** | Supervised Classifier Baseline | Fast signature matching on known attack patterns. | 25% |

---

## 20. System Health Diagnostics

The **System Health** page (`/health`) provides real-time infrastructure diagnostics:

- **API Subsystem:** Online status, process uptime, and request processing latency.
- **MongoDB Database:** Live ping latency, server topology (Standalone/ReplicaSet), connection pool count, and database name (`zero_day_detection`).
- **ML Model Loader:** Verification that all 4 models are loaded in memory.
- **Monitoring Subsystem:** State of packet sniffing threads and flow aggregation buffers.
- **System Memory & CPU:** RAM utilization and thread health.

---

## 21. User Management (Admin Console)

Accessible exclusively to users with the **`ADMIN`** role via `/users`.

### Administrative Capabilities
1. **View User Registry:** Table of all provisioned accounts, email addresses, assigned roles, and creation dates.
2. **Provision New User:** Create user accounts with custom usernames, emails, full names, roles (`ADMIN`, `ANALYST`, `VIEWER`), and secure passwords.
3. **Deactivate / Activate Accounts:** Instantly revoke access for departing personnel without deleting audit logs.
4. **Role Reassignment:** Modify role privileges dynamically.

---

## 22. Verification, Quality Assurance & Test Commands

The project includes an extensive automated test suite covering unit tests, API integration tests, security defense tests, and frontend test suites.

### 1. Backend Automated Tests (210 Tests)

Execute the full backend test suite using `pytest` in `backend/.venv`:

```powershell
# From project root:
.\backend\.venv\Scripts\python.exe -m pytest backend/tests -v
```

*(Or run `scripts\test_backend.bat`)*

#### Running Specific Test Modules:
```powershell
# API & Endpoints tests:
.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_api_v1.py -v

# Security, JWT, CORS & Rate Limiting tests:
.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_security.py -v

# Machine Learning Ensemble tests:
.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_ensemble.py -v

# Explainable AI (SHAP) tests:
.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_explainability.py -v
```

---

### 2. Frontend Automated Tests (16 Tests)

Run Vitest in the frontend directory:

```powershell
cd frontend
npm run test
```

---

### 3. Frontend Code Quality & Linting

Run Oxlint to verify code standards:

```powershell
cd frontend
npm run lint
```

---

### 4. Frontend Production Build Validation

Compile the production bundle:

```powershell
cd frontend
npm run build
```

---

### 5. End-to-End Workflow Verification

Execute the end-to-end integration test:

```powershell
.\backend\.venv\Scripts\python.exe scripts/test_phase17_e2e.py
```

---

## 23. Comprehensive Troubleshooting Manual

This section documents common operational issues, root causes, and verified solutions.

---

### 1. MongoDB Offline / Unreachable
- **Problem:** Terminal shows `[ERROR] MongoDB connection failed` and backend starts in degraded mode.
- **Cause:** MongoDB service is not started on the host machine.
- **Solution:** Open PowerShell as Administrator and run:
  ```powershell
  Start-Service -Name MongoDB
  ```
- **Verification:** Run `.\backend\.venv\Scripts\python.exe scripts/test_mongo_verification.py`.

---

### 2. MongoDB Connection Refused on Port 27017
- **Problem:** `pymongo.errors.ServerSelectionTimeoutError: connection refused`.
- **Cause:** MongoDB is listening on a different port or firewall blocks port 27017.
- **Solution:** Verify MongoDB configuration file (`mongod.cfg`) port binding is `27017` and `bindIp: 127.0.0.1`.

---

### 3. Backend Fails to Start (ModuleNotFoundError)
- **Problem:** `ModuleNotFoundError: No module named 'fastapi'` or similar.
- **Cause:** Command was executed using global Python instead of `backend/.venv`.
- **Solution:** Use the explicit virtual environment interpreter:
  ```powershell
  .\backend\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
  ```

---

### 4. Python Dependency Missing
- **Problem:** `ModuleNotFoundError: No module named 'reportlab'` or other package.
- **Cause:** New dependency added or incomplete `pip install`.
- **Solution:** Re-run pip install inside the virtual environment:
  ```powershell
  .\backend\.venv\Scripts\pip.exe install -r backend/requirements.txt
  ```

---

### 5. Wrong Python Interpreter Selected in VS Code / IDE
- **Problem:** IDE highlights imports as unresolved.
- **Cause:** IDE is pointing to global Python rather than `backend/.venv`.
- **Solution:** In VS Code, press `Ctrl+Shift+P`, type `Python: Select Interpreter`, and select `.\backend\.venv\Scripts\python.exe`.

---

### 6. backend/.venv Activation Script Disabled on PowerShell
- **Problem:** `File Activate.ps1 cannot be loaded because running scripts is disabled on this system`.
- **Cause:** Windows PowerShell execution policy restriction.
- **Solution:** Run in PowerShell:
  ```powershell
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  .\backend\.venv\Scripts\Activate.ps1
  ```

---

### 7. Frontend Won't Start (Vite Command Not Found)
- **Problem:** `'vite' is not recognized as an internal or external command`.
- **Cause:** `npm install` was not executed in the `frontend` directory.
- **Solution:** Navigate to `frontend` and install dependencies:
  ```powershell
  cd frontend
  npm install
  npm run dev
  ```

---

### 8. npm Dependency Installation Failure
- **Problem:** `npm ERR! code ERESOLVE` or dependency tree conflict.
- **Cause:** Cached npm metadata or conflicting peer dependencies.
- **Solution:** Run clean install:
  ```powershell
  cd frontend
  npm install --legacy-peer-deps
  ```

---

### 9. CORS Policy Rejection (Cross-Origin Request Blocked)
- **Problem:** Browser console displays `CORS header 'Access-Control-Allow-Origin' missing`.
- **Cause:** Frontend is running on a port not listed in `CORS_ORIGINS` in `backend/.env`.
- **Solution:** Ensure `backend/.env` contains `http://localhost:5173` in `CORS_ORIGINS`.

---

### 10. Login Failure (401 Unauthorized / Invalid Credentials)
- **Problem:** Frontend shows "Invalid username or password".
- **Cause:** Database not seeded with initial accounts or incorrect password.
- **Solution:** Re-run the seeding script to create or update default accounts:
  ```powershell
  .\backend\.venv\Scripts\python.exe scripts/seed_users.py --update-passwords --non-interactive
  ```

---

### 11. Frontend Network Error ("Failed to connect to backend")
- **Problem:** Dashboard shows error connecting to `http://localhost:8000`.
- **Cause:** Backend server is not running on port 8000.
- **Solution:** Verify backend terminal is running and reachable at `http://localhost:8000/api/v1/health`.

---

### 12. User Management Inaccessible (403 Forbidden)
- **Problem:** Navigating to `/users` displays Access Denied or redirect.
- **Cause:** Logged-in user has role `ANALYST` or `VIEWER` instead of `ADMIN`.
- **Solution:** Log out and log in with the `admin` account (`Admin12345!`).

---

### 13. Monitoring Inactive / Sniffing Fails to Start
- **Problem:** Starting live monitoring throws error or immediately stops.
- **Cause:** Missing Npcap packet capture driver or insufficient OS privileges.
- **Solution:** Install Npcap (with "WinPcap API-compatible mode" enabled) and run terminal as Administrator. Alternatively, use PCAP Replay Mode.

---

### 14. No Packets Captured During Live Monitoring
- **Problem:** Monitoring runs but packet counter stays at 0.
- **Cause:** Incorrect network adapter selected or no traffic matching filter.
- **Solution:** Set `MONITOR_PACKET_FILTER=""` to capture all traffic or select a specific adapter interface in `/monitoring`.

---

### 15. PCAP File Rejection / Path Traversal Error
- **Problem:** API returns `400 Bad Request: PCAP path outside allowed directory`.
- **Cause:** Security path sanitization blocked access to files outside `data/`.
- **Solution:** Place all `.pcap` files strictly inside `C:\Users\Win\Desktop\ZERO\data\sample\`.

---

### 16. ML Models Not Available (0/4 Loaded)
- **Problem:** Server outputs `ML models available (0/4 loaded)`.
- **Cause:** Pre-trained model weights missing from `ml_models/trained/`.
- **Solution:** Verify that `.joblib` and `.pt` files exist in `ml_models/trained/` or re-run model training scripts:
  ```powershell
  .\backend\.venv\Scripts\python.exe scripts/evaluate_models.py
  ```

---

### 17. Port 8000 or Port 5173 Already in Use
- **Problem:** `[Errno 10048] error while attempting to bind on address ('0.0.0.0', 8000)`.
- **Cause:** Another process or previous backend instance is still running.
- **Solution:** Identify and terminate the blocking process:
  ```powershell
  # Find PID on port 8000:
  Get-NetTCPConnection -LocalPort 8000 | Select-Object OwningProcess
  # Terminate process by PID:
  Stop-Process -Id <PID> -Force
  ```

---

### 18. Environment Variable Missing Error
- **Problem:** Pydantic validation error on application startup.
- **Cause:** `backend/.env` is missing or contains invalid syntax.
- **Solution:** Re-copy `backend/.env.example` to `backend/.env` and verify key-value pairs.

---

### 19. 401 Unauthorized on API Endpoints (JWT Token Expired)
- **Problem:** API returns `401 Unauthorized: Token has expired`.
- **Cause:** Access token exceeded its 60-minute lifetime.
- **Solution:** Refresh your session by logging out and logging back in, or use the automatic refresh token mechanism.

---

### 20. 429 Too Many Requests (Rate Limit Exceeded)
- **Problem:** API returns `429 Too Many Requests`.
- **Cause:** Login rate limit (5 attempts / 60 sec) or general API rate limit triggered.
- **Solution:** Wait 60 seconds for the rate limit window to expire, or increase `API_RATE_LIMIT_DEFAULT_PER_MINUTE` in `backend/.env`.

---

## 24. Common Windows Administration Commands

| Operation | PowerShell / CMD Command |
|:---|:---|
| **Activate venv (PowerShell)** | `.\backend\.venv\Scripts\Activate.ps1` |
| **Activate venv (CMD)** | `backend\.venv\Scripts\activate.bat` |
| **Deactivate venv** | `deactivate` |
| **Check Port 8000 (Backend)** | `Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue` |
| **Check Port 5173 (Frontend)** | `Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue` |
| **Kill Process on Port 8000** | `Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess -Force` |
| **Kill Process on Port 5173** | `Stop-Process -Id (Get-NetTCPConnection -LocalPort 5173).OwningProcess -Force` |
| **Check MongoDB Service Status** | `Get-Service -Name MongoDB` |
| **Start MongoDB Service** | `Start-Service -Name MongoDB` *(Requires Admin)* |
| **Stop MongoDB Service** | `Stop-Service -Name MongoDB` *(Requires Admin)* |
| **Verify Python Binary** | `Get-Command python` |
| **Verify Node Binary** | `Get-Command node` |

---

## 25. Daily Operations: Startup & Orderly Shutdown

### Daily Startup Sequence (5 Steps)

1. **Start MongoDB:**
   ```powershell
   Start-Service -Name MongoDB
   ```
2. **Start Backend API:**
   ```powershell
   cd C:\Users\Win\Desktop\ZERO
   .\backend\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
3. **Start Frontend:**
   ```powershell
   cd C:\Users\Win\Desktop\ZERO\frontend
   npm run dev
   ```
4. **Open Browser:** Navigate to `http://localhost:5173`.
5. **Log In:** Use your assigned RBAC credentials.

---

### Orderly Daily Shutdown Sequence

To avoid corrupted flow buffers or orphan background tasks:

1. **Stop Network Monitoring:** If active, click **Stop Monitoring** in the UI (`/monitoring`).
2. **Stop Frontend:** Press `Ctrl + C` in the Vite terminal.
3. **Stop Backend:** Press `Ctrl + C` in the FastAPI terminal. Lifespan context manager will gracefully close the MongoDB connection pool.
4. **(Optional) Stop MongoDB:** If local server shutdown is desired:
   ```powershell
   Stop-Service -Name MongoDB
   ```

---

## 26. Security Best Practices & Production Hardening

When deploying beyond local development, observe these security requirements:

1. **Rotate JWT Secret Key:** Generate a 64-character random hex string for `JWT_SECRET_KEY`.
2. **Enforce HTTPS / TLS:** Set `STRICT_TRANSPORT_SECURITY_ENABLED=True` and configure an SSL reverse proxy (Nginx / Cloudflare).
3. **Protect MongoDB Credentials:** Never commit `.env` files to Git. Store connection URIs in encrypted secret vaults.
4. **Disable Debug Mode:** Set `DEBUG=False` and `ENVIRONMENT=production` in `backend/.env`.
5. **Restrict CORS Origins:** Remove `*` or localhost origins; only allow authorized corporate domain origins.
6. **Strict Dependency Isolation:** Keep all runtime packages confined to `backend/.venv`.

---

## 27. Known Limitations & Operational Boundaries

1. **Live Capture Driver Dependency:** Live network sniffing requires Npcap on Windows or `libpcap` on Linux with administrative permissions.
2. **Evaluation Metric Proxy:** Detection results on held-out attack datasets represent an experimental proxy for zero-day behavior, not a guarantee against every novel zero-day exploit.
3. **Memory Buffering Bounds:** The in-memory flow aggregator maintains a sliding window buffer capped at 10,000 flows to protect system memory.
4. **Single-Node Deployment:** The default configuration is optimized for single-host development and evaluation. Enterprise multi-gigabit deployments require distributed Kafka ingestion and GPU-accelerated inference workers.

---

*ZeroDayAI Documentation Suite — Built for Enterprise Cyber Resilience & Zero-Day Threat Mitigation.*
