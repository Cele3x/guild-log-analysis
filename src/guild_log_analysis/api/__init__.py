"""API package for Guild Log Analysis."""

from .client import WarcraftLogsAPIClient, CacheManager, RateLimiter
from .auth import OAuthAuthenticator, TokenManager, get_access_token
from .exceptions import (
    WoWAnalysisError,
    APIError,
    AuthenticationError,
    RateLimitError,
    CacheError,
    AnalysisError,
    DataNotFoundError,
    InvalidDataError,
    PlotError,
    ConfigurationError,
)

__all__ = [
    'WarcraftLogsAPIClient',
    'CacheManager',
    'RateLimiter',
    'OAuthAuthenticator',
    'TokenManager',
    'get_access_token',
    'WoWAnalysisError',
    'APIError',
    'AuthenticationError',
    'RateLimitError',
    'CacheError',
    'AnalysisError',
    'DataNotFoundError',
    'InvalidDataError',
    'PlotError',
    'ConfigurationError',
]

