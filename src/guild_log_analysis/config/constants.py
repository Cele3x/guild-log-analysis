"""
Constants module for Guild Log Analysis.

This module contains only essential constants that are used repeatedly
across the codebase to avoid magic strings and improve maintainability.
"""

from typing import Final

# API Configuration
API_BASE_URL = "https://www.warcraftlogs.com/api/v2/client"
AUTH_URL = "https://www.warcraftlogs.com/oauth/authorize"
TOKEN_URL = "https://www.warcraftlogs.com/oauth/token"
DEFAULT_TIMEOUT = 30
DEFAULT_REDIRECT_URI = "http://localhost:8080"

# Analysis Configuration
DEFAULT_DIFFICULTY = 5  # Mythic
DEFAULT_WIPE_CUTOFF = 4  # Fights shorter than 4 seconds are considered wipes

# Logging Configuration
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FILE = "logs/wow_analysis.log"
DEFAULT_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s - %(message)s"

# Plot Configuration
DEFAULT_FIGURE_SIZE = (12, 8)
DEFAULT_DPI = 300

# Font Configuration
FONT_FAMILIES = [
    "Montserrat",  # Elegant, great for headings
    "Source Sans Pro",  # Adobe's open source font
    "Inter",  # Modern, highly readable
    "Lato",  # Humanist sans-serif
    "Roboto",
    "Open Sans",
    "Fira Sans",  # Mozilla's font
    "DejaVu Sans",  # Linux default
    "sans-serif",  # Fallback
]

# Specific font families for different plot elements
TITLE_FONT = ["Montserrat", "DejaVu Sans", "sans-serif"]
HEADER_FONT = ["Source Sans Pro", "DejaVu Sans", "sans-serif"]
NAME_FONT = ["Source Sans Pro", "DejaVu Sans", "sans-serif"]
DEFAULT_FONT = ["DejaVu Sans Mono", "Inter", "DejaVu Sans", "sans-serif"]


# Error Messages (only for repeated error scenarios)
class ErrorMessages:
    """Error message templates for common scenarios."""

    NO_ACCESS_TOKEN: Final[str] = "No access token provided"
    AUTH_FAILED: Final[str] = "Authentication failed"
    CACHE_CORRUPTED: Final[str] = "Cache file {cache_file} is corrupted and will be ignored"
    API_REQUEST_FAILED: Final[str] = "API request failed: {error}"
    INVALID_REPORT_CODE: Final[str] = "Invalid report code: {report_code}"
    NO_FIGHTS_FOUND: Final[str] = "No fights found for encounter {encounter_id} in report {report_code}"
    NO_PLAYERS_FOUND: Final[str] = "No players found for report {report_code}"


class ClassColors:
    """WoW class colors."""

    DEATHKNIGHT: Final[str] = "#C41E3A"
    MAGE: Final[str] = "#69CCF0"
    SHAMAN: Final[str] = "#0070DE"
    HUNTER: Final[str] = "#ABD473"
    WARRIOR: Final[str] = "#C79C6E"
    PALADIN: Final[str] = "#F58CBA"
    WARLOCK: Final[str] = "#9482C9"
    PRIEST: Final[str] = "#FFFFFF"
    ROGUE: Final[str] = "#FFF569"
    DRUID: Final[str] = "#FF7D0A"
    DEMONHUNTER: Final[str] = "#A330C9"
    MONK: Final[str] = "#00FF96"
    EVOKER: Final[str] = "#33937F"


# Player Roles
class PlayerRoles:
    """Player role constants for filtering analyses."""

    TANK: Final[str] = "tank"
    HEALER: Final[str] = "healer"
    DPS: Final[str] = "dps"

    ALL_ROLES: Final[list[str]] = [TANK, HEALER, DPS]


# Plot Colors
class PlotColors:
    """Essential color definitions for plots."""

    BACKGROUND: Final[str] = "#1A1A1A"
    CHART_BG: Final[str] = "#2A2A2A"
    TEXT_PRIMARY: Final[str] = "#FFFFFF"
    TEXT_SECONDARY: Final[str] = "#CCCCCC"
    GRID: Final[str] = "#404040"
    BORDER: Final[str] = "#555555"
    ROW_ALT: Final[str] = "#252525"

    # Change indicator colors
    POSITIVE_CHANGE_COLOR: Final[str] = "#00FF00"
    NEGATIVE_CHANGE_COLOR: Final[str] = "#FF0000"
    NEUTRAL_CHANGE_COLOR: Final[str] = "#CCCCCC"
