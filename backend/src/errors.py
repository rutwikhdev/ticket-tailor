from fastapi import Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    """Base error carrying a machine-readable code and HTTP status."""

    def __init__(self, message: str, code: str, status: int = 422):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status


def error_response(error: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status,
        content={"error": {"code": error.code, "message": error.message, "status": error.status}},
    )


async def domain_error_handler(request: Request, error: DomainError) -> JSONResponse:
    return error_response(error)


async def validation_error_handler(request: Request, error: ValueError) -> JSONResponse:
    return error_response(DomainError(str(error), "VALIDATION_ERROR", 422))


async def unhandled_error_handler(request: Request, error: Exception) -> JSONResponse:
    return error_response(DomainError("The request could not be completed.", "INTERNAL_ERROR", 500))
