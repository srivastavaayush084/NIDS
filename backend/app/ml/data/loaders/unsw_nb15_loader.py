from pathlib import Path
from typing import Dict, List, Optional, Union
import pandas as pd
from backend.app.core.logging import logger
from backend.app.ml.data.loaders.base_loader import BaseDatasetLoader
from backend.app.ml.data.utils.data_utils import load_dataframe


class UNSWNB15Loader(BaseDatasetLoader):
    """
    Dataset loader for UNSW-NB15 Network Intrusion Dataset.
    Features modern synthetic attack activities and realistic normal background flows.
    """

    CATEGORICAL_COLS: List[str] = ["proto", "service", "state"]

    DROP_COLS: List[str] = [
        "id", "srcip", "dstip", "sport", "dsport", "stime", "ltime"
    ]

    ATTACK_MAPPING: Dict[str, str] = {
        "normal": "normal",
        "benign": "normal",
        "0": "normal",
        # Attack Categories
        "fuzzers": "fuzzers",
        "analysis": "analysis",
        "backdoors": "backdoor",
        "backdoor": "backdoor",
        "dos": "dos",
        "exploits": "exploits",
        "generic": "generic",
        "reconnaissance": "reconnaissance",
        "shellcode": "shellcode",
        "worms": "worms"
    }

    @property
    def dataset_name(self) -> str:
        return "unsw_nb15"

    @property
    def target_column(self) -> str:
        return "attack_cat"

    @property
    def categorical_columns(self) -> List[str]:
        return self.CATEGORICAL_COLS

    @property
    def numerical_columns(self) -> List[str]:
        return []

    @property
    def drop_columns(self) -> List[str]:
        return self.DROP_COLS

    def get_attack_category_mapping(self) -> Dict[str, str]:
        return self.ATTACK_MAPPING

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Strip whitespace and normalize column names."""
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        return df

    def load(self, file_path: Optional[Union[str, Path]] = None, **kwargs) -> pd.DataFrame:
        """
        Load UNSW-NB15 dataset from specific file (e.g., UNSW_NB15_training-set.csv)
        or from the raw data directory.
        """
        target_path: Optional[Path] = None

        if file_path:
            target_path = Path(file_path)
        elif self.raw_dir.exists():
            for candidate_name in [
                "UNSW_NB15_training-set.csv", "UNSW-NB15.csv", "unsw_nb15.csv",
                "UNSW_NB15_testing-set.csv", "UNSW-NB15_1.csv"
            ]:
                candidate = self.raw_dir / candidate_name
                if candidate.exists():
                    target_path = candidate
                    break
            if not target_path:
                files = list(self.raw_dir.glob("*.csv"))
                if files:
                    target_path = files[0]

        if not target_path or not target_path.exists():
            raise FileNotFoundError(
                f"UNSW-NB15 dataset file not found at {target_path or self.raw_dir}. "
                f"Please place UNSW-NB15 CSV files in {self.raw_dir}"
            )

        logger.info(f"Loading UNSW-NB15 dataset from: {target_path}")
        df = load_dataframe(target_path, **kwargs)
        df = self._normalize_columns(df)

        # UNSW-NB15 has both 'attack_cat' (category string) and 'label' (0/1)
        # If attack_cat is missing/null on normal records, fill with 'normal'
        if "attack_cat" in df.columns:
            df["attack_cat"] = df["attack_cat"].fillna("normal").astype(str).str.strip().str.lower()
            df.loc[df["attack_cat"] == "", "attack_cat"] = "normal"
            df.loc[df["attack_cat"] == "nan", "attack_cat"] = "normal"

        self.raw_df = df
        logger.info(f"Loaded UNSW-NB15 dataset with shape: {df.shape}")
        return df
