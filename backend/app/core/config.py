from pathlib import Path
from typing import List, Union, Optional
from pydantic import Field, AliasChoices, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized Application Settings and Configuration Management."""
    
    # Project & Environment Settings
    PROJECT_NAME: str = "ZeroDayAI - Zero-Day Attack Detection Platform"
    PROJECT_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = Field(default="development", validation_alias=AliasChoices("ENVIRONMENT", "ENV"))
    DEBUG: bool = True
    LOG_LEVEL: str = Field(default="INFO", validation_alias=AliasChoices("LOG_LEVEL", "LOGGING_LEVEL"))

    # Server Host & Port Configuration
    HOST: str = Field(default="0.0.0.0", validation_alias=AliasChoices("API_HOST", "HOST", "BACKEND_HOST"))
    PORT: int = Field(default=8000, validation_alias=AliasChoices("API_PORT", "PORT", "BACKEND_PORT"))
    
    # Frontend & CORS Configuration
    FRONTEND_URL: str = Field(default="http://localhost:5173", validation_alias=AliasChoices("FRONTEND_URL", "CLIENT_URL"))
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v
        return []

    # MongoDB Database Configuration
    MONGODB_URI: str = Field(default="mongodb://localhost:27017", validation_alias=AliasChoices("MONGODB_URI", "MONGO_URI", "DATABASE_URL"))
    MONGODB_DATABASE: str = Field(default="zero_day_detection", validation_alias=AliasChoices("MONGODB_DATABASE", "MONGODB_DB_NAME", "MONGO_DB"))
    MONGODB_MIN_POOL_SIZE: int = 10
    MONGODB_MAX_POOL_SIZE: int = 50
    MONGODB_TIMEOUT_MS: int = 2500

    @field_validator("MONGODB_URI", mode="before")
    @classmethod
    def validate_mongodb_uri(cls, v: Union[str, None]) -> str:
        if not v or not isinstance(v, str) or not (v.startswith("mongodb://") or v.startswith("mongodb+srv://")):
            raise ValueError("MONGODB_URI must be a valid connection string starting with 'mongodb://' or 'mongodb+srv://'")
        return v

    # Security, JWT & Authentication Configuration
    JWT_SECRET_KEY: str = Field(
        default="dev-insecure-secret-key-change-in-production-1234567890",
        validation_alias=AliasChoices("JWT_SECRET_KEY", "SECRET_KEY")
    )
    JWT_ALGORITHM: str = Field(default="HS256", validation_alias=AliasChoices("JWT_ALGORITHM", "ALGORITHM"))
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60, validation_alias=AliasChoices("ACCESS_TOKEN_EXPIRE_MINUTES", "ACCESS_TOKEN_EXPIRE"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, validation_alias=AliasChoices("REFRESH_TOKEN_EXPIRE_DAYS", "REFRESH_TOKEN_EXPIRE"))
    AUTH_RATE_LIMIT_MAX_ATTEMPTS: int = 5
    AUTH_RATE_LIMIT_WINDOW_SECONDS: int = 60

    # API Security & Protection Configuration
    SECURITY_HEADERS_ENABLED: bool = True
    STRICT_TRANSPORT_SECURITY_ENABLED: bool = False
    API_RATE_LIMIT_ENABLED: bool = True
    API_RATE_LIMIT_DEFAULT_PER_MINUTE: int = 10000
    MAX_REQUEST_BODY_BYTES: int = 10 * 1024 * 1024  # 10 MB default max body size
    MAX_PCAP_FILE_BYTES: int = 50 * 1024 * 1024     # 50 MB max PCAP replay size
    ALLOWED_PCAP_EXTENSIONS: List[str] = [".pcap", ".pcapng", ".cap"]

    @field_validator("JWT_SECRET_KEY", mode="after")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if len(v) < 16:
            raise ValueError("JWT_SECRET_KEY must be at least 16 characters long.")
        return v

    # Paths and Directories
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    DATA_DIR: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent.parent / "data", validation_alias=AliasChoices("DATA_DIRECTORY", "DATA_DIR"))
    MODELS_DIR: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent.parent / "ml_models" / "trained", validation_alias=AliasChoices("MODEL_DIRECTORY", "MODELS_DIR"))
    PREPROCESSING_DIR: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent.parent / "ml_models" / "preprocessing", validation_alias=AliasChoices("PREPROCESSING_DIR"))

    # ML Detection Risk Thresholds
    DEFAULT_ANOMALY_THRESHOLD: float = 0.65
    HIGH_RISK_THRESHOLD: float = 0.85
    CRITICAL_RISK_THRESHOLD: float = 0.95

    # Autoencoder Deep Learning Configuration
    AUTOENCODER_EPOCHS: int = 50
    AUTOENCODER_BATCH_SIZE: int = 64
    AUTOENCODER_LEARNING_RATE: float = 0.001
    AUTOENCODER_LATENT_DIM: int = 8
    AUTOENCODER_THRESHOLD_PERCENTILE: float = 95.0
    AUTOENCODER_RANDOM_SEED: int = 42
    AUTOENCODER_EARLY_STOPPING_PATIENCE: int = 10

    # LSTM Sequential Deep Learning Configuration
    LSTM_SEQUENCE_LENGTH: int = 10
    LSTM_SEQUENCE_STRIDE: int = 1
    LSTM_ENCODER_UNITS: int = 64
    LSTM_LATENT_DIM: int = 16
    LSTM_DECODER_UNITS: int = 64
    LSTM_NUM_LAYERS: int = 1
    LSTM_DROPOUT: float = 0.1
    LSTM_LEARNING_RATE: float = 0.001
    LSTM_BATCH_SIZE: int = 32
    LSTM_EPOCHS: int = 40
    LSTM_EARLY_STOPPING_PATIENCE: int = 8
    LSTM_THRESHOLD_PERCENTILE: float = 95.0
    LSTM_RANDOM_SEED: int = 42

    # Random Forest Supervised Baseline Configuration
    RF_N_ESTIMATORS: int = 100
    RF_MAX_DEPTH: Optional[int] = None
    RF_MIN_SAMPLES_SPLIT: int = 2
    RF_MIN_SAMPLES_LEAF: int = 1
    RF_MAX_FEATURES: str = "sqrt"
    RF_CLASS_WEIGHT: Optional[str] = "balanced"
    RF_THRESHOLD: float = 0.5
    RF_RANDOM_SEED: int = 42
    RF_N_JOBS: int = -1

    # Ensemble Detection & Risk Scoring Engine Configuration
    ENSEMBLE_ISOLATION_FOREST_WEIGHT: float = 0.25
    ENSEMBLE_AUTOENCODER_WEIGHT: float = 0.25
    ENSEMBLE_LSTM_WEIGHT: float = 0.25
    ENSEMBLE_RANDOM_FOREST_WEIGHT: float = 0.25
    ENSEMBLE_DECISION_THRESHOLD: float = 50.0
    ENSEMBLE_SEVERITY_LOW_MAX: float = 24.99
    ENSEMBLE_SEVERITY_MEDIUM_MAX: float = 49.99
    ENSEMBLE_SEVERITY_HIGH_MAX: float = 74.99
    ENSEMBLE_SEVERITY_CRITICAL_MIN: float = 75.0
    ENSEMBLE_NORMALIZATION_METHOD: str = "threshold_relative"
    ENSEMBLE_ALLOW_MISSING_MODELS: bool = True

    # Explainable AI (XAI) Configuration
    XAI_ENABLED: bool = True
    XAI_DEFAULT_TOP_K: int = 10
    XAI_ENABLE_SHAP: bool = True
    XAI_ENABLE_ISOLATION_FOREST: bool = True
    XAI_ENABLE_AUTOENCODER: bool = True
    XAI_ENABLE_LSTM: bool = True
    XAI_CACHE_ENABLED: bool = True
    XAI_CACHE_MAX_SIZE: int = 1024
    EXPLAINERS_DIR: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent.parent / "ml_models" / "explainers", validation_alias=AliasChoices("EXPLAINERS_DIR"))
    XAI_EXPERIMENTS_DIR: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent.parent / "experiments" / "explainability", validation_alias=AliasChoices("XAI_EXPERIMENTS_DIR"))

    # Security Alert Engine Configuration
    ALERTS_ENABLED: bool = True
    ALERT_MIN_RISK_SCORE: float = 50.0
    ALERT_LOW_ENABLED: bool = False
    ALERT_MEDIUM_ENABLED: bool = False
    ALERT_HIGH_ENABLED: bool = True
    ALERT_CRITICAL_ENABLED: bool = True
    ALERT_DEDUP_WINDOW_SECONDS: int = 300
    ALERT_GENERATE_XAI_FOR_HIGH: bool = True
    ALERT_GENERATE_XAI_FOR_CRITICAL: bool = True
    ALERT_GENERATE_XAI_FOR_MEDIUM: bool = False
    ALERT_MAX_DESCRIPTION_LENGTH: int = 1000

    # REST API Layer Configuration
    MAX_DETECTION_BATCH_SIZE: int = 500
    MAX_PAGE_SIZE: int = 100
    DEFAULT_PAGE_SIZE: int = 20
    MAX_SEQUENCE_LENGTH: int = 100
    REQUEST_ID_ENABLED: bool = True

    # Real-Time Monitoring & Traffic Ingestion Configuration (Phase 13)
    MONITORING_ENABLED: bool = True
    MONITOR_CAPTURE_INTERFACE: Optional[str] = None
    MONITOR_PACKET_FILTER: str = "tcp or udp"
    MONITOR_FLOW_TIMEOUT_SECONDS: float = 30.0
    MONITOR_FLOW_MAX_PACKETS: int = 1000
    MONITOR_BUFFER_SIZE: int = 10000
    MONITOR_BATCH_SIZE: int = 100
    MONITOR_FLUSH_INTERVAL_SECONDS: float = 1.0
    MONITOR_MAX_PACKETS_PER_PCAP: int = 100000
    MONITOR_RAW_PACKET_STORAGE: bool = False
    MONITOR_PCAP_ALLOWED_DIRECTORY: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parent.parent.parent.parent / "data"
    )
    MONITOR_WORKERS: int = 2
    MONITOR_DEFAULT_DATASET: str = "synthetic"

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env", "../.env", "../../.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in ("production", "prod")


settings = Settings()
