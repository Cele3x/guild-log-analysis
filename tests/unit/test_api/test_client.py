"""Tests for API client functionality."""

import pytest
from unittest.mock import Mock, patch, mock_open
import json
import requests
from requests.exceptions import RequestException

from src.guild_log_analysis.api.client import WarcraftLogsAPIClient, CacheManager, RateLimiter
from src.guild_log_analysis.api.exceptions import APIError, AuthenticationError, RateLimitError


class TestCacheManager:
    """Test cases for CacheManager class."""
    
    def setup_method(self):
        """Setup method run before each test."""
        self.test_cache_file = "tests/cache/test_cache.json"
        self.test_cache_files_to_cleanup = []
    
    def teardown_method(self):
        """Teardown method run after each test to clean up cache files."""
        import os
        # Clean up test cache files
        cache_files_to_remove = [
            self.test_cache_file,
            f"{self.test_cache_file}.1",
            f"{self.test_cache_file}.2",
            f"{self.test_cache_file}.3",
            f"{self.test_cache_file}.4",
            f"{self.test_cache_file}.5"
        ]
        
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
        """Test CacheManager initialization with default cache file."""
        cache_manager = CacheManager()
        assert cache_manager.cache_file is not None
        assert isinstance(cache_manager.cache, dict)
    
    def test_init_with_custom_cache_file(self):
        """Test CacheManager initialization with custom cache file."""
        custom_file = "custom_cache.json"
        cache_manager = CacheManager(custom_file)
        assert cache_manager.cache_file == custom_file
    
    @patch('builtins.open', new_callable=mock_open, read_data='{"test": "data"}')
    @patch('os.path.exists', return_value=True)
    def test_load_cache_success(self, mock_exists, mock_file):
        """Test successful cache loading."""
        cache_manager = CacheManager("test_cache.json")
        assert cache_manager.cache == {"test": "data"}
    
    @patch('builtins.open', new_callable=mock_open, read_data='invalid json')
    @patch('os.path.exists', return_value=True)
    def test_load_cache_invalid_json(self, mock_exists, mock_file):
        """Test cache loading with invalid JSON."""
        cache_manager = CacheManager("test_cache.json")
        assert cache_manager.cache == {}
    
    @patch('os.path.exists', return_value=False)
    def test_load_cache_file_not_exists(self, mock_exists):
        """Test cache loading when file doesn't exist."""
        cache_manager = CacheManager("nonexistent.json")
        assert cache_manager.cache == {}
    
    def test_get_cache_key_without_variables(self):
        """Test cache key generation without variables."""
        cache_manager = CacheManager()
        query = "query { test }"
        key = cache_manager._get_cache_key(query)
        assert key == query
    
    def test_get_cache_key_with_variables(self):
        """Test cache key generation with variables."""
        cache_manager = CacheManager()
        query = "query { test }"
        variables = {"var1": "value1", "var2": "value2"}
        key = cache_manager._get_cache_key(query, variables)
        expected = f"{query}:{str(sorted(variables.items()))}"
        assert key == expected
    
    def test_get_and_set_cache(self):
        """Test cache get and set operations."""
        cache_manager = CacheManager()
        query = "test query"
        variables = {"test": "var"}
        response = {"data": "test"}
        
        # Initially should return None
        assert cache_manager.get(query, variables) is None
        
        # Set cache
        with patch.object(cache_manager, '_save_cache'):
            cache_manager.set(query, variables, response)
        
        # Should now return the cached response
        assert cache_manager.get(query, variables) == response
    
    def test_cache_file_operations_integration(self):
        """Integration test for actual cache file operations with cleanup."""
        import os
        import json
        
        # Ensure test cache directory exists
        os.makedirs("tests/cache", exist_ok=True)
        
        # Create cache manager with test file
        cache_manager = CacheManager(self.test_cache_file)
        self.test_cache_files_to_cleanup.append(self.test_cache_file)
        
        # Test data
        query = "test query"
        variables = {"test": "var"}
        response = {"data": "test response"}
        
        # Initially should return None (no cache file exists)
        assert cache_manager.get(query, variables) is None
        
        # Set cache (this should create the file)
        cache_manager.set(query, variables, response)
        
        # Verify file was created
        assert os.path.exists(self.test_cache_file)
        
        # Verify cache content
        with open(self.test_cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        cache_key = cache_manager._get_cache_key(query, variables)
        assert cache_key in cache_data
        assert cache_data[cache_key] == response
        
        # Test retrieval
        assert cache_manager.get(query, variables) == response
        
        # Test clear cache
        cache_manager.clear()
        
        # File should be removed
        assert not os.path.exists(self.test_cache_file)


class TestRateLimiter:
    """Test cases for RateLimiter class."""
    
    def test_init_with_default_rate_limit(self):
        """Test RateLimiter initialization with default rate limit."""
        rate_limiter = RateLimiter()
        assert rate_limiter.rate_limit_seconds > 0
        assert rate_limiter.last_request_time == 0.0
    
    def test_init_with_custom_rate_limit(self):
        """Test RateLimiter initialization with custom rate limit."""
        custom_rate = 2.0
        rate_limiter = RateLimiter(custom_rate)
        assert rate_limiter.rate_limit_seconds == custom_rate
    
    @patch('src.guild_log_analysis.api.client.time')
    def test_wait_if_needed_should_wait(self, mock_time_module):
        """Test rate limiter when waiting is needed."""
        # Mock time.time() and time.sleep()
        mock_time_module.time.side_effect = [1.5, 2.0]  # 0.5 seconds elapsed, then after sleep
        mock_time_module.sleep = Mock()
        
        rate_limiter = RateLimiter(1.0)
        rate_limiter.last_request_time = 1.0
        
        rate_limiter.wait_if_needed()
        
        mock_time_module.sleep.assert_called_once_with(0.5)
    
    @patch('src.guild_log_analysis.api.client.time')
    def test_wait_if_needed_no_wait(self, mock_time_module):
        """Test rate limiter when no waiting is needed."""
        # Mock time.time() - 1.5 seconds elapsed, more than rate limit
        mock_time_module.time.side_effect = [2.5, 2.5]  # 1.5 seconds elapsed
        mock_time_module.sleep = Mock()
        
        rate_limiter = RateLimiter(1.0)
        rate_limiter.last_request_time = 1.0
        
        rate_limiter.wait_if_needed()
        
        mock_time_module.sleep.assert_not_called()


class TestWarcraftLogsAPIClient:
    """Test cases for WarcraftLogsAPIClient class."""
    
    def test_init_with_access_token(self):
        """Test API client initialization with access token."""
        token = "test_token"
        client = WarcraftLogsAPIClient(access_token=token)
        assert client.access_token == token
        assert client.cache_manager is not None
        assert client.rate_limiter is not None
        assert client.session is not None
    
    def test_init_without_access_token(self):
        """Test API client initialization without access token."""
        client = WarcraftLogsAPIClient()
        assert client.access_token is None
    
    def test_update_auth_header(self):
        """Test authorization header update."""
        token = "test_token"
        client = WarcraftLogsAPIClient(access_token=token)
        client._update_auth_header()
        
        expected_header = f'Bearer {token}'
    
    def test_update_auth_header_no_token(self):
        """Test authorization header update without token."""
        client = WarcraftLogsAPIClient()
        
        with pytest.raises(AuthenticationError):
            client._update_auth_header()
    
    @patch('src.guild_log_analysis.api.client.time')
    def test_make_request_success(self, mock_time_module):
        """Test successful API request."""
        # Setup time mocking
        mock_time_module.time.return_value = 1.0
        mock_time_module.sleep = Mock()
        
        # Setup
        token = "test_token"
        client = WarcraftLogsAPIClient(access_token=token)
        
        # Mock the session.post method directly on the client's session
        with patch.object(client.session, 'post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": "test"}
            mock_post.return_value = mock_response
            
            query = "query { test }"
            variables = {"var": "value"}
            
            # Execute with force_refresh to bypass cache
            result = client.make_request(query, variables, force_refresh=True)
            
            # Verify
            assert result == {"data": "test"}
            mock_post.assert_called_once()
            
            # Verify the call was made with correct parameters
            call_args = mock_post.call_args
            assert call_args[1]['json']['query'] == query
            assert call_args[1]['json']['variables'] == variables
    
    @patch('requests.Session.post')
    def test_make_request_with_graphql_errors(self, mock_post):
        """Test API request with GraphQL errors."""
        token = "test_token"
        client = WarcraftLogsAPIClient(access_token=token)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "errors": [{"message": "Test error"}],
            "data": None
        }
        mock_post.return_value = mock_response
        
        query = "query { test }"
        
        with pytest.raises(APIError) as exc_info:
            client.make_request(query)
        
        assert "GraphQL errors" in str(exc_info.value)
    
    @patch('requests.Session.post')
    def test_make_request_unauthorized(self, mock_post):
        """Test API request with unauthorized response."""
        token = "invalid_token"
        client = WarcraftLogsAPIClient(access_token=token)
        
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Unauthorized"}
        mock_post.return_value = mock_response
        
        query = "query { test }"
        
        with pytest.raises(AuthenticationError):
            client.make_request(query)
    
    @patch('requests.Session.post')
    def test_make_request_rate_limited(self, mock_post):
        """Test API request with rate limit response."""
        token = "test_token"
        client = WarcraftLogsAPIClient(access_token=token)
        
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {'Retry-After': '60'}
        mock_response.json.return_value = {"error": "Rate limited"}
        mock_post.return_value = mock_response
        
        query = "query { test }"
        
        with pytest.raises(RateLimitError) as exc_info:
            client.make_request(query)
        
        assert exc_info.value.retry_after == 60
    
    @patch('requests.Session.post')
    def test_make_request_network_error(self, mock_post):
        """Test API request with network error."""
        token = "test_token"
        client = WarcraftLogsAPIClient(access_token=token)
        
        mock_post.side_effect = RequestException("Network error")
        
        query = "query { test }"
        
        with pytest.raises(APIError):
            client.make_request(query)
    
    def test_make_request_no_access_token(self):
        """Test API request without access token."""
        client = WarcraftLogsAPIClient()
        
        query = "query { test }"
        
        with pytest.raises(AuthenticationError):
            client.make_request(query)
    
    @patch('requests.Session.post')
    def test_make_request_uses_cache(self, mock_post):
        """Test that API request uses cache when available."""
        token = "test_token"
        client = WarcraftLogsAPIClient(access_token=token)
        
        query = "query { test }"
        cached_response = {"data": "cached"}
        
        # Mock cache to return cached response
        with patch.object(client.cache_manager, 'get', return_value=cached_response):
            result = client.make_request(query)
        
        # Should return cached response without making HTTP request
        assert result == cached_response
        mock_post.assert_not_called()
    
    @patch('requests.Session.post')
    def test_make_request_force_refresh(self, mock_post):
        """Test API request with force refresh ignores cache."""
        token = "test_token"
        client = WarcraftLogsAPIClient(access_token=token)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "fresh"}
        mock_post.return_value = mock_response
        
        query = "query { test }"
        cached_response = {"data": "cached"}
        
        # Mock cache to return cached response
        with patch.object(client.cache_manager, 'get', return_value=cached_response):
            with patch.object(client.cache_manager, 'set'):
                result = client.make_request(query, force_refresh=True)
        
        # Should make HTTP request despite cache
        assert result == {"data": "fresh"}
        mock_post.assert_called_once()
    
    def test_clear_cache(self):
        """Test cache clearing."""
        client = WarcraftLogsAPIClient()
        
        with patch.object(client.cache_manager, 'clear') as mock_clear:
            client.clear_cache()
            mock_clear.assert_called_once()
    
    def test_invalidate_cache_entry(self):
        """Test cache entry invalidation."""
        client = WarcraftLogsAPIClient()
        
        query = "test query"
        variables = {"test": "var"}
        
        with patch.object(client.cache_manager, 'invalidate_entry') as mock_invalidate:
            client.invalidate_cache_entry(query, variables)
            mock_invalidate.assert_called_once_with(query, variables)

