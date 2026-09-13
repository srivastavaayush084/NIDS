# ZeroDayAI REST API Reference (v1.0.0)

The **AI-Based Zero-Day Attack Detection System** exposes a high-performance, asynchronous REST API layer under the `/api/v1` namespace. This document provides complete operational details, parameter specifications, schema structures, status codes, and example payloads.

---

## Centralized Architecture & Headers

All API responses conform to standardized JSON envelopes with automatic correlation and latency tracking:

- **Correlation ID Header**: `X-Request-ID` (e.g. `req-3a51eeb3a410`)
- **Execution Timing Header**: `X-Process-Time` (e.g. `12.45ms`)

### Standard Response Envelopes

#### 1. Success Envelope
```json
{
  "success": true,
  "data": { ... },
  "message": "Optional operational note",
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 142,
    "total_pages": 8
  }
}
```

#### 2. Centralized Error Envelope
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request payload validation failed.",
    "details": [
      {
        "location": "body -> destination_port",
        "message": "Input should be less than or equal to 65535",
        "type": "less_than_equal"
      }
    ],
    "request_id": "req-3a51eeb3a410"
  }
}
```

---

## API Endpoints Directory

| Category | Method | Path | Summary |
| :--- | :--- | :--- | :--- |
| **Health** | `GET` | `/api/v1/health` | Comprehensive health check with DB latency & ML availability |
| **Health** | `GET` | `/api/health`, `/health` | Root & legacy health aliases |
| **Events** | `POST` | `/api/v1/events` | Ingest and store single network flow record |
| **Events** | `POST` | `/api/v1/events/batch` | Bulk event flow ingestion (up to 500 events) |
| **Detection**| `POST` | `/api/v1/detection` | End-to-end multi-model inference, XAI, and alert generation |
| **Detection**| `POST` | `/api/v1/detection/batch` | High-throughput batch inference across flow records |
| **Detection**| `POST` | `/api/v1/detection/sequence`| Sequential time-series anomaly detection (LSTM Autoencoder) |
| **Detection**| `GET` | `/api/v1/detection` | Query paginated detection history with multi-tier filters |
| **Detection**| `GET` | `/api/v1/detection/{detection_id}` | Retrieve full detection record, XAI attributions, and alert refs |
| **Alerts** | `GET` | `/api/v1/alerts` | List security incident alerts with pagination & filtering |
| **Alerts** | `GET` | `/api/v1/alerts/{alert_id}` | Retrieve detailed incident document with multi-model evidence |
| **Alerts** | `PATCH`| `/api/v1/alerts/{alert_id}/acknowledge` | Acknowledge alert (`OPEN` &rarr; `ACKNOWLEDGED`) |
| **Alerts** | `PATCH`| `/api/v1/alerts/{alert_id}/resolve` | Resolve alert (`RESOLVED`) with mandatory incident note |
| **Alerts** | `PATCH`| `/api/v1/alerts/{alert_id}/dismiss` | Dismiss alert (`DISMISSED`) with false-positive / policy justification |
| **Models** | `GET` | `/api/v1/models` | List all registered ML models with operational status & safe metadata |
| **Models** | `GET` | `/api/v1/models/{model_name}` | Retrieve architecture, hyperparameters, and calibrated thresholds |
| **Statistics**| `GET`| `/api/v1/statistics/summary` | Real-time aggregate telemetry for SOC dashboards |
| **Statistics**| `GET`| `/api/v1/statistics/alerts` | Alert distributions, severity breakdown, and top target IPs |
| **Statistics**| `GET`| `/api/v1/statistics/models` | Benchmark evaluation metrics (Known attacks vs. Zero-days) |

---

## Detailed Endpoint Specifications

### 1. Health Probe (`GET /api/v1/health`)
Returns deep subsystem readiness, live MongoDB round-trip latency, and model availability.

#### Response (`200 OK`)
```json
{
  "status": "healthy",
  "database": "connected",
  "environment": "development",
  "version": "1.0.0",
  "timestamp": "2026-09-08T13:50:00.000Z",
  "services": {
    "api": { "status": "healthy", "details": { "latency_ms": 0.1 } },
    "database": { "status": "healthy", "details": { "connected": true, "latency_ms": 2.1 } },
    "ml_engine": {
      "status": "healthy",
      "details": {
        "available_models": 4,
        "models": {
          "isolation_forest": "available",
          "autoencoder": "available",
          "lstm_autoencoder": "available",
          "random_forest": "available",
          "ensemble": "available"
        }
      }
    }
  }
}
```

---

### 2. Network Event Ingestion (`POST /api/v1/events`)
Validates and persists network flow headers and engineered features without executing CPU-intensive ML detection.

#### Request Body
```json
{
  "source_ip": "192.168.1.50",
  "destination_ip": "10.0.0.1",
  "source_port": 54321,
  "destination_port": 80,
  "protocol": "TCP",
  "dataset_name": "synthetic",
  "features": {
    "src_bytes": 150.0,
    "dst_bytes": 350.0,
    "count": 5.0,
    "srv_count": 5.0,
    "serror_rate": 0.0,
    "same_srv_rate": 1.0,
    "diff_srv_rate": 0.0,
    "dst_host_count": 10.0,
    "dst_host_srv_count": 10.0
  }
}
```

#### Response (`201 Created`)
```json
{
  "success": true,
  "data": {
    "event_id": "evt-7a91bf33c102",
    "timestamp": "2026-09-08T13:50:00.000Z",
    "status": "stored",
    "dataset_name": "synthetic",
    "source_ip": "192.168.1.50",
    "destination_ip": "10.0.0.1"
  }
}
```

---

### 3. Single Event Detection (`POST /api/v1/detection`)
Full end-to-end detection pipeline executing Isolation Forest, Deep Autoencoder, Random Forest, and Ensemble Scoring with integrated Explainable AI (XAI) and Alert Engine triggers.

#### Request Body
```json
{
  "features": {
    "src_bytes": 50000.0,
    "dst_bytes": 0.0,
    "count": 500.0,
    "srv_count": 500.0,
    "serror_rate": 1.0,
    "same_srv_rate": 1.0,
    "diff_srv_rate": 0.0,
    "dst_host_count": 255.0,
    "dst_host_srv_count": 1.0,
    "feat_byte_ratio": 50000.0,
    "feat_total_bytes": 50000.0,
    "feat_src_byte_rate": 10000.0,
    "feat_packet_ratio": 0.01,
    "protocol_type_icmp": 0.0,
    "protocol_type_tcp": 1.0,
    "service_eco_i": 0.0,
    "service_ftp": 0.0,
    "service_ftp_data": 0.0,
    "service_http": 0.0,
    "service_private": 1.0,
    "service_smtp": 0.0,
    "service_ssl_tls": 0.0,
    "service_telnet": 0.0,
    "flag_REJ": 0.0,
    "flag_S0": 1.0,
    "flag_SF": 0.0
  },
  "dataset_name": "synthetic",
  "generate_xai": true,
  "flow_context": {
    "source_ip": "198.51.100.25",
    "destination_ip": "10.0.0.15",
    "source_port": 54321,
    "destination_port": 443,
    "protocol": "TCP"
  }
}
```

#### Response (`200 OK`)
```json
{
  "success": true,
  "data": {
    "detection_id": "det-e3b91c841a02",
    "timestamp": "2026-09-08T13:50:00.000Z",
    "dataset_name": "synthetic",
    "prediction": "attack",
    "is_anomaly": true,
    "risk_score": 94.25,
    "severity": "CRITICAL",
    "threshold": 50.0,
    "model_agreement": {
      "models_total": 4,
      "models_available": 3,
      "models_anomalous": 3,
      "models_normal": 0,
      "agreement_ratio": 1.0,
      "consensus_prediction": "attack"
    },
    "models": [
      {
        "name": "isolation_forest",
        "prediction": "attack",
        "is_anomaly": true,
        "native_score": -0.32,
        "normalized_score": 88.5,
        "weight": 0.33,
        "weighted_contribution": 29.2,
        "latency_ms": 1.45,
        "is_available": true
      },
      {
        "name": "autoencoder",
        "prediction": "attack",
        "is_anomaly": true,
        "native_score": 4.12,
        "normalized_score": 96.0,
        "weight": 0.33,
        "weighted_contribution": 31.68,
        "latency_ms": 2.10,
        "is_available": true
      },
      {
        "name": "random_forest",
        "prediction": "attack",
        "is_anomaly": true,
        "native_score": 0.98,
        "normalized_score": 98.2,
        "weight": 0.34,
        "weighted_contribution": 33.38,
        "latency_ms": 0.95,
        "is_available": true
      }
    ],
    "explanation": {
      "is_available": true,
      "explanation_id": "exp-9f1230489",
      "method": "ensemble_risk_attribution",
      "summary": "Primary risk drivers: serror_rate (+0.38), src_bytes (+0.29), flag_S0 (+0.21)",
      "top_features": [
        { "feature_name": "serror_rate", "importance": 0.38, "description": "High SYN error rate indicates connection aborts" },
        { "feature_name": "src_bytes", "importance": 0.29, "description": "Abnormal forward volume burst" }
      ]
    },
    "alert": {
      "created": true,
      "alert_id": "alt-017d8ddf20f2",
      "severity": "CRITICAL",
      "priority": "URGENT",
      "deduplicated": false,
      "occurrence_count": 1
    },
    "flow_context": {
      "source_ip": "198.51.100.25",
      "destination_ip": "10.0.0.15"
    },
    "processing_time_ms": 12.45
  }
}
```

---

### 4. Alert Lifecycle Management

#### Acknowledge Alert (`PATCH /api/v1/alerts/{alert_id}/acknowledge`)
Transitions an incident from `OPEN` to `ACKNOWLEDGED`.

```json
// Request
{
  "user_id": "lead_soc_analyst"
}

// Response (200 OK)
{
  "success": true,
  "data": {
    "alert_id": "alt-017d8ddf20f2",
    "status": "ACKNOWLEDGED",
    "assigned_to": "lead_soc_analyst",
    "updated_at": "2026-09-08T13:51:00.000Z"
  },
  "message": "Alert 'alt-017d8ddf20f2' acknowledged by lead_soc_analyst."
}
```

#### Resolve Alert (`PATCH /api/v1/alerts/{alert_id}/resolve`)
Closes an incident into `RESOLVED` with mandatory audit commentary.

```json
// Request
{
  "resolution_note": "Host 198.51.100.25 quarantined via EDR. Malicious beaconing terminated.",
  "user_id": "lead_soc_analyst"
}

// Response (200 OK)
{
  "success": true,
  "data": {
    "alert_id": "alt-017d8ddf20f2",
    "status": "RESOLVED",
    "resolution_note": "Host 198.51.100.25 quarantined via EDR. Malicious beaconing terminated."
  }
}
```

#### State Transition Guards (`409 Conflict`)
Attempting to acknowledge or re-resolve an already `RESOLVED` or `DISMISSED` alert immediately rejects with `409 Conflict`:
```json
{
  "success": false,
  "error": {
    "code": "HTTP_409",
    "message": "Cannot acknowledge alert 'alt-017d8ddf20f2' because it is already in terminal state 'RESOLVED'."
  }
}
```

---

### 5. System & Dashboard Statistics (`GET /api/v1/statistics/summary`)
Returns aggregated telemetry formatted directly for real-time React dashboards and SOC wallboards.

#### Response (`200 OK`)
```json
{
  "total_detections": 15420,
  "total_anomalies": 328,
  "anomaly_rate": 2.13,
  "total_alerts": 42,
  "alerts_by_status": {
    "OPEN": 12,
    "ACKNOWLEDGED": 18,
    "RESOLVED": 10,
    "DISMISSED": 2
  },
  "alerts_by_severity": {
    "CRITICAL": 5,
    "HIGH": 14,
    "MEDIUM": 18,
    "LOW": 5
  },
  "average_risk_score": 14.85,
  "active_models_count": 4,
  "last_detection_time": "2026-09-08T13:54:10.000Z"
}
```
