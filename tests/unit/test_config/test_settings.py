"""Tests for settings configuration."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.guild_log_analysis.config.settings import Settings


class TestSettings:
    """Test cases for Settings class."""

    def test_init_loads_env_file(self):
        """Test that Settings loads environment variables from .env file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_content = """
CLIENT_ID=test_client_id
LOG_LEVEL=DEBUG
MELEE_DPS_PLAYERS=Player1,Player2,Player3
IGNORED_PLAYERS=IgnoredPlayer1,IgnoredPlayer2
"""
            env_file.write_text(env_content.strip())

            with patch("src.guild_log_analysis.config.settings.Path") as mock_path_class:
                # Mock Path constructor to return our test file
                mock_path_instance = env_file
                mock_path_class.return_value = mock_path_instance

                # Store original environment to restore later
                original_env = os.environ.copy()
                try:
                    # Clear relevant env vars to test .env file loading
                    for key in ["CLIENT_ID", "LOG_LEVEL"]:
                        os.environ.pop(key, None)

                    settings = Settings()

                    # Should have loaded values from .env file
                    assert settings.warcraft_logs_client_id == "test_client_id"
                    assert settings.log_level == "DEBUG"
                finally:
                    # Restore original environment
                    os.environ.clear()
                    os.environ.update(original_env)

    def test_env_file_missing(self):
        """Test behavior when .env file doesn't exist."""
        with patch("src.guild_log_analysis.config.settings.Path") as mock_path_class:
            # Mock a non-existent file
            mock_path_instance = Path("/non/existent/.env")
            mock_path_class.return_value = mock_path_instance

            # Should not raise error when .env file is missing
            settings = Settings()

            # Should use default values
            assert settings.log_level == "INFO"  # Default from constants

    def test_warcraft_logs_client_id(self):
        """Test Warcraft Logs client ID property."""
        with patch.dict(os.environ, {"CLIENT_ID": "test_client_123"}, clear=False):
            settings = Settings()
            assert settings.warcraft_logs_client_id == "test_client_123"

    def test_warcraft_logs_client_id_missing(self):
        """Test client ID missing returns None."""
        # Clear environment and don't load .env file
        with patch.dict(os.environ, {}, clear=True):
            with patch("src.guild_log_analysis.config.settings.Path") as mock_path_class:
                mock_path_instance = Path("/non/existent/.env")
                mock_path_class.return_value = mock_path_instance

                settings = Settings()
                # Should return None when CLIENT_ID is not set
                assert settings.warcraft_logs_client_id is None

    def test_redirect_uri_default(self):
        """Test redirect URI uses default when not set."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("src.guild_log_analysis.config.settings.Path") as mock_path_class:
                mock_path_instance = Path("/non/existent/.env")
                mock_path_class.return_value = mock_path_instance

                settings = Settings()
                assert settings.redirect_uri == "http://localhost:8080"

    def test_redirect_uri_custom(self):
        """Test redirect URI uses custom value when set."""
        with patch.dict(os.environ, {"REDIRECT_URI": "http://example.com/callback"}, clear=False):
            settings = Settings()
            assert settings.redirect_uri == "http://example.com/callback"

    def test_cache_directory_default(self):
        """Test cache directory uses default when not set."""
        with patch.dict(os.environ, {"CLIENT_ID": "test_id"}, clear=True):
            settings = Settings()
            assert settings.cache_directory == Path("cache")

    def test_cache_directory_custom(self):
        """Test cache directory uses custom value when set."""
        with patch.dict(os.environ, {"CACHE_DIRECTORY": "/custom/cache"}, clear=False):
            settings = Settings()
            assert settings.cache_directory == Path("/custom/cache")

    def test_output_directory_default(self):
        """Test output directory uses default when not set."""
        with patch.dict(os.environ, {"CLIENT_ID": "test_id"}, clear=True):
            settings = Settings()
            assert settings.output_directory == Path("output")

    def test_output_directory_custom(self):
        """Test output directory uses custom value when set."""
        with patch.dict(os.environ, {"OUTPUT_DIRECTORY": "/custom/output"}, clear=False):
            settings = Settings()
            assert settings.output_directory == Path("/custom/output")

    def test_plots_directory_matches_output(self):
        """Test plots directory matches output directory."""
        with patch.dict(os.environ, {"OUTPUT_DIRECTORY": "/test/output"}, clear=False):
            settings = Settings()
            assert settings.plots_directory == settings.output_directory

    def test_log_level_default(self):
        """Test log level uses default when not set."""
        with patch.dict(os.environ, {"CLIENT_ID": "test_id"}, clear=True):
            settings = Settings()
            assert settings.log_level == "INFO"

    def test_log_level_custom(self):
        """Test log level uses custom value when set."""
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}, clear=False):
            settings = Settings()
            assert settings.log_level == "DEBUG"

    def test_log_file_default(self):
        """Test log file uses default when not set."""
        with patch.dict(os.environ, {"CLIENT_ID": "test_id"}, clear=True):
            settings = Settings()
            assert settings.log_file == Path("logs/wow_analysis.log")

    def test_log_file_custom(self):
        """Test log file uses custom value when set."""
        with patch.dict(os.environ, {"LOG_FILE": "/custom/log.log"}, clear=False):
            settings = Settings()
            assert settings.log_file == Path("/custom/log.log")

    def test_melee_dps_players_default(self):
        """Test melee DPS players uses default when not set."""
        with patch.dict(os.environ, {"CLIENT_ID": "test_id"}, clear=True):
            settings = Settings()
            # Should have default melee DPS players
            assert len(settings.melee_dps_players) > 0

    def test_melee_dps_players_custom(self):
        """Test melee DPS players uses custom value when set."""
        with patch.dict(os.environ, {"MELEE_DPS_PLAYERS": "Player1,Player2,Player3"}, clear=False):
            settings = Settings()
            assert settings.melee_dps_players == {"Player1", "Player2", "Player3"}

    def test_ignored_players_default(self):
        """Test ignored players uses default when not set."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            # Should have default ignored players from constants
            expected_players = {"Ilagi", "Sinayan", "Tåygeta", "Kaschyma", "Zwerggo"}
            assert settings.ignored_players == expected_players

    def test_ignored_players_custom(self):
        """Test ignored players uses custom value when set."""
        with patch.dict(os.environ, {"IGNORED_PLAYERS": "Player1,Player2"}, clear=False):
            settings = Settings()
            assert settings.ignored_players == {"Player1", "Player2"}


class TestEnvFileProcessing:
    """Test cases for .env file processing functionality."""

    def test_env_file_comments_ignored(self):
        """Test that comments in .env file are ignored."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_content = """
# This is a comment
CLIENT_ID=test_client_id
# Another comment
LOG_LEVEL=DEBUG
"""
            env_file.write_text(env_content.strip())

            with patch("src.guild_log_analysis.config.settings.Path") as mock_path_class:
                mock_path_class.return_value = env_file

                original_env = os.environ.copy()
                try:
                    for key in ["CLIENT_ID", "LOG_LEVEL"]:
                        os.environ.pop(key, None)

                    settings = Settings()
                    assert settings.warcraft_logs_client_id == "test_client_id"
                    assert settings.log_level == "DEBUG"
                finally:
                    os.environ.clear()
                    os.environ.update(original_env)

    def test_env_file_empty_lines_ignored(self):
        """Test that empty lines in .env file are ignored."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_content = """

CLIENT_ID=test_client_id

LOG_LEVEL=DEBUG

"""
            env_file.write_text(env_content)

            with patch("src.guild_log_analysis.config.settings.Path") as mock_path_class:
                mock_path_class.return_value = env_file

                original_env = os.environ.copy()
                try:
                    for key in ["CLIENT_ID", "LOG_LEVEL"]:
                        os.environ.pop(key, None)

                    settings = Settings()
                    assert settings.warcraft_logs_client_id == "test_client_id"
                    assert settings.log_level == "DEBUG"
                finally:
                    os.environ.clear()
                    os.environ.update(original_env)

    def test_env_file_malformed_lines_ignored(self):
        """Test that malformed lines in .env file are ignored."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_content = """
CLIENT_ID=test_client_id
MALFORMED_LINE_WITHOUT_EQUALS
LOG_LEVEL=DEBUG
ANOTHER=MALFORMED=LINE=WITH=MULTIPLE=EQUALS
"""
            env_file.write_text(env_content.strip())

            with patch("src.guild_log_analysis.config.settings.Path") as mock_path_class:
                mock_path_class.return_value = env_file

                original_env = os.environ.copy()
                try:
                    for key in ["CLIENT_ID", "LOG_LEVEL"]:
                        os.environ.pop(key, None)

                    settings = Settings()
                    assert settings.warcraft_logs_client_id == "test_client_id"
                    assert settings.log_level == "DEBUG"
                finally:
                    os.environ.clear()
                    os.environ.update(original_env)

    def test_env_file_duplicate_keys(self):
        """Test that duplicate keys in .env file use the first value (setdefault behavior)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_content = """
CLIENT_ID=first_value
LOG_LEVEL=INFO
CLIENT_ID=final_value
"""
            env_file.write_text(env_content.strip())

            with patch("src.guild_log_analysis.config.settings.Path") as mock_path_class:
                mock_path_class.return_value = env_file

                original_env = os.environ.copy()
                try:
                    for key in ["CLIENT_ID", "LOG_LEVEL"]:
                        os.environ.pop(key, None)

                    settings = Settings()
                    # setdefault() keeps first value, so first_value should be used
                    assert settings.warcraft_logs_client_id == "first_value"
                finally:
                    os.environ.clear()
                    os.environ.update(original_env)

    def test_env_vars_override_env_file(self):
        """Test that environment variables override .env file values."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_content = """
CLIENT_ID=env_file_value
LOG_LEVEL=ERROR
"""
            env_file.write_text(env_content.strip())

            with patch("src.guild_log_analysis.config.settings.Path") as mock_path_class:
                mock_path_class.return_value = env_file

                # Set environment variable that should override .env file
                with patch.dict(os.environ, {"CLIENT_ID": "env_var_value"}, clear=False):
                    settings = Settings()
                    # Environment variable should take precedence
                    assert settings.warcraft_logs_client_id == "env_var_value"
