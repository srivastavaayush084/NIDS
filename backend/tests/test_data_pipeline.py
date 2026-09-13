import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from backend.app.ml.data.loaders.factory import get_dataset_loader, list_supported_datasets
from backend.app.ml.data.loaders.synthetic_loader import SyntheticSampleLoader
from backend.app.ml.data.loaders.nsl_kdd_loader import NSLKDDLoader
from backend.app.ml.data.loaders.cicids_loader import CICIDSLoader
from backend.app.ml.data.loaders.unsw_nb15_loader import UNSWNB15Loader

from backend.app.ml.data.validation.dataset_validator import DatasetValidator, ValidationReport
from backend.app.ml.data.statistics.dataset_analyzer import DatasetAnalyzer
from backend.app.ml.data.preprocessing.cleaner import DataCleaner
from backend.app.ml.data.preprocessing.encoder import CategoricalEncoder
from backend.app.ml.data.preprocessing.scaler import NumericalScaler
from backend.app.ml.data.preprocessing.feature_engineer import NetworkFeatureEngineer
from backend.app.ml.data.preprocessing.feature_selector import FeatureSelector
from backend.app.ml.data.preprocessing.pipeline import NetworkDataPipeline
from backend.app.ml.data.splitting.dataset_splitter import DatasetSplitter
from backend.app.ml.preprocessor import TrafficPreprocessor


@pytest.fixture
def sample_raw_df() -> pd.DataFrame:
    """Fixture providing a synthetic DataFrame for unit testing."""
    return pd.DataFrame({
        "duration": [0.0, 1.2, 0.0, 5.0, 0.0, 0.0, 2.1, 0.5, 0.0, 10.0],
        "protocol_type": ["tcp", "tcp", "udp", "tcp", "icmp", "tcp", "tcp", "udp", "tcp", "tcp"],
        "service": ["http", "http", "domain_u", "smtp", "eco_i", "ftp", "http", "other", "private", "custom_zero"],
        "flag": ["SF", "SF", "SF", "SF", "SF", "SF", "REJ", "SF", "S0", "SF"],
        "src_bytes": [215.0, 162.0, 45.0, 105.0, 8.0, 236.0, 0.0, 50.0, 0.0, 9200.0],
        "dst_bytes": [45076.0, 4528.0, 45.0, 1453.0, 0.0, 1228.0, 0.0, 100.0, 0.0, 48000.0],
        "count": [1, 2, 1, 1, 1, 1, 1, 3, 123, 50],
        "srv_count": [1, 2, 1, 1, 1, 1, 1, 3, 6, 50],
        "serror_rate": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
        "same_srv_rate": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.05, 1.0],
        "diff_srv_rate": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.07, 0.0],
        "dst_host_count": [0, 1, 3, 4, 1, 2, 255, 10, 255, 12],
        "dst_host_srv_count": [0, 1, 3, 4, 1, 2, 1, 10, 6, 1],
        "label": [
            "normal", "normal", "normal", "normal", "ipsweep",
            "normal", "portsweep", "normal", "neptune", "synthetic_zero_day"
        ],
    })


# ---------------------------------------------------------------------------
# 1. Dataset Validation Tests
# ---------------------------------------------------------------------------
def test_dataset_validator_file_checks(tmp_path: Path):
    """Verify file existence and empty file detection."""
    non_existent = tmp_path / "does_not_exist.csv"
    rep_missing = DatasetValidator.validate_file(non_existent)
    assert not rep_missing.is_valid
    assert len(rep_missing.errors) > 0

    empty_file = tmp_path / "empty.csv"
    empty_file.touch()
    rep_empty = DatasetValidator.validate_file(empty_file)
    assert not rep_empty.is_valid
    assert "empty" in rep_empty.errors[0].lower()


def test_dataset_validator_dataframe_quality(sample_raw_df: pd.DataFrame):
    """Verify DataFrame schema and quality checks."""
    report = DatasetValidator.validate_dataframe(sample_raw_df, target_column="label")
    assert report.is_valid
    assert report.total_rows == 10
    assert report.total_columns == 14
    assert report.target_column_found is True
    assert len(report.numerical_columns) > 0
    assert len(report.categorical_columns) > 0


# ---------------------------------------------------------------------------
# 2. Missing & Infinite Value Handling Tests
# ---------------------------------------------------------------------------
def test_data_cleaner_nan_and_inf_handling():
    """Verify NaN imputation and Infinity clamping."""
    dirty_df = pd.DataFrame({
        "num1": [1.0, np.nan, 3.0, np.inf, 5.0],
        "num2": [10.0, 20.0, -np.inf, 40.0, 50.0],
        "cat1": ["http", np.nan, "smtp", "ftp", "http"],
    })
    cleaner = DataCleaner(drop_duplicates=False, numeric_impute_strategy="median")
    cleaned_df = cleaner.fit_transform(dirty_df)

    assert not cleaned_df.isna().any().any()
    assert not np.isinf(cleaned_df["num1"].to_numpy()).any()
    assert not np.isinf(cleaned_df["num2"].to_numpy()).any()
    assert cleaned_df["cat1"].iloc[1] == "unknown"


# ---------------------------------------------------------------------------
# 3. Duplicate Removal Tests
# ---------------------------------------------------------------------------
def test_data_cleaner_duplicate_removal():
    """Verify duplicate record removal and logging."""
    dup_df = pd.DataFrame({
        "a": [1, 2, 2, 3],
        "b": ["x", "y", "y", "z"],
    })
    cleaner = DataCleaner(drop_duplicates=True)
    cleaned = cleaner.fit_transform(dup_df)

    assert len(cleaned) == 3
    assert cleaner.cleaning_stats["duplicates_removed"] == 1


# ---------------------------------------------------------------------------
# 4. Label Separation & Target Leakage Prevention Tests
# ---------------------------------------------------------------------------
def test_label_separation_and_no_leakage(sample_raw_df: pd.DataFrame):
    """Verify feature matrix X has strictly NO target or secondary label columns."""
    loader = SyntheticSampleLoader()
    X, y_orig, y_cat, y_bin = loader.extract_labels(sample_raw_df)

    assert "label" not in X.columns
    assert "attack_category" not in X.columns
    assert "binary_label" not in X.columns
    assert len(X) == len(y_bin)
    assert len(y_orig) == len(y_cat) == len(y_bin)
    
    # Check binary label conversion
    assert (y_bin.iloc[0] == 0)  # normal
    assert (y_bin.iloc[4] == 1)  # ipsweep attack
    assert (y_cat.iloc[4] == "probe")  # ipsweep -> probe


# ---------------------------------------------------------------------------
# 5. Categorical Encoding & Unknown Values Tests
# ---------------------------------------------------------------------------
def test_categorical_encoder_onehot_and_unknowns():
    """Verify OneHotEncoder fits on train and safely handles unknown values in test."""
    train_df = pd.DataFrame({
        "proto": ["tcp", "udp", "tcp"],
        "num": [10.0, 20.0, 30.0],
    })
    test_df = pd.DataFrame({
        "proto": ["icmp", "tcp"],  # icmp was not in training!
        "num": [40.0, 50.0],
    })

    encoder = CategoricalEncoder(strategy="onehot")
    train_enc = encoder.fit_transform(train_df)
    test_enc = encoder.transform(test_df)

    assert "proto_tcp" in train_enc.columns
    assert "proto_udp" in train_enc.columns
    assert "proto_tcp" in test_enc.columns
    assert "proto_udp" in test_enc.columns

    # Unknown category "icmp" should have 0s across all one-hot columns
    assert test_enc.iloc[0]["proto_tcp"] == 0.0
    assert test_enc.iloc[0]["proto_udp"] == 0.0
    assert test_enc.iloc[1]["proto_tcp"] == 1.0


# ---------------------------------------------------------------------------
# 6. Numerical Feature Scaling Tests
# ---------------------------------------------------------------------------
def test_numerical_scaling_standard_and_minmax():
    """Verify scaler fits only on train and transforms test accurately."""
    train_df = pd.DataFrame({"feat": [0.0, 10.0, 20.0]})
    test_df = pd.DataFrame({"feat": [5.0, 15.0]})

    scaler_mm = NumericalScaler(strategy="minmax")
    train_scaled = scaler_mm.fit_transform(train_df)
    test_scaled = scaler_mm.transform(test_df)

    assert train_scaled["feat"].min() == 0.0
    assert train_scaled["feat"].max() == 1.0
    assert test_scaled["feat"].iloc[0] == pytest.approx(0.25)
    assert test_scaled["feat"].iloc[1] == pytest.approx(0.75)


# ---------------------------------------------------------------------------
# 7. Network Feature Engineering Tests
# ---------------------------------------------------------------------------
def test_network_feature_engineering(sample_raw_df: pd.DataFrame):
    """Verify adaptive calculation of byte ratios and packet metrics."""
    engineer = NetworkFeatureEngineer(enable_engineering=True)
    eng_df = engineer.fit_transform(sample_raw_df)

    assert "feat_byte_ratio" in eng_df.columns
    assert "feat_total_bytes" in eng_df.columns
    assert "feat_src_byte_rate" in eng_df.columns


# ---------------------------------------------------------------------------
# 8. Feature Selection Tests
# ---------------------------------------------------------------------------
def test_feature_selection_variance_and_correlation():
    """Verify constant feature dropping and correlation pruning."""
    df = pd.DataFrame({
        "const": [1.0, 1.0, 1.0, 1.0],  # zero variance
        "var1": [1.0, 2.0, 3.0, 4.0],
        "var2": [10.0, 20.0, 30.0, 40.0],  # 1.0 correlated with var1
        "var3": [4.0, 1.0, 2.0, 5.0],
    })

    selector = FeatureSelector(
        strategy="correlation",
        variance_threshold=0.0,
        correlation_threshold=0.99
    )
    selected_df = selector.fit_transform(df)

    assert "const" not in selected_df.columns
    assert ("var1" in selected_df.columns) or ("var2" in selected_df.columns)
    assert not ("var1" in selected_df.columns and "var2" in selected_df.columns)


# ---------------------------------------------------------------------------
# 9. Dataset Splitting Tests (Standard & Stratified)
# ---------------------------------------------------------------------------
def test_dataset_splits(sample_raw_df: pd.DataFrame):
    """Verify Standard and Stratified dataset partitioning."""
    loader = SyntheticSampleLoader()
    X, y_orig, y_cat, y_bin = loader.extract_labels(sample_raw_df)

    split_res = DatasetSplitter.split(
        X, y_bin, y_cat, y_orig,
        strategy="standard",
        val_size=0.2,
        test_size=0.2,
        random_state=42
    )

    total_len = len(split_res.X_train) + len(split_res.X_val) + len(split_res.X_test)
    assert total_len == len(sample_raw_df)
    assert len(split_res.X_train) > len(split_res.X_val)


# ---------------------------------------------------------------------------
# 10. Unseen Zero-Day Attack Evaluation Split Tests
# ---------------------------------------------------------------------------
def test_unseen_zero_day_attack_split(sample_raw_df: pd.DataFrame):
    """
    CRITICAL ZERO-DAY EVALUATION TEST:
    Verify that withheld zero-day attack categories are strictly excluded from
    training and validation sets and placed 100% in the test set.
    """
    loader = SyntheticSampleLoader()
    X, y_orig, y_cat, y_bin = loader.extract_labels(sample_raw_df)

    unseen_attacks = ["zero_day_unseen", "synthetic_zero_day"]
    split_res = DatasetSplitter.split(
        X, y_bin, y_cat, y_orig,
        strategy="unseen_zero_day",
        unseen_categories=unseen_attacks,
        val_size=0.2,
        test_size=0.2,
        random_state=42
    )

    # 1. Training set must NOT contain any unseen attack categories
    train_cats = split_res.y_train_category.tolist()
    assert "zero_day_unseen" not in train_cats
    assert "synthetic_zero_day" not in train_cats

    # 2. Validation set must NOT contain any unseen attack categories
    val_cats = split_res.y_val_category.tolist()
    assert "zero_day_unseen" not in val_cats
    assert "synthetic_zero_day" not in val_cats

    # 3. Test set MUST contain the withheld zero-day attack samples
    test_cats = split_res.y_test_category.tolist()
    assert "zero_day_unseen" in test_cats


# ---------------------------------------------------------------------------
# 11. Preprocessing Artifact Serialization & Reload Tests
# ---------------------------------------------------------------------------
def test_pipeline_artifact_save_and_reload(sample_raw_df: pd.DataFrame, tmp_path: Path):
    """Verify pipeline serialization to disk and exact reload match."""
    loader = SyntheticSampleLoader()
    X, _, _, y_bin = loader.extract_labels(sample_raw_df)

    pipeline = NetworkDataPipeline(
        dataset_name="synthetic",
        scaling_strategy="standard",
        encoding_strategy="onehot",
        selection_strategy="variance",
    )
    pipeline.fit(X, y=y_bin)
    out_dir = pipeline.save(tmp_path / "artifacts")

    assert (out_dir / "pipeline.joblib").exists()
    assert (out_dir / "metadata.json").exists()
    assert (out_dir / "selected_features.json").exists()

    # Reload pipeline from disk
    loaded_pipeline = NetworkDataPipeline.load(out_dir)
    assert loaded_pipeline.is_fitted
    assert loaded_pipeline.selected_features_ == pipeline.selected_features_

    # Verify identical output on transformation
    original_trans = pipeline.transform_to_numpy(X)
    reloaded_trans = loaded_pipeline.transform_to_numpy(X)
    np.testing.assert_allclose(original_trans, reloaded_trans, atol=1e-5)


# ---------------------------------------------------------------------------
# 12. End-to-End Pipeline & TrafficPreprocessor Integration Tests
# ---------------------------------------------------------------------------
def test_traffic_preprocessor_end_to_end(sample_raw_df: pd.DataFrame, tmp_path: Path):
    """Verify TrafficPreprocessor seamless inference with NetworkDataPipeline."""
    loader = SyntheticSampleLoader()
    X, _, _, y_bin = loader.extract_labels(sample_raw_df)

    pipeline = NetworkDataPipeline(dataset_name="synthetic")
    pipeline.fit(X, y=y_bin)
    art_dir = pipeline.save(tmp_path / "preproc_models")

    preprocessor = TrafficPreprocessor()
    preprocessor.load_pipeline(art_dir)

    assert preprocessor.is_fitted
    feature_matrix = preprocessor.transform(X)
    assert isinstance(feature_matrix, np.ndarray)
    assert feature_matrix.shape[0] == len(X)
    assert feature_matrix.shape[1] == len(pipeline.selected_features_)
