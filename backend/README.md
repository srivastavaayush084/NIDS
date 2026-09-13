# ZeroDayAI - Backend Service & Database Layer

FastAPI-powered asynchronous backend and AI detection engine with MongoDB persistence for Zero-Day Network Anomaly Detection.

---

## 🐍 Virtual Environment Requirement

All Python execution **MUST** use the dedicated virtual environment `.venv`.

### Windows Activation
```powershell
.\.venv\Scripts\activate
```

---

## 🛠️ Setup & Installation

1. **Create virtual environment** (if not already present):
   ```powershell
   python -m venv .venv
   ```

2. **Activate virtual environment**:
   ```powershell
   .\.venv\Scripts\activate
   ```

3. **Upgrade pip and install dependencies**:
   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

---

## 🗄️ Database Architecture (MongoDB)

The backend uses **Motor** for non-blocking asynchronous MongoDB operations, organized as follows:

```
backend/app/database/
├── connection.py   # Connection pool lifecycle, health probes & graceful shutdown
├── client.py       # Singleton MongoClientManager holder
├── collections.py  # Centralized collection name constants
├── indexes.py      # Automated async index verification & creation
├── repository.py   # Generic BaseRepository & specialized domain repositories
└── mongodb.py      # Backward-compatibility accessor bridge
```

### Managed Collections
1. **`users`**: System operators and analysts with unique usernames/emails and RBAC roles.
2. **`network_logs`**: Ingested network packet flow records, metrics, and feature vectors.
3. **`detection_results`**: Model prediction outputs, anomaly scores, and explainability attributions.
4. **`alerts`**: Security incident alarms with severity and lifecycle statuses (`new`, `acknowledged`, `resolved`, `dismissed`).
5. **`system_events`**: Application lifecycle and operational audit events (`APP_STARTUP`, `DB_CONNECTED`, etc.).
6. **`audit_logs`**: Compliance and administrative audit trails.

---

## ⚙️ Environment Variables

Copy `.env.example` to `.env` in the backend or project root:

```env
PROJECT_NAME="ZeroDayAI - Zero-Day Attack Detection Platform"
ENVIRONMENT=development
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000
FRONTEND_URL="http://localhost:5173"
CORS_ORIGINS="http://localhost:3000,http://localhost:5173"
MONGODB_URI="mongodb://localhost:27017"
MONGODB_DATABASE="zero_day_detection"
```

---

## 🚀 Running the Backend

From the project root:
```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
Or execute:
```powershell
.\scripts\start_backend.bat
```

---

## 📡 API Endpoints

- **Health Probe**: `GET /api/health`
- **Database Status**: `GET /api/v1/database/status`
- **Interactive Documentation**: `GET /docs` (Swagger UI)
- **ML Models Registry**: `GET /api/v1/models`
- **Detection Engine**: `POST /api/v1/detection/analyze`
- **Security Alerts**: `GET /api/v1/alerts`
- **Traffic Ingestion**: `POST /api/v1/traffic/ingest`

---

## 🧪 Running Automated Tests

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend/tests -v
```
Or execute:
```powershell
.\scripts\test_backend.bat
```
