from pathlib import Path
from typing import Dict, List, Optional, Union
import pandas as pd
from backend.app.core.logging import logger
from backend.app.ml.data.loaders.base_loader import BaseDatasetLoader
from backend.app.ml.data.utils.data_utils import load_dataframe


class NSLKDDLoader(BaseDatasetLoader):
    """
    Dataset loader for NSL-KDD Network Intrusion Dataset.
    Standard NSL-KDD records comprise 41 traffic attributes, 1 attack label,
    and 1 optional difficulty rating score.
    """

    # 41 Standard NSL-KDD Feature Names + label + difficulty
    COLUMNS: List[str] = [
        "duration", "protocol_type", "service", "flag", "src_bytes", "dst_bytes",
        "land", "wrong_fragment", "urgent", "hot", "num_failed_logins", "logged_in",
        "num_compromised", "root_shell", "su_attempted", "num_root", "num_file_creations",
        "num_shells", "num_access_files", "num_outbound_cmds", "is_host_login",
        "is_guest_login", "count", "srv_count", "serror_rate", "srv_serror_rate",
        "rerror_rate", "srv_rerror_rate", "same_srv_rate", "diff_srv_rate",
        "srv_diff_host_rate", "dst_host_count", "dst_host_srv_count",
        "dst_host_same_srv_rate", "dst_host_diff_srv_rate", "dst_host_same_src_port_rate",
        "dst_host_srv_diff_host_rate", "dst_host_serror_rate", "dst_host_srv_serror_rate",
        "dst_host_rerror_rate", "dst_host_srv_rerror_rate", "label", "difficulty_level"
    ]

    CATEGORICAL_COLS: List[str] = ["protocol_type", "service", "flag"]

    NUMERICAL_COLS: List[str] = [
        "duration", "src_bytes", "dst_bytes", "land", "wrong_fragment", "urgent", "hot",
        "num_failed_logins", "logged_in", "num_compromised", "root_shell", "su_attempted",
        "num_root", "num_file_creations", "num_shells", "num_access_files", "num_outbound_cmds",
        "is_host_login", "is_guest_login", "count", "srv_count", "serror_rate", "srv_serror_rate",
        "rerror_rate", "srv_rerror_rate", "same_srv_rate", "diff_srv_rate", "srv_diff_host_rate",
        "dst_host_count", "dst_host_srv_count", "dst_host_same_srv_rate", "dst_host_diff_srv_rate",
        "dst_host_same_src_port_rate", "dst_host_srv_diff_host_rate", "dst_host_serror_rate",
        "dst_host_srv_serror_rate", "dst_host_rerror_rate", "dst_host_srv_rerror_rate"
    ]

    DROP_COLS: List[str] = ["difficulty_level"]

    # Mapping of specific attack types to high-level attack families (DoS, Probe, R2L, U2R, Normal)
    ATTACK_MAPPING: Dict[str, str] = {
        # Normal
        "normal": "normal",
        "benign": "normal",
        # Denial of Service (DoS)
        "apache2": "dos",
        "back": "dos",
        "land": "dos",
        "neptune": "dos",
        "mailbomb": "dos",
        "pod": "dos",
        "processtable": "dos",
        "smurf": "dos",
        "teardrop": "dos",
        "udpstorm": "dos",
        "worm": "dos",
        # Probing / Surveillance (Probe)
        "ipsweep": "probe",
        "mscan": "probe",
        "nmap": "probe",
        "portsweep": "probe",
        "saint": "probe",
        "satan": "probe",
        # Remote to Local (R2L)
        "ftp_write": "r2l",
        "guess_passwd": "r2l",
        "httptunnel": "r2l",
        "imap": "r2l",
        "multihop": "r2l",
        "named": "r2l",
        "phf": "r2l",
        "sendmail": "r2l",
        "snmpgetattack": "r2l",
        "snmpguess": "r2l",
        "spy": "r2l",
        "warezclient": "r2l",
        "warezmaster": "r2l",
        "xlock": "r2l",
        "xsnoop": "r2l",
        # User to Root (U2R)
        "buffer_overflow": "u2r",
        "loadmodule": "u2r",
        "perl": "u2r",
        "ps": "u2r",
        "rootkit": "u2r",
        "sqlattack": "u2r",
        "xterm": "u2r"
    }

    @property
    def dataset_name(self) -> str:
        return "nsl_kdd"

    @property
    def target_column(self) -> str:
        return "label"

    @property
    def categorical_columns(self) -> List[str]:
        return self.CATEGORICAL_COLS

    @property
    def numerical_columns(self) -> List[str]:
        return self.NUMERICAL_COLS

    @property
    def drop_columns(self) -> List[str]:
        return self.DROP_COLS

    def get_attack_category_mapping(self) -> Dict[str, str]:
        return self.ATTACK_MAPPING

    def load(self, file_path: Optional[Union[str, Path]] = None, **kwargs) -> pd.DataFrame:
        """
        Load NSL-KDD dataset from file or default raw directory.
        Handles both headered and headerless CSV/TXT files (e.g., KDDTrain+.txt).
        """
        target_path: Optional[Path] = None

        if file_path:
            target_path = Path(file_path)
        elif self.raw_dir.exists():
            # Search for standard NSL-KDD file names
            for candidate_name in [
                "KDDTrain+.txt", "KDDTrain+.csv", "nsl_kdd.csv", "KDDTrain_20Percent.txt",
                "KDDTest+.txt", "KDDTest+.csv", "nsl_kdd_train.csv"
            ]:
                candidate = self.raw_dir / candidate_name
                if candidate.exists():
                    target_path = candidate
                    break
            if not target_path:
                # Find any csv or txt file in the directory
                files = list(self.raw_dir.glob("*.csv")) + list(self.raw_dir.glob("*.txt"))
                if files:
                    target_path = files[0]

        if not target_path or not target_path.exists():
            raise FileNotFoundError(
                f"NSL-KDD dataset file not found at {target_path or self.raw_dir}. "
                f"Please place NSL-KDD files (e.g. KDDTrain+.txt) in {self.raw_dir}"
            )

        logger.info(f"Loading NSL-KDD dataset from: {target_path}")

        # Probe first line to check if headers are present
        with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
            first_line = f.readline().strip()

        # If first line contains known feature names like 'duration', 'protocol_type', use existing header
        if "duration" in first_line.lower() and "protocol" in first_line.lower():
            df = load_dataframe(target_path, **kwargs)
        else:
            # NSL-KDD raw files often have 42 or 43 columns without headers
            num_cols = len(first_line.split(","))
            if num_cols == 43:
                col_names = self.COLUMNS
            elif num_cols == 42:
                col_names = self.COLUMNS[:42]
            else:
                col_names = None

            if col_names:
                df = pd.read_csv(target_path, header=None, names=col_names, **kwargs)
            else:
                df = load_dataframe(target_path, **kwargs)

        self.raw_df = df
        logger.info(f"Loaded NSL-KDD dataset with shape: {df.shape}")
        return df
