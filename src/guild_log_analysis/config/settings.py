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
        return os.getenv("CLIENT_ID")

    @property
    def redirect_uri(self) -> str:
        """Get OAuth redirect URI."""
        return os.getenv("REDIRECT_URI", DEFAULT_REDIRECT_URI)

    # Cache Configuration
    @property
    def cache_directory(self) -> Path:
        """Get cache directory path."""
        cache_dir = os.getenv("CACHE_DIRECTORY", "cache")
        return Path(cache_dir)

    # Output Configuration
    @property
    def output_directory(self) -> Path:
        """Get output directory for plots and reports."""
        output_dir = os.getenv("OUTPUT_DIRECTORY", "output")
        return Path(output_dir)

    @property
    def plots_directory(self) -> Path:
        """Get plots output directory."""
        return self.output_directory

    # Logging Configuration
    @property
    def log_level(self) -> str:
        """Get logging level."""
        return os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL)

    @property
    def log_file(self) -> Path:
        """Get log file path."""
        log_file = os.getenv("LOG_FILE", DEFAULT_LOG_FILE)
        return Path(log_file)

    @property
    def log_format(self) -> str:
        """Get log format string."""
        return os.getenv("LOG_FORMAT", DEFAULT_LOG_FORMAT)

    # Player Configuration
    @property
    def melee_dps_players(self) -> set[str]:
        """Get set of melee DPS player names."""
        melee_players_str = os.getenv(
            "MELEE_DPS_PLAYERS",
            "Daarkin,Kazzekus,Kaschy,Kâsandra,Playpala,Doløød,Ixany,Phipsi,Nudelbeißer,Dämonir,Cranekickzdh,Arthios",
        )
        return {name.strip() for name in melee_players_str.split(",") if name.strip()}

    @property
    def ignored_players(self) -> set[str]:
        """Get set of player names to ignore in plots."""
        ignored_players_str = os.getenv("IGNORED_PLAYERS", "Ilagi,Sinayan,Tåygeta,Kaschyma,Zwerggo")
        return {name.strip() for name in ignored_players_str.split(",") if name.strip()}
