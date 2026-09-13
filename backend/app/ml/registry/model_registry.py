import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ml.data.utils.data_utils import ensure_dir, save_metadata, load_metadata


class ModelRegistry:
    """
    Centralized Model Registry managing trained model artifacts, schemas,
    hyperparameters, versions, and deployment statuses across the ZeroDayAI platform.
    """

    def __init__(self, registry_file: Optional[Union[str, Path]] = None):
        self.registry_file = (
            Path(registry_file)
            if registry_file
            else settings.BASE_DIR / "ml_models" / "model_registry.json"
        )
        self.models_dir = settings.MODELS_DIR
        ensure_dir(self.registry_file.parent)
        ensure_dir(self.models_dir)

    def _load_registry_data(self) -> Dict[str, Any]:
        """Load or initialize model registry dictionary from disk."""
        if not self.registry_file.exists():
            default_data = {
                "version": "1.0.0",
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "models": {}
            }
            save_metadata(default_data, self.registry_file)
            return default_data
        try:
            return load_metadata(self.registry_file)
        except Exception as e:
            logger.warning(f"Could not load registry file, creating new one: {e}")
            return {"version": "1.0.0", "updated_at": datetime.now(timezone.utc).isoformat(), "models": {}}

    def _save_registry_data(self, data: Dict[str, Any]) -> None:
        """Save registry dictionary to disk."""
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        save_metadata(data, self.registry_file)

    def register_model(
        self,
        model_name: str,
        dataset: str,
        version: str,
        artifact_path: Union[str, Path],
        model_type: str = "unsupervised_anomaly_detector",
        feature_count: int = 0,
        feature_names: Optional[List[str]] = None,
        preprocessing_dir: Optional[Union[str, Path]] = None,
        hyperparameters: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        training_samples: int = 0,
        set_active: bool = True,
    ) -> Dict[str, Any]:
        """
        Register a newly trained model artifact and its metadata into the registry.
        """
        registry = self._load_registry_data()
        model_key = f"{model_name.lower()}_{dataset.lower()}_v{version}"
        
        entry = {
            "model_key": model_key,
            "model_name": model_name.lower(),
            "model_type": model_type,
            "dataset": dataset.lower(),
            "version": version,
            "artifact_path": str(artifact_path),
            "preprocessing_dir": str(preprocessing_dir) if preprocessing_dir else "",
            "feature_count": feature_count,
            "feature_names": feature_names or [],
            "hyperparameters": hyperparameters or {},
            "metrics": metrics or {},
            "training_samples": training_samples,
            "is_active": set_active,
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }

        # If setting active, deactivate existing models for this (model_name, dataset) pair
        if set_active:
            for k, m in registry.get("models", {}).items():
                if m.get("model_name") == model_name.lower() and m.get("dataset") == dataset.lower():
                    m["is_active"] = False

        if "models" not in registry:
            registry["models"] = {}

        registry["models"][model_key] = entry
        self._save_registry_data(registry)
        logger.info(f"Registered model in registry: {model_key} (active={set_active})")
        return entry

    def _resolve_entry_paths(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Dynamically resolve model artifact and preprocessing paths on the current host."""
        entry_copy = dict(entry)
        raw_art = entry_copy.get("artifact_path", "")
        if raw_art:
            art_path = Path(raw_art)
            if art_path.exists():
                entry_copy["artifact_path"] = str(art_path.resolve())
            elif (settings.BASE_DIR / raw_art).exists():
                entry_copy["artifact_path"] = str((settings.BASE_DIR / raw_art).resolve())
            elif (settings.MODELS_DIR / art_path.name).exists():
                entry_copy["artifact_path"] = str((settings.MODELS_DIR / art_path.name).resolve())
            elif (settings.BASE_DIR / "ml_models" / "trained" / art_path.name).exists():
                entry_copy["artifact_path"] = str((settings.BASE_DIR / "ml_models" / "trained" / art_path.name).resolve())

        raw_prep = entry_copy.get("preprocessing_dir", "")
        if raw_prep:
            prep_path = Path(raw_prep)
            if prep_path.exists():
                entry_copy["preprocessing_dir"] = str(prep_path.resolve())
            elif (settings.BASE_DIR / raw_prep).exists():
                entry_copy["preprocessing_dir"] = str((settings.BASE_DIR / raw_prep).resolve())
            elif prep_path.name and (settings.PREPROCESSING_DIR / prep_path.name).exists():
                entry_copy["preprocessing_dir"] = str((settings.PREPROCESSING_DIR / prep_path.name).resolve())
            elif prep_path.name and (settings.BASE_DIR / "ml_models" / "preprocessing" / prep_path.name).exists():
                entry_copy["preprocessing_dir"] = str((settings.BASE_DIR / "ml_models" / "preprocessing" / prep_path.name).resolve())

        return entry_copy

    def get_model(
        self,
        model_name: str,
        dataset: Optional[str] = None,
        version: Optional[str] = None,
        active_only: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve model metadata from the registry.
        """
        registry = self._load_registry_data()
        models = registry.get("models", {})

        for _, m in models.items():
            if m.get("model_name") != model_name.lower():
                continue
            if dataset and m.get("dataset") != dataset.lower():
                continue
            if version and m.get("version") != version:
                continue
            if active_only and not m.get("is_active", False):
                continue
            return self._resolve_entry_paths(m)

        # Fallback: if active_only requested but none marked active, return latest
        for _, m in reversed(list(models.items())):
            if m.get("model_name") == model_name.lower():
                if dataset is None or m.get("dataset") == dataset.lower():
                    return self._resolve_entry_paths(m)

        return None

    def list_models(
        self,
        model_name: Optional[str] = None,
        dataset: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List registered models with optional filtering."""
        registry = self._load_registry_data()
        result = []
        for _, m in registry.get("models", {}).items():
            if model_name and m.get("model_name") != model_name.lower():
                continue
            if dataset and m.get("dataset") != dataset.lower():
                continue
            result.append(self._resolve_entry_paths(m))
        return result


model_registry = ModelRegistry()
