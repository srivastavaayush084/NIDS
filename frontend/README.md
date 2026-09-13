# ZERO AI NIDS — Security Operations Center (SOC) Frontend Dashboard

A professional, responsive React-based Security Operations Center (SOC) dashboard for the AI-Based Zero-Day Attack Detection System.

---

## Architecture & Directory Structure

```text
frontend/src/
├── api/
│   ├── client.js          # Central HTTP fetch client with timeout & error normalization
│   ├── health.js          # /api/v1/health endpoints
│   ├── statistics.js      # /api/v1/statistics endpoints (KPIs, alert distributions)
│   ├── alerts.js          # /api/v1/alerts endpoints (queries & lifecycle mutations)
│   ├── detection.js       # /api/v1/detection endpoints (history, single, batch)
│   ├── models.js          # /api/v1/models endpoints (registry & comparison)
│   ├── monitoring.js      # /api/v1/monitoring endpoints (telemetry & controls)
│   └── index.js           # Public API exports
│
├── hooks/
│   ├── useHealth.js       # System health polling
│   ├── useStatistics.js   # Dashboard summary KPIs polling
│   ├── useAlerts.js       # Alerts query, filtering, and action mutations
│   ├── useDetection.js    # Detection history query
│   ├── useModels.js       # Model registry & comparison metrics
│   └── useMonitoring.js   # Live telemetry polling & capture session controls
│
├── components/
│   ├── common/            # SeverityBadge, RiskScore, StatusPill, Card, Modal, Pagination, etc.
│   ├── charts/            # AlertTrendChart, SeverityDistributionChart, ModelComparisonChart, ThroughputChart
│   ├── dashboard/         # KPICards, MonitoringCard, RecentAlertsTable, ModelOverviewGrid
│   ├── alerts/            # AlertsTable, AlertFilters, AlertActionModal
│   ├── monitoring/        # MonitoringControls, MonitoringLiveFeed, PCAPTestRunner, ModelCompatibilityMatrix
│   ├── models/            # ModelCard, ModelComparisonTable
│   ├── health/            # SystemHealthGrid
│   └── xai/               # XAIExplanationView (Feature attributions & explanations)
│
├── pages/
│   ├── Dashboard.jsx      # /dashboard (and /) - Main SOC overview
│   ├── Monitoring.jsx     # /monitoring - Live traffic ingestion & PCAP benchmark inspector
│   ├── Alerts.jsx         # /alerts - Security incident triage & filtering
│   ├── AlertDetails.jsx   # /alerts/:alertId - Full alert investigation & lifecycle actions
│   ├── DetectionHistory.jsx # /detections - Historical evaluated network events
│   ├── DetectionDetails.jsx # /detections/:detectionId - Single flow detection & XAI breakdown
│   ├── Models.jsx         # /models - AI model registry & benchmark comparison
│   ├── SystemHealth.jsx   # /health - API, DB, models, and monitoring diagnostics
│   └── NotFound.jsx       # 404 fallback page
│
├── layouts/
│   ├── MainLayout.jsx     # Main layout wrapper with responsive drawer
│   ├── Sidebar.jsx        # Left navigation with route links & badges
│   └── Navbar.jsx         # Top telemetry bar, status pills & manual refresh
│
└── App.jsx                # Top-level Router configuration
```

---

## Routes & Pages

| Route | Page | Purpose |
|---|---|---|
| `/` | `Navigate -> /dashboard` | Redirects to default dashboard view |
| `/dashboard` | `Dashboard` | Real-time SOC overview, KPIs, threat distributions, model health, recent alerts |
| `/monitoring` | `Monitoring` | Live traffic ingestion telemetry, capture session controls, live feed, PCAP benchmark runner |
| `/alerts` | `Alerts` | Incident triage table with backend filtering, search, pagination, and status actions |
| `/alerts/:alertId` | `AlertDetails` | Full investigation view: 5-tuples, model evidence, XAI attributions, action modals |
| `/detections` | `DetectionHistory` | Paginated audit log of evaluated network events |
| `/detections/:detectionId` | `DetectionDetails` | Single detection inspection with raw features, model scores, XAI, and alert links |
| `/models` | `Models` | Model registry cards and comparison matrix (Standard vs Zero-Day Proxy) |
| `/health` | `SystemHealth` | Subsystem diagnostics (FastAPI, MongoDB, 5 ML Models, Monitoring Driver) |
| `*` | `NotFound` | Clean 404 page with return to dashboard navigation |

---

## Environment Configuration

Create a `.env` file in `frontend/` (see `.env.example`):

```bash
# API Base URL for Zero-Day NIDS Backend
VITE_API_BASE_URL=http://localhost:8000

# Telemetry and Status Polling Interval (in milliseconds)
VITE_POLLING_INTERVAL_MS=5000
```

---

## Development & Build Commands

```bash
# Install dependencies
npm install

# Start local development server
npm run dev

# Run unit and integration tests
npm test

# Run code linter
npm run lint

# Compile production bundle
npm run build
```
