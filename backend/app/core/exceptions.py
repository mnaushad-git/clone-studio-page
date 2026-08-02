"""Typed application exceptions mapped to the standard error envelope by core/errors.py."""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base class for all application-raised errors with a stable error code."""

    code: str = "INTERNAL_ERROR"
    status_code: int = 500
    message: str = "An unexpected error occurred."

    def __init__(
        self, message: str | None = None, *, details: list[dict[str, Any]] | None = None
    ) -> None:
        super().__init__(message or self.message)
        if message:
            self.message = message
        self.details = details


class ValidationAppError(AppError):
    code = "VALIDATION_ERROR"
    status_code = 422
    message = "Request validation failed."


class NotFoundError(AppError):
    code = "NOT_FOUND"
    status_code = 404
    message = "Resource not found."


class UnauthorizedError(AppError):
    code = "UNAUTHORIZED"
    status_code = 401
    message = "Authentication is required."


class ForbiddenError(AppError):
    code = "FORBIDDEN"
    status_code = 403
    message = "You do not have permission to perform this action."


class ConflictError(AppError):
    code = "CONFLICT"
    status_code = 409
    message = "The request conflicts with the current state of the resource."


class RateLimitedError(AppError):
    code = "RATE_LIMITED"
    status_code = 429
    message = "Too many requests."


class UpstreamUnavailableError(AppError):
    code = "UPSTREAM_UNAVAILABLE"
    status_code = 503
    message = "A required upstream dependency is unavailable."


class PaymentDeclinedError(AppError):
    code = "PAYMENT_DECLINED"
    status_code = 402
    message = "Payment was declined."
