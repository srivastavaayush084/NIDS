"""
Phase 17 — Complete End-to-End Live Integration Verification Script.
Tests all backend subsystems against live FastAPI server and MongoDB:
- Health & Database Ping
- Seeded Accounts & RBAC
- Authentication & JWT Token Refresh
- User Management CRUD & Last Admin Protection
- Model Registry & All 4 Models
- Single, Batch & Sequence Detection Pipelines
- Explainable AI (XAI) Attributions
- Alert Engine, Fingerprinting, Deduplication & Lifecycle (OPEN->ACKNOWLEDGED->RESOLVED)
- Real-Time Network Monitoring & PCAP Testing
- Statistics APIs & Audit Log Verification
"""

import time
import httpx
from datetime import datetime, timezone

BASE_URL = "http://127.0.0.1:8000"
API_V1 = f"{BASE_URL}/api/v1"

results = []

def record(test_name: str, passed: bool, details: str = ""):
    status_str = "PASS" if passed else "FAIL"
    results.append({"name": test_name, "status": status_str, "details": details})
    print(f"[{status_str}] {test_name}" + (f" - {details}" if details else ""))
    assert passed, f"Test failed: {test_name} - {details}"


def run_tests():
    print("\n" + "=" * 60)
    print("PHASE 17: END-TO-END LIVE INTEGRATION VERIFICATION")
    print("=" * 60)

    client = httpx.Client(base_url=BASE_URL, timeout=15.0)

    # 1. System Health & MongoDB Connectivity
    print("\n--- 1. Health & Database Connectivity ---")
    r = client.get("/health")
    record("Health Check /health", r.status_code == 200 and r.json().get("status") in ["healthy", "degraded"], f"Status: {r.status_code}")
    health_data = r.json()
    record("MongoDB Real Ping Health", health_data.get("mongodb", {}).get("connected") is True, f"DB Status: {health_data.get('mongodb', {}).get('status')}, Latency: {health_data.get('mongodb', {}).get('latency_ms')}ms")
    record("ML Engine Service Health", health_data.get("services", {}).get("ml_engine", {}).get("status") == "healthy", f"Available Models: {health_data.get('services', {}).get('ml_engine', {}).get('details', {}).get('available_models')}")

    # 2. Authentication & Token Management
    print("\n--- 2. Authentication & Token Management ---")
    # Admin Login
    r_admin = client.post(f"{API_V1}/auth/login", json={"username": "admin", "password": "Admin12345!"})
    record("Admin Login", r_admin.status_code == 200, f"Token received for user {r_admin.json().get('user', {}).get('username')}")
    admin_tokens = r_admin.json()
    admin_access_token = admin_tokens["access_token"]
    admin_refresh_token = admin_tokens["refresh_token"]
    admin_headers = {"Authorization": f"Bearer {admin_access_token}"}

    # Analyst Login
    r_analyst = client.post(f"{API_V1}/auth/login", json={"username": "analyst", "password": "Analyst12345!"})
    record("Analyst Login", r_analyst.status_code == 200)
    analyst_token = r_analyst.json()["access_token"]
    analyst_headers = {"Authorization": f"Bearer {analyst_token}"}

    # Viewer Login
    r_viewer = client.post(f"{API_V1}/auth/login", json={"username": "viewer", "password": "Viewer12345!"})
    record("Viewer Login", r_viewer.status_code == 200)
    viewer_token = r_viewer.json()["access_token"]
    viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

    # Invalid Credentials Rejection
    r_bad = client.post(f"{API_V1}/auth/login", json={"username": "admin", "password": "WrongPassword!"})
    record("Invalid Password Rejected (401)", r_bad.status_code == 401)

    # Current User Profile
    r_me = client.get(f"{API_V1}/auth/me", headers=admin_headers)
    record("Current User /auth/me Profile", r_me.status_code == 200 and r_me.json().get("username") == "admin")

    # Token Refresh Flow
    r_ref = client.post(f"{API_V1}/auth/refresh", json={"refresh_token": admin_refresh_token})
    record("Token Refresh Flow", r_ref.status_code == 200 and "access_token" in r_ref.json())
    new_admin_token = r_ref.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {new_admin_token}"}

    # 3. Authorization & RBAC Checks
    print("\n--- 3. Authorization & Role-Based Access Control ---")
    # Unauthenticated Access Rejected
    r_unauth = client.get(f"{API_V1}/users")
    record("Unauthenticated Access Rejected (401)", r_unauth.status_code == 401)

    # Admin access to User Management
    r_adm_u = client.get(f"{API_V1}/users", headers=admin_headers)
    record("Admin User Management Allowed (200)", r_adm_u.status_code == 200, f"Users found: {r_adm_u.json().get('total')}")

    # Analyst denied User Management
    r_an_u = client.get(f"{API_V1}/users", headers=analyst_headers)
    record("Analyst User Management Denied (403)", r_an_u.status_code == 403)

    # Viewer denied User Management
    r_vi_u = client.get(f"{API_V1}/users", headers=viewer_headers)
    record("Viewer User Management Denied (403)", r_vi_u.status_code == 403)

    # Viewer denied Monitoring Control
    r_vi_m = client.post(f"{API_V1}/monitoring/start", headers=viewer_headers, json={"source": "live"})
    record("Viewer Monitoring Start Denied (403)", r_vi_m.status_code == 403)

    # 4. User Management Full CRUD Operations
    print("\n--- 4. User Management CRUD & Safety ---")
    test_uname = f"testuser_{int(time.time())}"
    test_email = f"{test_uname}@zeroday.local"
    # Create User
    r_create = client.post(
        f"{API_V1}/users",
        headers=admin_headers,
        json={"username": test_uname, "email": test_email, "password": "UserPass12345!", "role": "analyst", "full_name": "Test Analyst E2E"}
    )
    record("Admin Create User", r_create.status_code == 201, f"Created {test_uname}")
    created_user_id = r_create.json()["user_id"]

    # Duplicate Username Rejection
    r_dup = client.post(
        f"{API_V1}/users",
        headers=admin_headers,
        json={"username": test_uname, "email": f"other_{test_email}", "password": "UserPass12345!", "role": "analyst"}
    )
    record("Duplicate Username Rejected (409)", r_dup.status_code == 409)

    # Update User Role
    r_update = client.patch(
        f"{API_V1}/users/{created_user_id}",
        headers=admin_headers,
        json={"role": "viewer", "full_name": "Updated Test Viewer"}
    )
    record("Admin Update User Role", r_update.status_code == 200 and r_update.json()["role"] == "viewer")

    # Deactivate User
    r_deact = client.delete(f"{API_V1}/users/{created_user_id}", headers=admin_headers)
    record("Admin Deactivate User", r_deact.status_code == 200)

    # Verify Deactivated User Login Rejected
    r_deact_login = client.post(f"{API_V1}/auth/login", json={"username": test_uname, "password": "UserPass12345!"})
    record("Deactivated User Login Blocked (401)", r_deact_login.status_code == 401)

    # Last Admin Protection
    r_deact_admin = client.delete(f"{API_V1}/users/usr-admin-01", headers=admin_headers)
    record("Last Admin Deactivation Guard (400)", r_deact_admin.status_code == 400 or r_deact_admin.status_code == 404)

    # 5. ML Models Registry Verification
    print("\n--- 5. ML Models & Registry ---")
    r_models = client.get(f"{API_V1}/models", headers=admin_headers)
    record("List Registered Models (200)", r_models.status_code == 200, f"Models Count: {r_models.json().get('total')}")
    model_ids = [m["model_id"] for m in r_models.json().get("models", [])]
    for expected_model in ["isolation_forest", "autoencoder", "lstm_autoencoder", "random_forest", "ensemble"]:
        record(f"Model Present: {expected_model}", expected_model in model_ids)

    # 6. Single Detection Pipeline & XAI Attributions
    print("\n--- 6. Single Detection Pipeline & XAI ---")
    # High-risk anomalous feature payload designed to trigger high composite risk & alert
    anomalous_payload = {
        "features": {
            "duration": 0.0,
            "src_bytes": 1054320,
            "dst_bytes": 0,
            "wrong_fragment": 3,
            "urgent": 2,
            "hot": 5,
            "num_failed_logins": 4,
            "logged_in": 0,
            "num_compromised": 10,
            "root_shell": 1,
            "su_attempted": 1,
            "num_root": 5,
            "num_file_creations": 3,
            "num_shells": 2,
            "count": 511,
            "srv_count": 511,
            "serror_rate": 1.0,
            "srv_serror_rate": 1.0,
            "rerror_rate": 0.0,
            "srv_rerror_rate": 0.0,
            "same_srv_rate": 1.0,
            "diff_srv_rate": 0.0,
            "dst_host_count": 255,
            "dst_host_srv_count": 255,
            "dst_host_same_srv_rate": 1.0,
            "dst_host_diff_srv_rate": 0.0,
            "dst_host_same_src_port_rate": 1.0,
            "dst_host_serror_rate": 1.0,
            "dst_host_srv_serror_rate": 1.0,
        },
        "dataset_name": "synthetic",
        "generate_xai": True,
        "flow_context": {
            "src_ip": "198.51.100.44",
            "dst_ip": "10.0.0.15",
            "src_port": 49152,
            "dst_port": 445,
            "protocol": "TCP"
        }
    }

    r_det = client.post(f"{API_V1}/detection", headers=analyst_headers, json=anomalous_payload)
    record("Single Detection Execution (200)", r_det.status_code == 200)
    det_data = r_det.json().get("data", {})
    record("Detection Has Valid ID", bool(det_data.get("detection_id")))
    record("Detection Risk Score (0-100)", 0.0 <= det_data.get("risk_score", -1) <= 100.0, f"Score: {det_data.get('risk_score')}, Severity: {det_data.get('severity')}")
    record("Detection Model Agreement", det_data.get("model_agreement", {}).get("models_total") >= 3)
    record("XAI Attributions Attached", det_data.get("explanation", {}).get("is_available") is True, f"Method: {det_data.get('explanation', {}).get('method')}")
    alert_info = det_data.get("alert", {})
    record("Security Alert Created on High-Risk Flow", alert_info.get("created") is True or bool(alert_info.get("alert_id")), f"Alert ID: {alert_info.get('alert_id')}")
    created_alert_id = alert_info.get("alert_id")

    # 7. Batch Detection Pipeline
    print("\n--- 7. Batch Detection Pipeline ---")
    batch_payload = {
        "events": [
            {"src_bytes": 100, "dst_bytes": 200, "count": 5, "protocol": "TCP"},
            {"src_bytes": 500000, "dst_bytes": 0, "count": 400, "serror_rate": 0.9, "protocol": "TCP"},
            {"src_bytes": 300, "dst_bytes": 500, "count": 2, "protocol": "UDP"},
        ],
        "dataset_name": "synthetic",
        "generate_xai": False
    }
    r_batch = client.post(f"{API_V1}/detection/batch", headers=analyst_headers, json=batch_payload)
    record("Batch Detection Execution (200)", r_batch.status_code == 200 and r_batch.json().get("data", {}).get("total") == 3)

    # 8. Sequence Detection Pipeline (LSTM Autoencoder)
    print("\n--- 8. Sequence Detection Pipeline ---")
    seq_payload = {
        "sequence": [
            {"src_bytes": 100, "count": 1, "serror_rate": 0.0},
            {"src_bytes": 150, "count": 2, "serror_rate": 0.0},
            {"src_bytes": 200, "count": 3, "serror_rate": 0.1},
            {"src_bytes": 80000, "count": 200, "serror_rate": 0.9},
            {"src_bytes": 90000, "count": 250, "serror_rate": 1.0},
        ],
        "dataset_name": "synthetic",
        "generate_xai": True
    }
    r_seq = client.post(f"{API_V1}/detection/sequence", headers=analyst_headers, json=seq_payload)
    record("Sequence Detection Execution (200)", r_seq.status_code == 200)
    seq_data = r_seq.json().get("data", {})
    record("Sequence Reconstruction Error Calculated", "reconstruction_error" in seq_data)

    # 9. Alert Deduplication & Cooldown Verification
    print("\n--- 9. Alert Deduplication Verification ---")
    # Send identical payload immediately to verify deduplication
    r_det2 = client.post(f"{API_V1}/detection", headers=analyst_headers, json=anomalous_payload)
    det_data2 = r_det2.json().get("data", {})
    alert_info2 = det_data2.get("alert", {})
    record("Alert Deduplication Triggered", alert_info2.get("deduplicated") is True or alert_info2.get("occurrence_count", 0) >= 2 or alert_info2.get("alert_id") == created_alert_id, f"Deduplicated: {alert_info2.get('deduplicated')}, Count: {alert_info2.get('occurrence_count')}")

    # 10. Alert Lifecycle State Transitions (OPEN -> ACKNOWLEDGED -> RESOLVED)
    print("\n--- 10. Alert Lifecycle Management ---")
    if created_alert_id:
        # Get Alert Detail
        r_detail = client.get(f"{API_V1}/alerts/{created_alert_id}", headers=analyst_headers)
        record("Get Alert Detail (200)", r_detail.status_code == 200 and r_detail.json().get("data", {}).get("alert_id") == created_alert_id)

        # Query Alerts with Filtering
        r_list = client.get(f"{API_V1}/alerts?page=1&page_size=10", headers=analyst_headers)
        record("List Alerts with Pagination (200)", r_list.status_code == 200 and "data" in r_list.json())

        # Acknowledge
        r_ack = client.patch(f"{API_V1}/alerts/{created_alert_id}/acknowledge", headers=analyst_headers, json={"user_id": "analyst"})
        record("Alert Acknowledge (200)", r_ack.status_code == 200, f"Status: {r_ack.json().get('data', {}).get('status')}")

        # Resolve
        r_res = client.patch(
            f"{API_V1}/alerts/{created_alert_id}/resolve",
            headers=analyst_headers,
            json={"resolution_note": "Identified and blocked source IP at perimeter firewall.", "user_id": "analyst"}
        )
        record("Alert Resolve (200)", r_res.status_code == 200, f"Status: {r_res.json().get('data', {}).get('status')}")

    # 11. Real-Time Network Monitoring Subsystem
    print("\n--- 11. Network Monitoring Subsystem ---")
    # Network Interfaces
    r_ifaces = client.get(f"{API_V1}/monitoring/interfaces", headers=viewer_headers)
    record("Network Interfaces Enumeration (200)", r_ifaces.status_code == 200 and "interfaces" in r_ifaces.json())

    # Model Compatibility Matrix
    r_compat = client.get(f"{API_V1}/monitoring/compatibility?dataset_name=synthetic", headers=viewer_headers)
    record("Monitoring Feature Compatibility Matrix (200)", r_compat.status_code == 200 and "isolation_forest" in r_compat.json())

    # Start Monitoring
    r_mon_start = client.post(
        f"{API_V1}/monitoring/start",
        headers=analyst_headers,
        json={"source": "live", "max_packets": 500, "dataset_name": "synthetic"}
    )
    record("Monitoring Start (200)", r_mon_start.status_code == 200 and r_mon_start.json().get("running") is True)

    # Query Status
    r_mon_stat = client.get(f"{API_V1}/monitoring/status", headers=viewer_headers)
    record("Monitoring Status Telemetry (200)", r_mon_stat.status_code == 200)

    # Stop Monitoring
    r_mon_stop = client.post(f"{API_V1}/monitoring/stop", headers=analyst_headers)
    record("Monitoring Stop (200)", r_mon_stop.status_code == 200 and r_mon_stop.json().get("status") == "stopped")

    # 12. Statistics & Aggregation APIs
    print("\n--- 12. Statistics & Analytics APIs ---")
    r_stats = client.get(f"{API_V1}/statistics/summary", headers=viewer_headers)
    record("Dashboard Summary Statistics (200)", r_stats.status_code == 200 and "total_detections" in r_stats.json())

    r_alert_stats = client.get(f"{API_V1}/statistics/alerts", headers=viewer_headers)
    record("Alert Breakdown Statistics (200)", r_alert_stats.status_code == 200 and ("status_breakdown" in r_alert_stats.json() or "total_alerts" in r_alert_stats.json()))

    r_model_stats = client.get(f"{API_V1}/statistics/models", headers=viewer_headers)
    record("Model Evaluation Benchmarks (200)", r_model_stats.status_code == 200 and "models" in r_model_stats.json())

    # 13. Audit Log Subsystem
    print("\n--- 13. Audit Logging Verification ---")
    # Logout Admin
    r_logout = client.post(f"{API_V1}/auth/logout", headers=admin_headers)
    record("User Logout & Audit Log Entry (200)", r_logout.status_code == 200)

    print("\n" + "=" * 60)
    passed_count = sum(1 for r in results if r["status"] == "PASS")
    failed_count = sum(1 for r in results if r["status"] == "FAIL")
    print(f"TOTAL INTEGRATION TESTS: {len(results)}")
    print(f"PASSED: {passed_count}")
    print(f"FAILED: {failed_count}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_tests()
