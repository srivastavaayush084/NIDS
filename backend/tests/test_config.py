from backend.app.core.config import Settings


def test_settings_initialization():
    """Verify settings loads properly with defaults."""
    custom_settings = Settings(
        PROJECT_NAME="Custom ZeroDay",
        ENVIRONMENT="testing",
        MONGODB_DATABASE="test_db"
    )
    assert custom_settings.PROJECT_NAME == "Custom ZeroDay"
    assert custom_settings.ENVIRONMENT == "testing"
    assert custom_settings.MONGODB_DATABASE == "test_db"
    assert not custom_settings.is_production


def test_cors_origins_parsing():
    """Verify comma-separated string is parsed into a list of origins."""
    settings = Settings(CORS_ORIGINS="http://localhost:3000, http://test.local")
    assert "http://localhost:3000" in settings.CORS_ORIGINS
    assert "http://test.local" in settings.CORS_ORIGINS


def test_paths_configured():
    """Verify base paths and directories exist as Path objects."""
    settings = Settings()
    assert settings.DATA_DIR is not None
    assert settings.MODELS_DIR is not None
    assert settings.PREPROCESSING_DIR is not None
