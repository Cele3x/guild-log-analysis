"""
Warcraft Logs API client.

This module provides a robust client for interacting with the Warcraft Logs API
with features like rate limiting, caching, and error handling.
"""

import time
import json
import os
from typing import Dict, Any, Optional
import logging

import requests

from ..config import ErrorMessages
from ..config.settings import Settings
from .exceptions import APIError, RateLimitError, AuthenticationError

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages API response caching with rotation."""
    
    def __init__(self, cache_file: Optional[str] = None) -> None:
        """
        Initialize cache manager.
        
        :param cache_file: Path to cache file
        """
        settings = Settings()
        self.cache_file = cache_file or str(settings.cache_directory / "api_cache.json")
        self.cache: Dict[str, Any] = self._load_cache()
    
    def _get_cache_file_size(self) -> int:
        """
        Get the size of the current cache file in bytes.
        
        :returns: File size in bytes
        """
        if os.path.exists(self.cache_file):
            return os.path.getsize(self.cache_file)
        return 0
    
    def _rotate_cache_files(self) -> None:
        """Rotate cache files when they get too large."""
        if not os.path.exists(self.cache_file):
            return
        
        # Check if current file needs rotation
        if self._get_cache_file_size() < 10 * 1024 * 1024:  # 10MB max cache size
            return
        
        logger.info("Rotating cache files due to size limit")
        
        try:
            # Remove oldest cache file if we've reached the maximum number of files
            oldest_cache = f"{self.cache_file}.{5}"
            if os.path.exists(oldest_cache):
                os.remove(oldest_cache)
            
            # Rotate existing cache files
            for i in range(5 - 1, 0, -1):
                old_name = f"{self.cache_file}.{i}"
                new_name = f"{self.cache_file}.{i + 1}"
                if os.path.exists(old_name):
                    os.rename(old_name, new_name)
            
            # Rename current cache file
            os.rename(self.cache_file, f"{self.cache_file}.1")
            
        except OSError as e:
            logger.error(f"Failed to rotate cache files: {e}")
    
    def _load_cache(self) -> Dict[str, Any]:
        """
        Load cache from file if it exists.
        
        :returns: Cache dictionary
        """
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning(
                    ErrorMessages.CACHE_CORRUPTED.format(cache_file=self.cache_file)
                )
                return {}
        return {}
    
    def _save_cache(self) -> None:
        """Save cache to file with rotation if needed."""
        # Check if we need to rotate before saving
        self._rotate_cache_files()
        
        try:
            # Ensure cache directory exists
            cache_path = os.path.dirname(self.cache_file)
            if cache_path:
                os.makedirs(cache_path, exist_ok=True)
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save cache: {e}")
    
    def _get_cache_key(self, query: str, variables: Optional[Dict] = None) -> str:
        """
        Generate a unique cache key for the query and variables.
        
        :param query: GraphQL query string
        :param variables: Query variables
        :returns: Unique cache key
        """
        if variables:
            return f"{query}:{str(sorted(variables.items()))}"
        return query
    
    def get(self, query: str, variables: Optional[Dict] = None) -> Optional[Any]:
        """
        Get cached response.
        
        :param query: GraphQL query string
        :param variables: Query variables
        :returns: Cached response or None
        """
        cache_key = self._get_cache_key(query, variables)
        return self.cache.get(cache_key)
    
    def set(self, query: str, variables: Optional[Dict], response: Any) -> None:
        """
        Cache response.
        
        :param query: GraphQL query string
        :param variables: Query variables
        :param response: API response to cache
        """
        cache_key = self._get_cache_key(query, variables)
        self.cache[cache_key] = response
        self._save_cache()
    
    def clear(self) -> None:
        """Clear all cached data and remove all cache files."""
        self.cache.clear()
        
        # Remove all cache files
        for i in range(1, 5 + 1):
            cache_file = f"{self.cache_file}.{i}"
            if os.path.exists(cache_file):
                try:
                    os.remove(cache_file)
                except OSError as e:
                    logger.error(f"Failed to remove cache file {cache_file}: {e}")
        
        if os.path.exists(self.cache_file):
            try:
                os.remove(self.cache_file)
            except OSError as e:
                logger.error(f"Failed to remove main cache file: {e}")
    
    def invalidate_entry(self, query: str, variables: Optional[Dict] = None) -> None:
        """
        Invalidate a specific cache entry.
        
        :param query: GraphQL query string
        :param variables: Query variables
        """
        cache_key = self._get_cache_key(query, variables)
        if cache_key in self.cache:
            del self.cache[cache_key]
            self._save_cache()


class RateLimiter:
    """Handles API rate limiting."""
    
    def __init__(self, rate_limit_seconds: Optional[float] = None) -> None:
        """
        Initialize rate limiter.
        
        :param rate_limit_seconds: Minimum seconds between requests
        """
        self.rate_limit_seconds = rate_limit_seconds or 1.0  # Default 1 second rate limit
        self.last_request_time = 0.0
    
    def wait_if_needed(self) -> None:
        """Wait if necessary to respect rate limit."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.rate_limit_seconds:
            sleep_time = self.rate_limit_seconds - time_since_last_request
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()


class WarcraftLogsAPIClient:
    """
    Warcraft Logs API client with caching, rate limiting, and error handling.
    """
    
    def __init__(
        self,
        access_token: Optional[str] = None,
        cache_manager: Optional[CacheManager] = None,
        rate_limiter: Optional[RateLimiter] = None
    ) -> None:
        """
        Initialize API client.
        
        :param access_token: OAuth access token
        :param cache_manager: Cache manager instance
        :param rate_limiter: Rate limiter instance
        """
        self.access_token = access_token
        self.cache_manager = cache_manager or CacheManager()
        self.rate_limiter = rate_limiter or RateLimiter()
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """
        Create and configure requests session.
        
        :returns: Configured session
        """
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": 'WoW-Guild-Analysis/1.0'
        })
        return session
    
    def _update_auth_header(self) -> None:
        """Update authorization header with current token."""
        if not self.access_token:
            raise AuthenticationError(ErrorMessages.NO_ACCESS_TOKEN)
        
        self.session.headers["Authorization"] = f'Bearer {self.access_token}'
    
    def make_request(
        self,
        query: str,
        variables: Optional[Dict] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Make an API request with rate limiting and caching.
        
        :param query: GraphQL query string
        :param variables: Query variables
        :param force_refresh: If True, ignores cache and makes fresh request
        :returns: API response data
        :raises APIError: If API request fails
        :raises AuthenticationError: If authentication fails
        :raises RateLimitError: If rate limit is exceeded
        """
        if not self.access_token:
            raise AuthenticationError(ErrorMessages.NO_ACCESS_TOKEN)
        
        # Check cache first, unless force_refresh is True
        if not force_refresh:
            cached_response = self.cache_manager.get(query, variables)
            if cached_response is not None:
                logger.debug("Using cached response")
                return cached_response
        
        # Make fresh API request
        self.rate_limiter.wait_if_needed()
        self._update_auth_header()
        
        payload = {'query': query}
        if variables:
            payload['variables'] = variables
        
        try:
            settings = Settings()
            logger.debug(f"Making API request to {settings.api_url}")
            response = self.session.post(
                settings.api_url,
                json=payload,
                timeout=30
            )
            
            self._handle_response_errors(response)
            result = response.json()
            
            # Check for GraphQL errors
            if 'errors' in result:
                error_messages = [error.get('message', 'Unknown error') for error in result['errors']]
                raise APIError(f"GraphQL errors: {', '.join(error_messages)}")
            
            # Cache the result
            self.cache_manager.set(query, variables, result)
            
            return result
            
        except requests.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise APIError(ErrorMessages.API_REQUEST_FAILED) from e
    
    def _handle_response_errors(self, response: requests.Response) -> None:
        """
        Handle HTTP response errors.
        
        :param response: HTTP response object
        :raises APIError: For various API errors
        :raises RateLimitError: If rate limit is exceeded
        :raises AuthenticationError: If authentication fails
        """
        if response.status_code == 200:
            return
        
        try:
            error_data = response.json()
        except json.JSONDecodeError:
            error_data = None
        
        if response.status_code == 401:
            raise AuthenticationError(
                ErrorMessages.AUTH_FAILED,
                status_code=response.status_code,
                response_data=error_data
            )
        elif response.status_code == 429:
            retry_after = response.headers.get('Retry-After')
            raise RateLimitError(
                "Rate limit exceeded",
                status_code=response.status_code,
                retry_after=int(retry_after) if retry_after else None,
                response_data=error_data
            )
        else:
            raise APIError(
                f"API request failed with status {response.status_code}",
                status_code=response.status_code,
                response_data=error_data
            )
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        self.cache_manager.clear()
    
    def invalidate_cache_entry(self, query: str, variables: Optional[Dict] = None) -> None:
        """
        Invalidate a specific cache entry.
        
        :param query: GraphQL query string
        :param variables: Query variables
        """
        self.cache_manager.invalidate_entry(query, variables)

