from pathlib import Path
from typing import Dict, List, Optional, Union
import pandas as pd
from backend.app.core.logging import logger
from backend.app.ml.data.loaders.base_loader import BaseDatasetLoader
from backend.app.ml.data.utils.data_utils import load_dataframe


class CICIDSLoader(BaseDatasetLoader):
    """
    Dataset loader for CICIDS 2017 Intrusion Detection Dataset.
    Supports individual daily PCAP-flow CSVs or combined datasets.
    Handles stripped whitespace headers, infinite rate values, and attack categories.
    """

    CATEGORICAL_COLS: List[str] = ["protocol", "destination_port"]

    DROP_COLS: List[str] = [
        "flow_id", "source_ip", "src_ip", "destination_ip", "dst_ip",
        "timestamp", "source_port", "src_port"
    ]

    ATTACK_MAPPING: Dict[str, str] = {
        "benign": "normal",
        "normal": "normal",
        # DoS attacks
        "dos slowloris": "dos",
        "dos slowhttptest": "dos",
        "dos hulk": "dos",
        "dos goldeneye": "dos",
        "heartbleed": "dos",
        # DDoS
        "ddos": "ddos",
        # Port Scanning
        "portscan": "portscan",
        # Brute Force
        "ftp-patator": "brute_force",
        "ssh-patator": "brute_force",
        # Web Attacks
        "web attack \x96 brute force": "web_attack",
        "web attack - brute force": "web_attack",
        "web attack – brute force": "web_attack",
        "web attack \ufffd brute force": "web_attack",
        "web attack \x96 xss": "web_attack",
        "web attack - xss": "web_attack",
        "web attack – xss": "web_attack",
        "web attack \ufffd xss": "web_attack",
        "web attack \x96 sql injection": "web_attack",
        "web attack - sql injection": "web_attack",
        "web attack – sql injection": "web_attack",
        "web attack \ufffd sql injection": "web_attack",
        # Botnet & Infiltration
        "bot": "botnet",
        "infiltration": "infiltration"
    }

    @property
    def dataset_name(self) -> str:
        return "cicids2017"

    @property
    def target_column(self) -> str:
        return "label"

    @property
    def categorical_columns(self) -> List[str]:
        return self.CATEGORICAL_COLS

    @property
    def numerical_columns(self) -> List[str]:
        # CICIDS features are dynamic flow attributes; dynamically extracted if not fixed
        return []

    @property
    def drop_columns(self) -> List[str]:
        return self.DROP_COLS

    def get_attack_category_mapping(self) -> Dict[str, str]:
        return self.ATTACK_MAPPING

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Strip whitespace, replace special characters, and convert column names to snake_case."""
        clean_cols = []
        for col in df.columns:
            cleaned = col.strip().lower()
            cleaned = cleaned.replace(" /s", "_per_s").replace("/s", "_per_s")
            cleaned = cleaned.replace(" ", "_").replace(".", "_").replace("-", "_")
            clean_cols.append(cleaned)
        df.columns = clean_cols
        return df

    def load(self, file_path: Optional[Union[str, Path]] = None, **kwargs) -> pd.DataFrame:
        """
        Load CICIDS 2017 dataset from a specific file or consolidate all CSVs in raw_dir.
        """
        target_path: Optional[Path] = None

        if file_path:
            target_path = Path(file_path)
            if not target_path.exists():
                raise FileNotFoundError(f"CICIDS 2017 dataset file not found at: {target_path}")
            logger.info(f"Loading CICIDS 2017 dataset from: {target_path}")
            df = load_dataframe(target_path, **kwargs)
        elif self.raw_dir.exists():
            for candidate_name in ["cicids2017.csv", "cicids2017_cleaned.csv", "cicids2017_consolidated.csv"]:
                candidate = self.raw_dir / candidate_name
                if candidate.exists():
                    target_path = candidate
                    break
            if target_path:
                logger.info(f"Loading consolidated CICIDS 2017 dataset from: {target_path}")
                df = load_dataframe(target_path, **kwargs)
            else:
                csv_files = sorted([f for f in self.raw_dir.glob("*.csv") if not f.name.startswith("cicids2017")])
                if not csv_files:
                    raise FileNotFoundError(f"No CSV files found in CICIDS 2017 raw directory: {self.raw_dir}")

                logger.info(f"Loading {len(csv_files)} CICIDS 2017 CSV files from: {self.raw_dir}")
                dfs = []
                for csv_file in csv_files:
                    logger.debug(f"Reading {csv_file.name}...")
                    sub_df = load_dataframe(csv_file, **kwargs)
                    dfs.append(sub_df)
                df = pd.concat(dfs, ignore_index=True)
        else:
            raise FileNotFoundError(
                f"CICIDS 2017 directory not found at {self.raw_dir}. "
                f"Please place CICIDS 2017 CSV files in {self.raw_dir}"
            )

        # Normalize column names
        df = self._normalize_columns(df)
        self.raw_df = df
        logger.info(f"Loaded CICIDS 2017 dataset with shape: {df.shape}")
        return df
