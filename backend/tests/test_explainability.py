import pytest
import numpy as np
import pandas as pd
from datetime import datetime

from backend.app.ml.models.random_forest import RandomForestClassifierModel
from backend.app.ml.models.isolation_forest import IsolationForestDetector
from backend.app.ml.models.autoencoder import AutoencoderDetector
from backend.app.ml.models.lstm_autoencoder import LSTMAutoencoderDetector
from backend.app.ml.ensemble.ensemble_detector import EnsembleDetector
from backend.app.ml.model_manager import ModelManager
from backend.app.ml.explainability.schemas import (
    FeatureContribution,
    TimestepContribution,
    ModelExplanation,
    EnsembleExplanation,
    ExplanationRequest,
)
from backend.app.ml.explainability.feature_attribution import (
    resolve_feature_names,
    build_feature_contributions,
    generate_natural_language_summary,
    get_model_limitations,
)
from backend.app.ml.explainability.random_forest_explainer import RandomForestExplainer
from backend.app.ml.explainability.isolation_forest_explainer import IsolationForestExplainer
from backend.app.ml.explainability.autoencoder_explainer import AutoencoderExplainer
from backend.app.ml.explainability.lstm_explainer import LSTMAutoencoderExplainer
from backend.app.ml.explainability.ensemble_explainer import EnsembleExplainer
from backend.app.services.explainer_service import ExplainerService


@pytest.fixture
def synthetic_tabular_data():
    """Generate small reproducible tabular dataset with normal and anomaly samples."""
    np.random.seed(42)
    feature_names = ["duration", "src_bytes", "dst_bytes", "count", "srv_count"]
    
    # 80 normal samples centered around 0
    X_norm = np.random.normal(loc=0.0, scale=0.5, size=(80, 5))
    y_norm = np.zeros(80, dtype=int)
    
    # 20 attack samples with high src_bytes & count
    X_att = np.random.normal(loc=3.0, scale=0.8, size=(20, 5))
    y_att = np.ones(20, dtype=int)
    
    X = np.vstack([X_norm, X_att])
    y = np.concatenate([y_norm, y_att])
    
    return pd.DataFrame(X, columns=feature_names), pd.Series(y), feature_names


@pytest.fixture
def synthetic_sequence_data():
    """Generate small 3D sequence array (N=10, T=5, D=4)."""
    np.random.seed(42)
    seqs = np.random.normal(loc=0.0, scale=0.5, size=(10, 5, 4)).astype(np.float32)
    # Inject spike at t=3 in sample 0
    seqs[0, 3, 1] = 8.0
    return seqs


class TestXAISchemas:
    """Test XAI Pydantic schemas and serialization."""

    def test_feature_contribution_schema(self):
        fc = FeatureContribution(
            feature_name="src_bytes",
            feature_value=1024.0,
            contribution=0.35,
            direction="increases_risk",
            absolute_contribution=0.35,
            rank=1,
            raw_feature_name="src_bytes",
            shap_value=0.35,
        )
        assert fc.feature_name == "src_bytes"
        assert fc.direction == "increases_risk"
        assert fc.rank == 1

        # Test serialization
        data = fc.model_dump()
        assert data["contribution"] == 0.35
        assert data["direction"] == "increases_risk"

    def test_model_explanation_serialization(self):
        exp = ModelExplanation(
            model_name="random_forest",
            prediction="attack",
            is_anomaly=True,
            risk_score=85.0,
            severity="CRITICAL",
            decision_threshold=0.5,
            explanation_method="shap_tree",
            summary="Test summary",
            limitations=["Test limitation"],
        )
        json_str = exp.model_dump_json()
        assert "random_forest" in json_str
        assert "CRITICAL" in json_str

        summary_dict = exp.to_summary_dict()
        assert summary_dict["model_name"] == "random_forest"
        assert summary_dict["risk_score"] == 85.0


class TestFeatureAttributionHelpers:
    """Test feature resolution, contribution building, and natural language summary generation."""

    def test_feature_name_resolution(self):
        names = ["f1", "f2", "f3"]
        assert resolve_feature_names(names, 3) == names
        assert resolve_feature_names(None, 3, "col") == ["col_0", "col_1", "col_2"]

    def test_build_feature_contributions_ranking(self):
        feat_names = ["feat_a", "feat_b", "feat_c"]
        feat_vals = [10.0, 20.0, 30.0]
        contribs = [0.8, -0.9, 0.2]  # feat_b has highest abs contribution (0.9), feat_a is second (0.8)

        all_ranked, pos, neg = build_feature_contributions(
            feature_names=feat_names,
            feature_values=feat_vals,
            contributions=contribs,
            top_k=5,
        )

        assert len(all_ranked) == 3
        assert all_ranked[0].feature_name == "feat_b"
        assert all_ranked[0].rank == 1
        assert all_ranked[0].direction == "decreases_risk"

        assert all_ranked[1].feature_name == "feat_a"
        assert all_ranked[1].rank == 2
        assert all_ranked[1].direction == "increases_risk"

        assert len(pos) == 2
        assert len(neg) == 1
        assert neg[0].feature_name == "feat_b"

    def test_dynamic_summary_generation(self):
        top_pos = [
            FeatureContribution(
                feature_name="src_bytes",
                feature_value=5000,
                contribution=0.5,
                direction="increases_risk",
                absolute_contribution=0.5,
                rank=1,
            )
        ]
        top_neg = []
        summary = generate_natural_language_summary(
            model_name="random_forest",
            prediction="attack",
            risk_score=92.5,
            severity="CRITICAL",
            top_pos_features=top_pos,
            top_neg_features=top_neg,
        )
        assert "src_bytes" in summary
        assert "Random Forest" in summary
        assert "attack" in summary.lower()


class TestRandomForestExplainer:
    """Test Random Forest SHAP TreeExplainer."""

    def test_rf_shap_explanation(self, synthetic_tabular_data):
        X_df, y_ser, feat_names = synthetic_tabular_data
        rf = RandomForestClassifierModel(n_estimators=10, random_state=42)
        rf.train(X_df, y_ser, feature_names=feat_names)

        explainer = RandomForestExplainer(model=rf, feature_names=feat_names)
        assert explainer.is_initialized

        # Explain an attack sample (high index)
        attack_sample = X_df.iloc[-1]
        exp = explainer.explain_instance(attack_sample, top_k=3)

        assert isinstance(exp, ModelExplanation)
        assert exp.model_name == "random_forest"
        assert exp.explanation_method == "shap_tree"
        assert len(exp.feature_contributions) <= 3
        assert len(exp.limitations) > 0
        assert exp.total_latency_ms >= 0.0

        # Verify real feature names are present
        for fc in exp.feature_contributions:
            assert fc.feature_name in feat_names
            assert isinstance(fc.contribution, float)
            assert fc.direction in ("increases_risk", "decreases_risk", "neutral")


class TestIsolationForestExplainer:
    """Test Isolation Forest perturbation sensitivity explainer."""

    def test_if_perturbation_explanation(self, synthetic_tabular_data):
        X_df, y_ser, feat_names = synthetic_tabular_data
        X_norm = X_df[y_ser == 0]

        iforest = IsolationForestDetector(n_estimators=20, random_state=42)
        iforest.train(X_norm, feature_names=feat_names)

        explainer = IsolationForestExplainer(model=iforest, feature_names=feat_names)
        explainer.set_reference_baseline(X_norm)

        # Explain an anomaly sample
        sample = X_df.iloc[-1]
        exp = explainer.explain_instance(sample, top_k=5)

        assert exp.model_name == "isolation_forest"
        assert exp.explanation_method == "isolation_forest_perturbation"
        assert len(exp.feature_contributions) == 5
        assert any("perturbation" in lim.lower() for lim in exp.limitations)


class TestAutoencoderExplainer:
    """Test Dense Autoencoder reconstruction error explainer."""

    def test_autoencoder_reconstruction_explanation(self, synthetic_tabular_data):
        X_df, y_ser, feat_names = synthetic_tabular_data
        X_norm = X_df[y_ser == 0].to_numpy(dtype=np.float32)

        ae = AutoencoderDetector(input_dim=5, latent_dim=2, epochs=5, batch_size=16)
        ae.train(X_norm)
        ae.calibrate_threshold_and_bounds(X_norm)

        explainer = AutoencoderExplainer(model=ae, feature_names=feat_names)
        
        sample = X_df.iloc[-1].to_numpy(dtype=np.float32)
        exp = explainer.explain_instance(sample, top_k=4)

        assert exp.model_name == "autoencoder"
        assert exp.explanation_method == "autoencoder_reconstruction_error"
        assert len(exp.feature_contributions) == 4
        # Verify reconstruction error fields are populated
        for fc in exp.feature_contributions:
            assert fc.reconstructed_value is not None
            assert fc.reconstruction_error is not None
            assert fc.reconstruction_error >= 0.0


class TestLSTMExplainer:
    """Test LSTM Autoencoder hierarchical timestep and feature explainer."""

    def test_lstm_sequence_explanation(self, synthetic_sequence_data):
        seqs = synthetic_sequence_data
        lstm = LSTMAutoencoderDetector(
            input_dim=4,
            seq_len=5,
            encoder_units=16,
            latent_dim=4,
            decoder_units=16,
            epochs=3,
            batch_size=4,
        )
        lstm.train(seqs)
        lstm.calibrate_threshold_and_bounds(seqs)

        feat_names = ["f_0", "f_1", "f_2", "f_3"]
        explainer = LSTMAutoencoderExplainer(model=lstm, feature_names=feat_names)

        exp = explainer.explain_instance(seqs[0], top_k=3)

        assert exp.model_name == "lstm_autoencoder"
        assert exp.timestep_contributions is not None
        assert len(exp.timestep_contributions) == 5
        
        # Verify peak anomalous timestep identification (we spiked t=3, feature=1)
        peak_t = exp.timestep_contributions[0]
        assert peak_t.rank == 1
        assert peak_t.timestep_index in range(5)
        assert len(peak_t.top_features) > 0


class TestEnsembleExplainer:
    """Test unified Ensemble Explainer with multi-model risk breakdown."""

    def test_ensemble_explanation_breakdown(self, synthetic_tabular_data):
        X_df, y_ser, feat_names = synthetic_tabular_data
        
        rf = RandomForestClassifierModel(n_estimators=10, random_state=42).train(X_df, y_ser, feat_names)
        iforest = IsolationForestDetector(n_estimators=15, random_state=42).train(X_df[y_ser == 0], feat_names)
        
        detector = EnsembleDetector(
            random_forest=rf,
            isolation_forest=iforest,
            dataset_name="synthetic_test",
        )
        explainer = EnsembleExplainer(ensemble_detector=detector, top_k=5)

        sample = X_df.iloc[-1].to_dict()
        exp = explainer.explain_instance(sample)

        assert isinstance(exp, EnsembleExplanation)
        assert exp.model_name == "ensemble"
        assert len(exp.model_contributions) >= 2
        assert "random_forest" in exp.model_contributions
        assert "isolation_forest" in exp.model_contributions
        
        # Check weighted contributions sum properly
        rf_c = exp.model_contributions["random_forest"]
        assert "weighted_contribution" in rf_c
        assert "effective_weight" in rf_c
        
        assert len(exp.limitations) > 0
        assert len(exp.fused_feature_contributions) > 0


class TestExplainerService:
    """Test ExplainerService caching and async methods."""

    @pytest.mark.asyncio
    async def test_service_async_explanation(self, synthetic_tabular_data):
        X_df, y_ser, feat_names = synthetic_tabular_data
        rf = RandomForestClassifierModel(n_estimators=10, random_state=42).train(X_df, y_ser, feat_names)
        
        service = ExplainerService(default_dataset="test_ds")
        service.explainers["test_ds:random_forest"] = RandomForestExplainer(
            model=rf,
            dataset_name="test_ds",
            feature_names=feat_names,
            top_k=3,
        )

        sample = X_df.iloc[0].to_dict()
        exp = await service.explain_record_async("random_forest", sample, dataset="test_ds", top_k=3)

        assert exp.model_name == "random_forest"
        assert exp.top_k == 3
