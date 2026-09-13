from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
import numpy as np
import pandas as pd
from backend.app.core.logging import logger


@dataclass
class ValidationReport:
    """Structured report containing dataset integrity, quality, and schema findings."""
    is_valid: bool
    file_path: Optional[str] = None
    total_rows: int = 0
    total_columns: int = 0
    duplicate_rows: int = 0
    missing_values_count: int = 0
    infinite_values_count: int = 0
    numerical_columns: List[str] = field(default_factory=list)
    categorical_columns: List[str] = field(default_factory=list)
    target_column_found: bool = False
    target_column_name: Optional[str] = None
    missing_required_columns: List[str] = field(default_factory=list)
    detected_leakage_columns: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "file_path": self.file_path,
            "total_rows": self.total_rows,
            "total_columns": self.total_columns,
            "duplicate_rows": self.duplicate_rows,
            "missing_values_count": self.missing_values_count,
            "infinite_values_count": self.infinite_values_count,
            "numerical_columns_count": len(self.numerical_columns),
            "categorical_columns_count": len(self.categorical_columns),
            "target_column_found": self.target_column_found,
            "target_column_name": self.target_column_name,
            "missing_required_columns": self.missing_required_columns,
            "detected_leakage_columns": self.detected_leakage_columns,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class DatasetValidator:
    """
    Validates network intrusion datasets before and after ingestion.
    Performs integrity, quality, missing value, infinity, and schema checks.
    """

    SUPPORTED_EXTENSIONS: Set[str] = {".csv", ".txt", ".parquet", ".pq", ".gz"}
    COMMON_LEAKAGE_COLUMNS: Set[str] = {
        "id", "flow_id", "src_ip", "dst_ip", "source_ip", "destination_ip",
        "srcip", "dstip", "timestamp", "stime", "ltime", "difficulty_level"
    }

    @classmethod
    def validate_file(cls, file_path: Union[str, Path]) -> ValidationReport:
        """Validate physical file existence and readable extension."""
        path = Path(file_path)
        errors: List[str] = []
        warnings: List[str] = []

        if not path.exists():
            return ValidationReport(
                is_valid=False,
                file_path=str(path),
                errors=[f"File does not exist: {path}"]
            )

        if path.is_dir():
            return ValidationReport(
                is_valid=False,
                file_path=str(path),
                errors=[f"Expected a dataset file, but got a directory: {path}"]
            )

        ext = path.suffix.lower()
        if ext not in cls.SUPPORTED_EXTENSIONS:
            warnings.append(
                f"File extension '{ext}' is not in standard supported extensions: {cls.SUPPORTED_EXTENSIONS}"
            )

        if path.stat().st_size == 0:
            return ValidationReport(
                is_valid=False,
                file_path=str(path),
                errors=[f"Dataset file is completely empty (0 bytes): {path}"]
            )

        return ValidationReport(
            is_valid=True,
            file_path=str(path),
            warnings=warnings
        )

    @classmethod
    def validate_dataframe(
        cls,
        df: pd.DataFrame,
        target_column: Optional[str] = None,
        required_columns: Optional[List[str]] = None,
        check_leakage: bool = True,
    ) -> ValidationReport:
        """
        Comprehensive data quality and schema validation for in-memory DataFrame.
        """
        errors: List[str] = []
        warnings: List[str] = []

        if df is None:
            return ValidationReport(is_valid=False, errors=["DataFrame is None"])

        if df.empty or len(df) == 0:
            return ValidationReport(
                is_valid=False,
                total_rows=0,
                total_columns=len(df.columns) if df is not None else 0,
                errors=["Dataset is empty (0 rows)."]
            )

        total_rows = len(df)
        total_cols = len(df.columns)

        # 1. Duplicates check
        try:
            duplicate_count = int(df.duplicated().sum())
            if duplicate_count > 0:
                warnings.append(f"Found {duplicate_count} duplicate rows ({duplicate_count / total_rows:.2%}).")
        except Exception:
            duplicate_count = 0

        # 2. Missing values check
        missing_count = int(df.isna().sum().sum())
        if missing_count > 0:
            warnings.append(f"Found {missing_count} total NaN/missing values.")

        # 3. Infinite values check (on numeric columns)
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()

        inf_count = 0
        if numeric_cols:
            inf_mask = np.isinf(df[numeric_cols].to_numpy(dtype=float, na_value=0.0))
            inf_count = int(np.sum(inf_mask))
            if inf_count > 0:
                warnings.append(f"Found {inf_count} infinite (+/- inf) values in numeric columns.")

        # 4. Target column check
        target_found = False
        target_name = None
        if target_column:
            col_map = {c.lower().strip(): c for c in df.columns}
            if target_column.lower().strip() in col_map:
                target_found = True
                target_name = col_map[target_column.lower().strip()]
            else:
                errors.append(f"Specified target column '{target_column}' was not found in dataset columns.")
        else:
            # Check if any standard target column exists
            for candidate in ("label", "attack", "class", "attack_cat", "attack_category"):
                col_map = {c.lower().strip(): c for c in df.columns}
                if candidate in col_map:
                    target_found = True
                    target_name = col_map[candidate]
                    break
            if not target_found:
                warnings.append("No explicit target label column detected in dataset.")

        # 5. Required columns check
        missing_reqs: List[str] = []
        if required_columns:
            existing_set = set(df.columns)
            missing_reqs = [c for c in required_columns if c not in existing_set]
            if missing_reqs:
                errors.append(f"Missing {len(missing_reqs)} required columns: {missing_reqs[:10]}...")

        # 6. Leakage column detection
        detected_leakage: List[str] = []
        if check_leakage:
            for col in df.columns:
                c_clean = col.lower().strip().replace(" ", "_").replace("-", "_")
                if c_clean in cls.COMMON_LEAKAGE_COLUMNS and col != target_name:
                    detected_leakage.append(col)
            if detected_leakage:
                warnings.append(f"Detected potential metadata/leakage columns: {detected_leakage}")

        is_valid = len(errors) == 0

        report = ValidationReport(
            is_valid=is_valid,
            total_rows=total_rows,
            total_columns=total_cols,
            duplicate_rows=duplicate_count,
            missing_values_count=missing_count,
            infinite_values_count=inf_count,
            numerical_columns=numeric_cols,
            categorical_columns=categorical_cols,
            target_column_found=target_found,
            target_column_name=target_name,
            missing_required_columns=missing_reqs,
            detected_leakage_columns=detected_leakage,
            errors=errors,
            warnings=warnings,
        )

        if not is_valid:
            logger.error(f"Dataset validation failed with {len(errors)} errors: {errors}")
        else:
            logger.info(
                f"Dataset validation passed: {total_rows} rows, {total_cols} cols, "
                f"{len(numeric_cols)} numeric, {len(categorical_cols)} categorical, "
                f"{len(warnings)} warnings."
            )

        return report
