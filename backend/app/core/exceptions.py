from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.core.logging import logger


class AppException(Exception):
    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class DatabaseConnectionException(AppException):
    def __init__(self, message: str = "Database connection failed", details: dict | None = None):
        super().__init__(message, status_code=status.HTTP_503_SERVICE_UNAVAILABLE, details=details)


class ResourceNotFoundException(AppException):
    def __init__(self, message: str = "Resource not found", details: dict | None = None):
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND, details=details)


class BadRequestException(AppException):
    def __init__(self, message: str = "Bad request", details: dict | None = None):
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST, details=details)


class ValidationException(AppException):
    def __init__(self, message: str = "Validation failed", details: dict | None = None):
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST, details=details)


class SecurityException(AppException):
    def __init__(self, message: str = "Access denied due to security policy", details: dict | None = None):
        super().__init__(message, status_code=status.HTTP_403_FORBIDDEN, details=details)



async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    logger.error(f"Application error on {request.method} {request.url.path}: {exc.message} (status: {exc.status_code})")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.__class__.__name__,
                "message": exc.message,
                "details": exc.details,
            },
        },
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.warning(f"Validation error on {request.method} {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "ValidationError",
                "message": "Input validation failed",
                "details": exc.errors(),
            },
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(f"Unhandled server error on {request.method} {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "InternalServerError",
                "message": "An unexpected internal server error occurred.",
                "details": {},
            },
        },
    )
