from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationMetadata(BaseModel):
    """Standard pagination metadata model."""
    page: int = Field(1, ge=1, description="Current page number (1-indexed)")
    page_size: int = Field(20, ge=1, le=500, description="Number of items per page")
    total: int = Field(0, ge=0, description="Total matching items count")
    total_pages: int = Field(1, ge=0, description="Total number of pages")


class APIResponse(BaseModel, Generic[T]):
    """Standardized single-resource API response wrapper."""
    success: bool = Field(default=True, description="Indicates whether the request was successful")
    data: T = Field(..., description="Response payload data")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standardized paginated list response wrapper."""
    success: bool = Field(default=True, description="Indicates whether the request was successful")
    data: List[T] = Field(default_factory=list, description="List of items for current page")
    pagination: PaginationMetadata = Field(..., description="Pagination metadata")


class APIErrorDetail(BaseModel):
    """Detailed error structure."""
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error explanation")
    details: Optional[Any] = Field(None, description="Detailed validation or contextual errors")
    request_id: Optional[str] = Field(None, description="Correlation request ID")


class APIErrorResponse(BaseModel):
    """Standardized error response payload."""
    success: bool = Field(default=False)
    error: APIErrorDetail
