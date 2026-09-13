from pathlib import Path
from typing import Dict, List, Optional, Union
import pandas as pd
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ml.data.loaders.base_loader import BaseDatasetLoader
from backend.app.ml.data.utils.data_utils import load_dataframe


class SyntheticSampleLoader(BaseDatasetLoader):
    """
    Synthetic / Demo Dataset Loader.
    EXPLICITLY LABELED AS SYNTHETIC / DEMO DATA for verifying pipeline mechanics,
    unit testing, and smoke testing when full multi-gigabyte raw datasets are not mounted.
    DO NOT REPRESENT AS GENUINE NSL-KDD, CICIDS 2017, OR UNSW-NB15 TRAFFIC.
    """

    CATEGORICAL_COLS: List[str] = ["protocol_type", "service", "flag"]

    NUMERICAL_COLS: List[str] = [
        "duration", "src_bytes", "dst_bytes", "count", "srv_count",
        "serror_rate", "same_srv_rate", "diff_srv_rate",
        "dst_host_count", "dst_host_srv_count"
    ]

    ATTACK_MAPPING: Dict[str, str] = {
        "normal": "normal",
        "neptune": "dos",
        "ipsweep": "probe",
        "portsweep": "probe",
        "guess_passwd": "r2l",
        "warezclient": "r2l",
        "buffer_overflow": "u2r",
        "synthetic_zero_day": "zero_day_unseen"
    }

    @property
    def dataset_name(self) -> str:
        return "synthetic"

    @property
    def target_column(self) -> str:
        return "label"

    @property
    def categorical_columns(self) -> List[str]:
        return self.CATEGORICAL_COLS

    @property
    def numerical_columns(self) -> List[str]:
        return self.NUMERICAL_COLS

    def get_attack_category_mapping(self) -> Dict[str, str]:
        return self.ATTACK_MAPPING

    def load(self, file_path: Optional[Union[str, Path]] = None, **kwargs) -> pd.DataFrame:
        """Load the synthetic demonstration dataset."""
        sample_path = (
            Path(file_path)
            if file_path
            else settings.DATA_DIR / "sample" / "synthetic_network_sample.csv"
        )
        if not sample_path.exists():
            raise FileNotFoundError(f"Synthetic sample dataset not found at: {sample_path}")

        logger.info(f"Loading SYNTHETIC/DEMO dataset from: {sample_path}")
        df = load_dataframe(sample_path, comment="#", **kwargs)
        self.raw_df = df
        logger.info(f"Loaded synthetic dataset with shape: {df.shape}")
        return df
