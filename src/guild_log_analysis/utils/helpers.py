"""
Helper utility functions for Guild Log Analysis.

This module provides various utility functions used throughout the application.
"""

from typing import Any, Optional, Union


def format_number(value: Union[int, float], decimal_places: int = 2) -> str:
    """
    Format number with appropriate suffix (b, m, k) and rounding.

    :param value: Number to format
    :param decimal_places: Number of decimal places to display (default: 2)
    :returns: Formatted string
    """
    if abs(value) >= 1_000_000_000:  # Billion
        return f"{value / 1_000_000_000:.{decimal_places}f}b"
    elif abs(value) >= 1_000_000:  # Million
        return f"{value / 1_000_000:.{decimal_places}f}m"
    elif abs(value) >= 1_000:  # Thousand
        return f"{value / 1_000:.{decimal_places}f}k"
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


def calculate_change_percentage(current: Union[int, float], previous: Union[int, float]) -> Optional[float]:
    """
    Calculate percentage change between two values.

    :param current: Current value
    :param previous: Previous value
    :returns: Percentage change or None if calculation not possible
    """
    if previous == 0:
        return None if current == 0 else float("inf")

    return ((current - previous) / previous) * 100


def filter_players_by_roles(players: list[dict[str, Any]], roles: list[str]) -> list[dict[str, Any]]:
    """
    Filter players by their roles.

    :param players: List of player dictionaries
    :param roles: List of role names to include
    :returns: Filtered list of players matching any of the specified roles
    """
    if not roles:
        # If no roles specified, return all players
        return players

    def get_player_role(player: dict[str, Any]) -> str:
        """Get player role, defaulting to 'dps' if None or missing."""
        role = player.get("role")
        return role if role is not None else "dps"

    return [player for player in players if get_player_role(player) in roles]
