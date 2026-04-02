"""
Custom DRF exception handler.

Adds consistent error response formatting and logs server errors.
"""

import logging

from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Wrap DRF's default exception handler with:
      - Consistent { "detail": ..., "code": ... } envelope
      - Server-error logging
    """
    response = exception_handler(exc, context)

    if response is not None:
        # Ensure every error has a 'code' field
        if isinstance(response.data, dict) and "code" not in response.data:
            response.data["code"] = getattr(
                exc, "default_code", f"error_{response.status_code}"
            )
    else:
        # Unhandled exception — log and let Django return 500
        logger.exception(
            "Unhandled exception in %s",
            context.get("view", "unknown view"),
            exc_info=exc,
        )

    return response
