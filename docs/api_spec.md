# ZeroDayAI - REST API Specification

## Base URL
- **Local Development**: `http://localhost:8000`
- **Prefix**: `/api/v1` (with `/api/health` available directly)

---

## Endpoints

### 1. System Health
- **`GET /api/health`** (or `GET /api/v1/health`)
  - **Description**: Returns live subsystem health (API, MongoDB, ML Engine).
  - **Response Sample**:
    ```json
    {
      "status": "healthy",
      "version": "1.0.0",
      "timestamp": "2026-09-08T01:45:00.000000Z",
      "environment": "development",
      "services": {
        "api": { "status": "healthy" },
        "database": { "status": "disconnected" },
        "ml_engine": { "status": "initialized" }
      }
    }
    ```

### 2. Network Flow Detection
- **`POST /api/v1/detection/analyze`**
  - **Description**: Evaluates single packet/flow feature payload.
  - **Request Body**:
    ```json
    {
      "flow": {
        "src_ip": "192.168.1.100",
        "dst_ip": "10.0.0.5",
        "src_port": 49210,
        "dst_port": 443,
        "protocol": "TCP",
        "duration": 0.45,
        "src_bytes": 1024,
        "dst_bytes": 4096,
        "packet_count": 12
      },
      "active_models": ["isolation_forest", "autoencoder", "lstm", "random_forest"]
    }
    ```

- **`POST /api/v1/detection/analyze/batch`**
  - **Description**: Evaluates batch list of network flows.

### 3. Security Incident Alerts
- **`GET /api/v1/alerts?limit=50&skip=0`**
  - **Description**: Lists paginated security alerts.
- **`POST /api/v1/alerts`**
  - **Description**: Dispatches manual or external incident alert.

### 4. Traffic Ingestion
- **`POST /api/v1/traffic/ingest`**
  - **Description**: Ingests flow packet batches from live tap or replay scripts.

### 5. AI Models Registry
- **`GET /api/v1/models`**
  - **Description**: Lists registered AI/ML models with training and metric status.
