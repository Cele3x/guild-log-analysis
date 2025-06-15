"""Tests for authentication functionality."""

import pytest
from unittest.mock import Mock, patch, mock_open
import json
import requests
from datetime import datetime, timedelta

from src.guild_log_analysis.api.auth import TokenManager, OAuthAuthenticator, get_access_token
from src.guild_log_analysis.api.exceptions import AuthenticationError


class TestTokenManager:
    """Test cases for TokenManager class."""
    
    def setup_method(self):
        """Setup method run before each test."""
        self.test_token_cache_file = "tests/cache/test_token_cache.json"
        self.test_cache_files_to_cleanup = []
    
    def teardown_method(self):
        """Teardown method run after each test to clean up cache files."""
        import os
        # Clean up test cache files
        cache_files_to_remove = [self.test_token_cache_file]
        
        for cache_file in cache_files_to_remove:
            if os.path.exists(cache_file):
                try:
                    os.remove(cache_file)
                except OSError:
                    pass  # Ignore cleanup errors
        
        # Clean up any additional cache files tracked during tests
        for cache_file in self.test_cache_files_to_cleanup:
            if os.path.exists(cache_file):
                try:
                    os.remove(cache_file)
                except OSError:
                    pass
    
    def test_init_with_default_cache_file(self):
        """Test TokenManager initialization with default cache file."""
        token_manager = TokenManager()
        assert token_manager.cache_file is not None
    
    def test_init_with_custom_cache_file(self):
        """Test TokenManager initialization with custom cache file."""
        custom_file = "custom_token_cache.json"
        token_manager = TokenManager(custom_file)
        assert token_manager.cache_file == custom_file
    
    @patch('os.path.exists', return_value=False)
    def test_load_cached_token_no_file(self, mock_exists):
        """Test loading cached token when file doesn't exist."""
        token_manager = TokenManager()
        result = token_manager.load_cached_token()
        assert result is None
    
    @patch('builtins.open', new_callable=mock_open, read_data='invalid json')
    @patch('os.path.exists', return_value=True)
    def test_load_cached_token_invalid_json(self, mock_exists, mock_file):
        """Test loading cached token with invalid JSON."""
        token_manager = TokenManager()
        result = token_manager.load_cached_token()
        assert result is None
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists', return_value=True)
    def test_load_cached_token_expired(self, mock_exists, mock_file):
        """Test loading expired cached token."""
        # Create expired token data
        expired_time = datetime.now() - timedelta(hours=1)
        cache_data = {
            'access_token': 'expired_token',
            'expires_at': expired_time.isoformat()
        }
        mock_file.return_value.read.return_value = json.dumps(cache_data)
        
        token_manager = TokenManager()
        result = token_manager.load_cached_token()
        assert result is None
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists', return_value=True)
    def test_load_cached_token_valid(self, mock_exists, mock_file):
        """Test loading valid cached token."""
        # Create valid token data
        future_time = datetime.now() + timedelta(hours=1)
        cache_data = {
            'access_token': 'valid_token',
            'expires_at': future_time.isoformat()
        }
        mock_file.return_value.read.return_value = json.dumps(cache_data)
        
        token_manager = TokenManager()
        result = token_manager.load_cached_token()
        assert result == 'valid_token'
    
    @patch('builtins.open', new_callable=mock_open)
    def test_save_token_to_cache(self, mock_file):
        """Test saving token to cache."""
        token_manager = TokenManager()
        access_token = "test_token"
        expires_in = 3600
        
        token_manager.save_token_to_cache(access_token, expires_in)
        
        # Verify file was opened for writing (check if the cache file was in the calls)
        cache_file_calls = [call for call in mock_file.call_args_list 
                           if len(call[0]) > 0 and str(call[0][0]).endswith('token_cache.json')]
        assert len(cache_file_calls) == 1
        assert cache_file_calls[0] == ((token_manager.cache_file, 'w'), {'encoding': 'utf-8'})
        
        # Verify JSON was written
        handle = mock_file.return_value.__enter__.return_value
        handle.write.assert_called()


class TestOAuthAuthenticator:
    """Test cases for OAuthAuthenticator class."""
    
    def test_init_with_default_token_manager(self):
        """Test OAuthAuthenticator initialization with default token manager."""
        authenticator = OAuthAuthenticator()
        assert authenticator.token_manager is not None
    
    def test_init_with_custom_token_manager(self):
        """Test OAuthAuthenticator initialization with custom token manager."""
        custom_manager = Mock(spec=TokenManager)
        authenticator = OAuthAuthenticator(custom_manager)
        assert authenticator.token_manager == custom_manager
    
    @patch.object(TokenManager, 'load_cached_token')
    def test_get_access_token_from_cache(self, mock_load_token):
        """Test getting access token from cache."""
        mock_load_token.return_value = "cached_token"
        
        authenticator = OAuthAuthenticator()
        result = authenticator.get_access_token()
        
        assert result == "cached_token"
        mock_load_token.assert_called_once()
    
    @patch.object(TokenManager, 'load_cached_token', return_value=None)
    @patch.object(OAuthAuthenticator, '_perform_oauth_flow')
    def test_get_access_token_oauth_flow(self, mock_oauth_flow, mock_load_token):
        """Test getting access token via OAuth flow."""
        mock_oauth_flow.return_value = "new_token"
        
        authenticator = OAuthAuthenticator()
        result = authenticator.get_access_token()
        
        assert result == "new_token"
        mock_load_token.assert_called_once()
        mock_oauth_flow.assert_called_once()
    
    def test_generate_pkce_params(self):
        """Test PKCE parameter generation."""
        code_verifier, code_challenge = OAuthAuthenticator._generate_pkce_params()
        
        assert isinstance(code_verifier, str)
        assert isinstance(code_challenge, str)
        assert len(code_verifier) > 0
        assert len(code_challenge) > 0
        assert code_verifier != code_challenge
    
    @patch('src.guild_log_analysis.api.auth.Settings')
    def test_build_auth_url(self, mock_settings_class):
        """Test authorization URL building."""
        mock_settings = Mock()
        mock_settings.warcraft_logs_client_id = "test_client_id"
        mock_settings.auth_url = "https://example.com/auth"
        # Add cache_directory for TokenManager
        from pathlib import Path
        mock_settings.cache_directory = Path("cache")
        mock_settings_class.return_value = mock_settings
        
        authenticator = OAuthAuthenticator()
        code_challenge = "test_challenge"
        url = authenticator._build_auth_url(code_challenge)
        
        assert "test_client_id" in url
        assert "test_challenge" in url
        assert "https://example.com/auth" in url
    
    @patch('requests.post')
    @patch('src.guild_log_analysis.config.settings.Settings')
    def test_exchange_code_for_token_success(self, mock_settings_class, mock_post):
        """Test successful token exchange."""
        mock_settings = Mock()
        mock_settings.token_url = "https://example.com/token"
        mock_settings.warcraft_logs_client_id = "test_client_id"
        mock_settings.warcraft_logs_client_secret = "test_secret"
        mock_settings_class.return_value = mock_settings
        
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'new_token',
            'expires_in': 3600
        }
        mock_post.return_value = mock_response
        
        authenticator = OAuthAuthenticator()
        result = authenticator._exchange_code_for_token("auth_code", "code_verifier")
        
        assert result['access_token'] == 'new_token'
        assert result['expires_in'] == 3600
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_exchange_code_for_token_failure(self, mock_post):
        """Test failed token exchange."""
        mock_post.side_effect = requests.RequestException("Network error")
        
        authenticator = OAuthAuthenticator()
        
        with pytest.raises(AuthenticationError):
            authenticator._exchange_code_for_token("auth_code", "code_verifier")


class TestGetAccessToken:
    """Test cases for get_access_token convenience function."""
    
    @patch('src.guild_log_analysis.api.auth.Settings')
    @patch.object(OAuthAuthenticator, 'get_access_token')
    def test_get_access_token(self, mock_get_token, mock_settings_class):
        """Test get_access_token convenience function."""
        # Mock settings to provide required OAuth configuration
        from pathlib import Path
        mock_settings = Mock()
        mock_settings.warcraft_logs_client_id = "test_client_id"
        mock_settings.warcraft_logs_client_secret = "test_client_secret"
        mock_settings.cache_directory = Path("cache")
        mock_settings_class.return_value = mock_settings
        
        mock_get_token.return_value = "test_token"
        
        result = get_access_token()
        
        assert result == "test_token"
        mock_get_token.assert_called_once()
    
    @patch('src.guild_log_analysis.api.auth.Settings')
    def test_get_access_token_missing_client_id(self, mock_settings_class):
        """Test get_access_token with missing client ID."""
        mock_settings = Mock()
        mock_settings.warcraft_logs_client_id = None
        mock_settings.warcraft_logs_client_secret = "test_secret"
        mock_settings_class.return_value = mock_settings
        
        with pytest.raises(AuthenticationError) as exc_info:
            get_access_token()
        
        assert "WOW_CLIENT_ID environment variable is required" in str(exc_info.value)
