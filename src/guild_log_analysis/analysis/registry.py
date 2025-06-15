"""
Analysis registry for automatic boss discovery and registration.

This module provides a decorator-based system for registering boss analysis
classes, enabling automatic discovery and method generation.
"""

import logging
from typing import Callable, Type

logger = logging.getLogger(__name__)

# Global registry to store boss analysis classes
_BOSS_REGISTRY: dict[str, Type] = {}


def register_boss(name: str) -> Callable[[Type], Type]:
    """
    Register boss analysis classes with decorator.

    :param name: The name identifier for the boss (used for method generation)
    :return: The decorator function
    """

    def decorator(cls: Type) -> Type:
        """
        Register the boss analysis class.

        :param cls: The boss analysis class to register
        :return: The original class
        """
        _BOSS_REGISTRY[name] = cls
        logger.debug(f"Registered boss analysis: {name} -> {cls.__name__}")
        return cls

    return decorator


def get_registered_bosses() -> dict[str, Type]:
    """
    Get all registered boss analysis classes.

    :return: Dictionary mapping boss names to their analysis classes
    """
    return _BOSS_REGISTRY.copy()


def clear_registry() -> None:
    """Clear the boss registry (primarily for testing purposes)."""
    _BOSS_REGISTRY.clear()
    logger.debug("Boss registry cleared")
