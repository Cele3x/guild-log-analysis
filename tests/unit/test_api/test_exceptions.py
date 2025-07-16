"""Tests for API exceptions."""

from src.guild_log_analysis.api.exceptions import (
    APIError,
    AuthenticationError,
    ConfigurationError,
    RateLimitError,
    WoWAnalysisError,
)


class TestWoWAnalysisError:
    """Test cases for WoWAnalysisError base exception."""

    def test_init_with_message_only(self):
        """Test exception initialization with message only."""
        message = "Test error message"
        error = WoWAnalysisError(message)

        assert error.message == message
        assert error.details is None
        assert str(error) == message

    def test_init_with_message_and_details(self):
        """Test exception initialization with message and details."""
        message = "Test error message"
        details = {"key": "value"}
        error = WoWAnalysisError(message, details)

        assert error.message == message
        assert error.details == details
        assert str(error) == f"{message}. Details: {details}"

    def test_inheritance(self):
        """Test that WoWAnalysisError inherits from Exception."""
        error = WoWAnalysisError("test")
        assert isinstance(error, Exception)


class TestAPIError:
    """Test cases for APIError exception."""

    def test_init_with_message_only(self):
        """Test APIError initialization with message only."""
        message = "API error"
        error = APIError(message)

        assert error.message == message
        assert error.status_code is None
        assert error.response_data is None

    def test_init_with_all_parameters(self):
        """Test APIError initialization with all parameters."""
        message = "API error"
        status_code = 500
        response_data = {"error": "Internal server error"}

        error = APIError(message, status_code, response_data)

        assert error.message == message
        assert error.status_code == status_code
        assert error.response_data == response_data
        assert error.details == response_data

    def test_inheritance(self):
        """Test that APIError inherits from WoWAnalysisError."""
        error = APIError("test")
        assert isinstance(error, WoWAnalysisError)


class TestAuthenticationError:
    """Test cases for AuthenticationError exception."""

    def test_inheritance(self):
        """Test that AuthenticationError inherits from APIError."""
        error = AuthenticationError("auth error")
        assert isinstance(error, APIError)
        assert isinstance(error, WoWAnalysisError)


class TestRateLimitError:
    """Test cases for RateLimitError exception."""

    def test_init_with_retry_after(self):
        """Test RateLimitError initialization with retry_after."""
        message = "Rate limit exceeded"
        retry_after = 60
        status_code = 429

        error = RateLimitError(message, retry_after=retry_after, status_code=status_code)

        assert error.message == message
        assert error.retry_after == retry_after
        assert error.status_code == status_code

    def test_init_without_retry_after(self):
        """Test RateLimitError initialization without retry_after."""
        message = "Rate limit exceeded"
        error = RateLimitError(message)

        assert error.message == message
        assert error.retry_after is None

    def test_inheritance(self):
        """Test that RateLimitError inherits from APIError."""
        error = RateLimitError("rate limit error")
        assert isinstance(error, APIError)
        assert isinstance(error, WoWAnalysisError)


class TestConfigurationError:
    """Test cases for ConfigurationError exception."""

    def test_inheritance(self):
        """Test that ConfigurationError inherits from WoWAnalysisError."""
        error = ConfigurationError("config error")
        assert isinstance(error, WoWAnalysisError)
