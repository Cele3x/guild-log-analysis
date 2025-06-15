"""
Settings module for Guild Log Analysis.

This module handles configuration management using environment variables
and provides default values for all settings.
"""

import os
from pathlib import Path
from typing import Optional

from .constants import (
    API_BASE_URL,
    AUTH_URL,
    DEFAULT_LOG_FILE,
    DEFAULT_LOG_FORMAT,
    DEFAULT_LOG_LEVEL,
    DEFAULT_REDIRECT_URI,
    DEFAULT_TIMEOUT,
    TOKEN_URL,
)


class Settings:
    """Application settings with environment variable support."""

    def __init__(self) -> None:
        """Initialize settings from environment variables."""
        self._load_env_file()

    def _load_env_file(self) -> None:
        """Load environment variables from .env file if it exists."""
        env_file = Path(".env")
        if env_file.exists():
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ.setdefault(key.strip(), value.strip())

    # API Configuration
    @property
    def api_url(self) -> str:
        """Get API URL."""
        return os.getenv("WARCRAFT_LOGS_API_URL", API_BASE_URL)

    @property
    def auth_url(self) -> str:
        """Get authentication URL."""
        return AUTH_URL

    @property
    def token_url(self) -> str:
        """Get token URL."""
        return TOKEN_URL

    @property
    def warcraft_logs_client_id(self) -> Optional[str]:
        """Get Warcraft Logs client ID."""
        return os.getenv("WOW_CLIENT_ID")

    @property
    def redirect_uri(self) -> str:
        """Get OAuth redirect URI."""
        return os.getenv("WOW_REDIRECT_URI", DEFAULT_REDIRECT_URI)

    @property
    def request_timeout(self) -> int:
        """Get request timeout in seconds."""
        return int(os.getenv("REQUEST_TIMEOUT", DEFAULT_TIMEOUT))

    # Cache Configuration
    @property
    def cache_enabled(self) -> bool:
        """Check if caching is enabled."""
        return os.getenv("CACHE_ENABLED", "true").lower() == "true"

    @property
    def cache_directory(self) -> Path:
        """Get cache directory path."""
        cache_dir = os.getenv("CACHE_DIRECTORY", "cache")
        return Path(cache_dir)

    @property
    def cache_ttl(self) -> int:
        """Get cache TTL in seconds."""
        return int(os.getenv("CACHE_TTL", "3600"))  # 1 hour default

    # Output Configuration
    @property
    def output_directory(self) -> Path:
        """Get output directory for plots and reports."""
        output_dir = os.getenv("OUTPUT_DIRECTORY", "output")
        return Path(output_dir)

    @property
    def plots_directory(self) -> Path:
        """Get plots output directory."""
        return self.output_directory / "plots"

    @property
    def reports_directory(self) -> Path:
        """Get reports output directory."""
        return self.output_directory / "reports"

    # Logging Configuration
    @property
    def log_level(self) -> str:
        """Get logging level."""
        return os.getenv("WOW_LOG_LEVEL", DEFAULT_LOG_LEVEL)

    @property
    def log_file(self) -> Path:
        """Get log file path."""
        log_file = os.getenv("WOW_LOG_FILE", DEFAULT_LOG_FILE)
        return Path(log_file)

    @property
    def log_format(self) -> str:
        """Get log format string."""
        return os.getenv("WOW_LOG_FORMAT", DEFAULT_LOG_FORMAT)
