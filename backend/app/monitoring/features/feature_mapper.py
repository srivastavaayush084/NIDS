import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.app.core.config import settings
from backend.app.ml.registry.model_registry import model_registry
from backend.app.monitoring.features.flow_features import FlowFeatures
from backend.app.monitoring.schemas import ModelCompatibilityReport

logger = logging.getLogger(__name__)


class FeatureMapper:
    """
    Transforms FlowFeatures into dataset-aligned feature representations
    compatible with trained ML models and preprocessors.
    """

    @staticmethod
    def map_to_synthetic(flow: FlowFeatures) -> Dict[str, float]:
        """
        Map FlowFeatures to the 26 standard features expected by models trained
        on the synthetic / network traffic dataset.
        """
        proto = flow.protocol.lower()
        service = flow.service.lower()
        flag = flow.tcp_state

        mapped: Dict[str, float] = {
            "src_bytes": float(flow.src_bytes),
            "dst_bytes": float(flow.dst_bytes),
            "count": float(flow.count),
            "srv_count": float(flow.srv_count),
            "serror_rate": float(flow.serror_rate),
            "same_srv_rate": float(flow.same_srv_rate),
            "diff_srv_rate": float(flow.diff_srv_rate),
            "dst_host_count": float(flow.dst_host_count),
            "dst_host_srv_count": float(flow.dst_host_srv_count),
            "feat_byte_ratio": float(flow.byte_ratio),
            "feat_total_bytes": float(flow.total_bytes),
            "feat_src_byte_rate": float(flow.src_byte_rate),
            "feat_packet_ratio": float(flow.packet_ratio),
            # One-hot encoded protocols
            "protocol_type_icmp": 1.0 if proto == "icmp" else 0.0,
            "protocol_type_tcp": 1.0 if proto == "tcp" else 0.0,
            # One-hot encoded services
            "service_eco_i": 1.0 if service in ("eco_i", "icmp") else 0.0,
            "service_ftp": 1.0 if service == "ftp" else 0.0,
            "service_ftp_data": 1.0 if service == "ftp_data" else 0.0,
            "service_http": 1.0 if service == "http" else 0.0,
            "service_private": 1.0 if service == "private" else 0.0,
            "service_smtp": 1.0 if service == "smtp" else 0.0,
            "service_ssl_tls": 1.0 if service in ("ssl_tls", "https") else 0.0,
            "service_telnet": 1.0 if service == "telnet" else 0.0,
            # One-hot encoded TCP flags
            "flag_REJ": 1.0 if flag == "REJ" else 0.0,
            "flag_S0": 1.0 if flag == "S0" else 0.0,
            "flag_SF": 1.0 if flag == "SF" else 0.0,
        }
        return mapped

    @classmethod
    def map_flow(cls, flow: FlowFeatures, dataset_name: str = "synthetic") -> Dict[str, float]:
        """
        Map FlowFeatures into target dataset format.
        """
        ds = dataset_name.lower().strip()
        if ds == "synthetic":
            return cls.map_to_synthetic(flow)
        else:
            # Default fallback mapping
            mapped = cls.map_to_synthetic(flow)
            return mapped

    @classmethod
    def check_model_compatibility(
        cls,
        model_name: str,
        dataset_name: str = "synthetic",
    ) -> ModelCompatibilityReport:
        """
        Evaluate whether the monitoring feature pipeline satisfies the required
        features for a specified model and dataset.
        """
        ds = dataset_name.lower().strip()
        features_path = Path("ml_models/preprocessing") / ds / "selected_features.json"

        required_features: List[str] = []
        if features_path.exists():
            try:
                with open(features_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    required_features = data.get("features", [])
            except Exception as e:
                logger.warning(f"Could not load selected features from {features_path}: {e}")

        # Check against mapped features keys
        dummy_flow = FlowFeatures(
            flow_id="test",
            src_ip="192.168.1.1",
            dst_ip="192.168.1.2",
            src_port=1234,
            dst_port=80,
            protocol="tcp",
            service="http",
            tcp_state="SF",
            duration=0.1,
            src_bytes=100,
            dst_bytes=200,
            src_pkts=2,
            dst_pkts=2,
            total_bytes=300,
            total_pkts=4,
            byte_ratio=0.33,
            packet_ratio=0.5,
            src_byte_rate=1000.0,
            dst_byte_rate=2000.0,
            packet_rate=40.0,
        )
        available_dict = cls.map_flow(dummy_flow, dataset_name=ds)
        available_keys = set(available_dict.keys())

        missing = [f for f in required_features if f not in available_keys]
        total_req = len(required_features) if required_features else len(available_keys)
        avail_count = total_req - len(missing)
        is_compatible = len(missing) == 0

        # Also check model artifact status in registry
        meta = model_registry.get_model(model_name, dataset=ds)
        has_artifact = bool(meta and Path(meta.get("artifact_path", "")).exists()) if model_name != "ensemble" else True

        explanation = (
            f"All {total_req} required features extracted and mapped."
            if is_compatible
            else f"Missing {len(missing)} features: {', '.join(missing[:3])}"
        )
        if not has_artifact and model_name != "ensemble":
            explanation += " (Note: Model artifact not registered/found, but feature mapping is compatible)."

        return ModelCompatibilityReport(
            model_name=model_name,
            compatible=is_compatible,
            available_features=avail_count,
            total_required_features=total_req,
            missing_features=missing,
            explanation=explanation,
        )

    @classmethod
    def get_all_compatibility(cls, dataset_name: str = "synthetic") -> Dict[str, ModelCompatibilityReport]:
        """Check compatibility across all 4 ML models plus the Ensemble Engine."""
        models = ["isolation_forest", "autoencoder", "lstm_autoencoder", "random_forest", "ensemble"]
        return {m: cls.check_model_compatibility(m, dataset_name) for m in models}
