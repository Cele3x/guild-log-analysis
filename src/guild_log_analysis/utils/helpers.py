"""
Helper utility functions for Guild Log Analysis.

This module provides various utility functions used throughout the application.
"""

from typing import Dict, List, Any, Optional, Union
import re
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def format_number(value: Union[int, float], decimal_places: int = 2) -> str:
    """
    Format number with appropriate suffix (b, m, k) and rounding.

    :param value: Number to format
    :param decimal_places: Number of decimal places to display (default: 2)
    :returns: Formatted string
    """
    if abs(value) >= 1_000_000_000:  # Billion
        return f"{value/1_000_000_000:.{decimal_places}f}b"
    elif abs(value) >= 1_000_000:  # Million
        return f"{value/1_000_000:.{decimal_places}f}m"
    elif abs(value) >= 1_000:  # Thousand
        return f"{value/1_000:.{decimal_places}f}k"
    else:
        # If the value is an integer, display it without decimals
        if value.is_integer():
            return f"{int(value)}"
        return f"{value:.{decimal_places}f}"


def format_percentage(value: Union[int, float], decimal_places: int = 1) -> str:
    """
    Format a number as a percentage.
    
    :param value: Number to format as percentage
    :param decimal_places: Number of decimal places to show
    :returns: Formatted percentage string
    """
    return f"{value:.{decimal_places}f}%"


def format_timestamp(timestamp: float, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format a Unix timestamp as a human-readable string.
    
    :param timestamp: Unix timestamp in seconds
    :param format_str: Format string for datetime formatting
    :returns: Formatted timestamp string
    """
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime(format_str)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing invalid characters.
    
    :param filename: Original filename
    :returns: Sanitized filename
    """
    # Remove invalid characters for filenames
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove multiple consecutive underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    # Remove leading/trailing underscores and dots
    sanitized = sanitized.strip('_.')
    return sanitized


def safe_get_nested(data: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
    """
    Safely get a nested value from a dictionary.
    
    :param data: Dictionary to search in
    :param keys: List of keys representing the path to the value
    :param default: Default value to return if path doesn't exist
    :returns: Value at the specified path or default
    """
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


def validate_report_code(report_code: str) -> bool:
    """
    Validate a Warcraft Logs report code format.
    
    :param report_code: Report code to validate
    :returns: True if valid, False otherwise
    """
    if not isinstance(report_code, str):
        return False
    
    # Report codes are typically 16 characters long, alphanumeric
    pattern = r'^[a-zA-Z0-9]{16}$'
    return bool(re.match(pattern, report_code))


def calculate_change_percentage(current: Union[int, float], previous: Union[int, float]) -> Optional[float]:
    """
    Calculate percentage change between two values.
    
    :param current: Current value
    :param previous: Previous value
    :returns: Percentage change or None if calculation not possible
    """
    if previous == 0:
        return None if current == 0 else float('inf')
    
    return ((current - previous) / previous) * 100


def group_players_by_role(players: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Group players by their role.
    
    :param players: List of player dictionaries
    :returns: Dictionary with roles as keys and player lists as values
    """
    role_groups = {
        "tank": [],
        "healer": [],
        "dps": []
    }
    
    for player in players:
        role = player.get("role", "dps")
        if role in role_groups:
            role_groups[role].append(player)
        else:
            role_groups["dps"].append(player)
    
    return role_groups


def filter_players_by_class(players: List[Dict[str, Any]], class_name: str) -> List[Dict[str, Any]]:
    """
    Filter players by their class.
    
    :param players: List of player dictionaries
    :param class_name: Class name to filter by
    :returns: Filtered list of players
    """
    return [player for player in players if player.get("class", "").lower() == class_name.lower()]


def merge_player_data(players1: List[Dict[str, Any]], players2: List[Dict[str, Any]], 
                     key: str = "name") -> List[Dict[str, Any]]:
    """
    Merge two lists of player data based on a key.
    
    :param players1: First list of player dictionaries
    :param players2: Second list of player dictionaries
    :param key: Key to match players on
    :returns: Merged list of player dictionaries
    """
    # Create lookup dictionary for second list
    lookup = {player[key]: player for player in players2 if key in player}
    
    merged = []
    for player in players1:
        if key in player and player[key] in lookup:
            # Merge the dictionaries
            merged_player = {**player, **lookup[player[key]]}
            merged.append(merged_player)
        else:
            merged.append(player)
    
    return merged


def deduplicate_players(players: List[Dict[str, Any]], key: str = "name") -> List[Dict[str, Any]]:
    """
    Remove duplicate players based on a key.
    
    :param players: List of player dictionaries
    :param key: Key to deduplicate on
    :returns: Deduplicated list of players
    """
    seen = set()
    deduplicated = []
    
    for player in players:
        if key in player:
            player_key = player[key]
            if player_key not in seen:
                seen.add(player_key)
                deduplicated.append(player)
    
    return deduplicated

