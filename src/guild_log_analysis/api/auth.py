"""
Authentication module for WoW Guild Analysis.

This module handles OAuth authentication flow with Warcraft Logs API.
"""

import base64
import hashlib
import json
import logging
import os
import secrets
import threading
import urllib.parse
import webbrowser
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Optional

import requests

from ..config import ErrorMessages
from ..config.settings import Settings
from .exceptions import AuthenticationError

logger = logging.getLogger(__name__)


class HTTPConstants:
    """HTTP constants for OAuth callback handler."""

    OK = 200
    BAD_REQUEST = 400
    CONTENT_TYPE_HEADER = "Content-Type"


class CallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth callback."""

    def do_GET(self) -> None:
        """Handle GET request for OAuth callback."""
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)

        if "code" in params:
            self.server.auth_code = params["code"][0]
            self._send_success_response()
        else:
            self._send_error_response()

    def _send_success_response(self) -> None:
        """Send success response to browser."""
        self.send_response(HTTPConstants.OK)
        self.send_header(HTTPConstants.CONTENT_TYPE_HEADER, "text/html")
        self.end_headers()
        self.wfile.write(
            b"<html><body><h1>Authorization successful!</h1>" b"<p>You can close this window.</p></body></html>"
        )

    def _send_error_response(self) -> None:
        """Send error response to browser."""
        self.send_response(HTTPConstants.BAD_REQUEST)
        self.send_header(HTTPConstants.CONTENT_TYPE_HEADER, "text/html")
        self.end_headers()
        self.wfile.write(b"<html><body><h1>Authorization failed!</h1></body></html>")

    def log_message(self, format: str, *args) -> None:
        """Suppress default logging."""
        pass


class TokenManager:
    """Manages OAuth tokens with caching and expiration."""

    def __init__(self, cache_file: Optional[str] = None) -> None:
        """
        Initialize token manager.

        :param cache_file: Path to token cache file
        """
        settings = Settings()
        self.cache_file = cache_file or str(settings.cache_directory / "token_cache.json")

    def load_cached_token(self) -> Optional[str]:
        """
        Load cached token if it exists and is still valid.

        :returns: Valid access token or None
        """
        if not os.path.exists(self.cache_file):
            return None

        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)

            # Check if token is expired
            expires_at = datetime.fromisoformat(cache_data["expires_at"])
            if datetime.now() >= expires_at:
                logger.info("Cached token has expired")
                return None

            logger.info("Using cached access token")
            return cache_data["access_token"]

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to load cached token: {e}")
            return None

    def save_token_to_cache(self, access_token: str, expires_in: int = 3600) -> None:
        """
        Save token to cache with expiration time.

        :param access_token: OAuth access token
        :param expires_in: Token expiration time in seconds
        """
        cache_data = {
            "access_token": access_token,
            "expires_at": (datetime.now() + timedelta(seconds=expires_in)).isoformat(),
        }

        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2)
            logger.info(f"Token cached to {self.cache_file}")
        except IOError as e:
            logger.error(f"Failed to save token to cache: {e}")


class OAuthAuthenticator:
    """Handles OAuth authentication flow."""

    def __init__(self, token_manager: Optional[TokenManager] = None) -> None:
        """
        Initialize OAuth authenticator.

        :param token_manager: Token manager instance
        """
        self.token_manager = token_manager or TokenManager()

    def get_access_token(self) -> str:
        """
        Get access token using OAuth flow or from cache.

        :returns: Valid access token
        :raises AuthenticationError: If authentication fails
        """
        # Try to load cached token first
        cached_token = self.token_manager.load_cached_token()
        if cached_token:
            return cached_token

        logger.info("Starting OAuth authentication flow")
        return self._perform_oauth_flow()

    def _perform_oauth_flow(self) -> str:
        """
        Perform complete OAuth flow.

        :returns: Access token
        :raises AuthenticationError: If authentication fails
        """
        try:
            code_verifier, code_challenge = self._generate_pkce_params()
            auth_code = self._get_authorization_code(code_challenge)
            token_info = self._exchange_code_for_token(auth_code, code_verifier)

            access_token = token_info["access_token"]
            expires_in = token_info.get("expires_in", 3600)

            # Cache the token
            self.token_manager.save_token_to_cache(access_token, expires_in)
            return access_token

        except Exception as e:
            logger.error(f"OAuth flow failed: {e}")
            raise AuthenticationError(ErrorMessages.AUTH_FAILED) from e

    @staticmethod
    def _generate_pkce_params() -> tuple[str, str]:
        """
        Generate PKCE code verifier and challenge.

        :returns: Tuple of (code_verifier, code_challenge)
        """
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("utf-8").rstrip("=")

        code_challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode("utf-8")).digest()).decode("utf-8").rstrip("=")
        )

        return code_verifier, code_challenge

    def _get_authorization_code(self, code_challenge: str) -> str:
        """
        Get authorization code from OAuth provider.

        :param code_challenge: PKCE code challenge
        :returns: Authorization code
        :raises AuthenticationError: If authorization fails
        """
        server = HTTPServer(("localhost", 8080), CallbackHandler)
        server.auth_code = None
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        try:
            auth_url = self._build_auth_url(code_challenge)

            logger.info("Opening browser for authorization...")
            logger.info(f"If browser doesn't open, visit: {auth_url}")
            webbrowser.open(auth_url)

            logger.info("Waiting for authorization...")
            while server.auth_code is None:
                pass

            logger.info("Authorization code received")
            return server.auth_code

        finally:
            server.shutdown()

    def _build_auth_url(self, code_challenge: str) -> str:
        """
        Build authorization URL.

        :param code_challenge: PKCE code challenge
        :returns: Authorization URL
        """
        settings = Settings()
        params = {
            "client_id": settings.warcraft_logs_client_id,
            "redirect_uri": settings.redirect_uri,
            "response_type": "code",
            "code_challenge_method": "S256",
            "code_challenge": code_challenge,
        }
        return f"{settings.auth_url}?{urllib.parse.urlencode(params)}"

    def _exchange_code_for_token(self, auth_code: str, code_verifier: str) -> dict[str, Any]:
        """
        Exchange authorization code for access token.

        :param auth_code: Authorization code
        :param code_verifier: PKCE code verifier
        :returns: Token information
        :raises AuthenticationError: If token exchange fails
        """
        settings = Settings()
        data = {
            "grant_type": "authorization_code",
            "client_id": settings.warcraft_logs_client_id,
            "code": auth_code,
            "redirect_uri": settings.redirect_uri,
            "code_verifier": code_verifier,
        }

        try:
            response = requests.post(settings.token_url, data=data, timeout=30)
            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            logger.error(f"Token exchange failed: {e}")
            raise AuthenticationError(ErrorMessages.AUTH_FAILED) from e


def get_access_token() -> str:
    """
    Return a valid access token.

    :returns: Valid access token
    :raises AuthenticationError: If authentication fails
    """
    # First check if we have an existing token in environment variables
    existing_token = os.getenv("WARCRAFT_LOGS_ACCESS_TOKEN")
    if existing_token:
        logger.info("Using existing access token from environment variables")
        return existing_token

    # If no existing token, validate OAuth configuration
    settings = Settings()
    if not settings.warcraft_logs_client_id:
        raise AuthenticationError(
            "WOW_CLIENT_ID environment variable is required for OAuth authentication. "
            "Please register your application at https://www.warcraftlogs.com/api/clients/ "
            "and set the WOW_CLIENT_ID environment variable."
        )

    authenticator = OAuthAuthenticator()
    return authenticator.get_access_token()
