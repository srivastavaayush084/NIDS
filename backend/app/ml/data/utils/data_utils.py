import json
from pathlib import Path
from typing import Any, Dict, Optional, Union
import joblib
import pandas as pd
from backend.app.core.logging import logger


def ensure_dir(dir_path: Union[str, Path]) -> Path:
    """Ensure that the given directory exists, creating parents if needed."""
    path = Path(dir_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_artifact(obj: Any, file_path: Union[str, Path]) -> Path:
    """Serialize and save an ML artifact (scaler, encoder, pipeline) using joblib."""
    path = Path(file_path)
    ensure_dir(path.parent)
    joblib.dump(obj, path)
    logger.info(f"Saved artifact to: {path}")
    return path


def load_artifact(file_path: Union[str, Path]) -> Any:
    """Load a serialized ML artifact from disk."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Artifact not found at {path}")
    obj = joblib.load(path)
    logger.debug(f"Loaded artifact from: {path}")
    return obj


def save_metadata(metadata: Dict[str, Any], file_path: Union[str, Path]) -> Path:
    """Save metadata dictionary as formatted JSON."""
    path = Path(file_path)
    ensure_dir(path.parent)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, default=str)
    logger.info(f"Saved metadata to: {path}")
    return path


def load_metadata(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Load metadata dictionary from JSON file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Metadata file not found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_dataframe(
    df: pd.DataFrame, file_path: Union[str, Path], file_format: str = "csv"
) -> Path:
    """Save pandas DataFrame to CSV or Parquet format."""
    path = Path(file_path)
    ensure_dir(path.parent)
    if file_format.lower() in ("parquet", "pq"):
        df.to_parquet(path, index=False)
    else:
        df.to_csv(path, index=False)
    logger.info(f"Saved DataFrame ({len(df)} rows, {len(df.columns)} cols) to: {path}")
    return path


def load_dataframe(file_path: Union[str, Path], **kwargs) -> pd.DataFrame:
    """Load DataFrame from file (CSV, Parquet, TXT, GZ)."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Data file not found at {path}")
    
    suffix = path.suffix.lower()
    if suffix in (".parquet", ".pq"):
        return pd.read_parquet(path, **kwargs)
    elif suffix in (".csv", ".txt", ".gz"):
        return pd.read_csv(path, **kwargs)
    else:
        # Default fallback to read_csv
        return pd.read_csv(path, **kwargs)
