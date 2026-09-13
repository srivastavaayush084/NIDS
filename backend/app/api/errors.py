from typing import Any, Dict
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.core.logging import logger


def register_exception_handlers(app: FastAPI) -> None:
    """Register centralized exception handlers for standardized JSON error responses."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": detail,
                    "status_code": exc.status_code,
                    "request_id": request_id,
                },
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        errors = []
        for err in exc.errors():
            loc = " -> ".join([str(p) for p in err.get("loc", [])])
            errors.append({
                "location": loc,
                "message": err.get("msg", "Invalid value"),
                "type": err.get("type", "validation_error"),
            })

        logger.warning(f"[{request_id}] Validation failure on {request.method} {request.url.path}: {errors}")

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request payload validation failed.",
                    "details": errors,
                    "request_id": request_id,
                },
            },
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        logger.warning(f"[{request_id}] Bad request (ValueError) on {request.method} {request.url.path}: {exc}")

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "error": {
                    "code": "BAD_REQUEST",
                    "message": str(exc),
                    "request_id": request_id,
                },
            },
        )

    @app.exception_handler(KeyError)
    async def key_error_handler(request: Request, exc: KeyError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        clean_exc = str(exc).strip("'\"")
        msg = f"Requested resource not found: {clean_exc}"
        logger.info(f"[{request_id}] Resource not found (KeyError) on {request.method} {request.url.path}: {msg}")

        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "error": {
                    "code": "RESOURCE_NOT_FOUND",
                    "message": msg,
                    "request_id": request_id,
                },
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        logger.error(f"[{request_id}] Unhandled error on {request.method} {request.url.path}: {exc}", exc_info=True)

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected internal server error occurred.",
                    "request_id": request_id,
                },
            },
        )
