from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class ServiceStatus(BaseModel):
    status: str = "healthy"
    details: Optional[Dict[str, Any]] = None


class MongoDBHealth(BaseModel):
    status: str = Field(..., description="MongoDB status: connected, disconnected, error")
    database: str = Field(..., description="Database name")
    server_type: str = Field(default="unknown", description="standalone, replica_set, mongos, or unknown")
    latency_ms: Optional[float] = Field(default=None, description="Ping latency in milliseconds")
    error: Optional[str] = Field(default=None, description="Error message if any")
    connected: bool = Field(default=False, description="Whether database is connected")


class HealthResponse(BaseModel):
    status: str = Field(..., description="Overall system health status: healthy, degraded, unhealthy")
    database: str = Field(..., description="Database connection state: connected, disconnected, error")
    environment: str = Field(default="development", description="Environment mode")
    timestamp: str = Field(..., description="ISO 8601 formatted timestamp")
    version: str = Field(default="1.0.0", description="API version")
    mongodb: Optional[MongoDBHealth] = Field(default=None, description="Authoritative MongoDB telemetry")
    services: Dict[str, ServiceStatus] = Field(
        default_factory=dict,
        description="Detailed subsystem health metrics"
    )
