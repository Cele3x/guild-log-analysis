"""
Custom exceptions for WoW Guild Analysis API.

This module defines custom exception classes for better error handling
and debugging throughout the application.
"""

from typing import Any, Optional


class WoWAnalysisError(Exception):
    """Base exception class for WoW Guild Analysis."""

    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        """
        Initialize the exception.

        :param message: Error message
        :param details: Optional additional details about the error
        """
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        """Return string representation of the exception."""
        if self.details:
            return f"{self.message}. Details: {self.details}"
        return self.message


class APIError(WoWAnalysisError):
    """Exception raised for API-related errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Any] = None,
    ) -> None:
        """
        Initialize the API exception.

        :param message: Error message
        :param status_code: HTTP status code if applicable
        :param response_data: Response data from the API
        """
        super().__init__(message, response_data)
        self.status_code = status_code
        self.response_data = response_data


class AuthenticationError(APIError):
    """Exception raised for authentication-related errors."""

    pass


class RateLimitError(APIError):
    """Exception raised when API rate limit is exceeded."""

    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs) -> None:
        """
        Initialize the rate limit exception.

        :param message: Error message
        :param retry_after: Seconds to wait before retrying
        :param kwargs: Additional arguments for parent class
        """
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class CacheError(WoWAnalysisError):
    """Exception raised for cache-related errors."""

    pass


class AnalysisError(WoWAnalysisError):
    """Exception raised for analysis-related errors."""

    pass


class DataNotFoundError(AnalysisError):
    """Exception raised when expected data is not found."""

    pass


class InvalidDataError(AnalysisError):
    """Exception raised when data is invalid or corrupted."""

    pass


class PlotError(WoWAnalysisError):
    """Exception raised for plotting-related errors."""

    pass


class ConfigurationError(WoWAnalysisError):
    """Exception raised for configuration-related errors."""

    pass
