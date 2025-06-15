"""
Utility functions for caching operations.

This module provides helper functions for cache management and data serialization.
"""

import json
import hashlib
from typing import Any, Dict, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def generate_cache_key(*args: Any, **kwargs: Any) -> str:
    """
    Generate a unique cache key from arguments.
    
    :param args: Positional arguments
    :param kwargs: Keyword arguments
    :returns: Unique cache key
    """
    # Create a string representation of all arguments
    key_data = {
        'args': args,
        'kwargs': sorted(kwargs.items()) if kwargs else {}
    }
    
    # Convert to JSON string for consistent representation
    key_string = json.dumps(key_data, sort_keys=True, default=str)
    
    # Generate hash for shorter, consistent key
    return hashlib.md5(key_string.encode('utf-8')).hexdigest()


def safe_json_load(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    Safely load JSON from file with error handling.
    
    :param file_path: Path to JSON file
    :returns: Loaded data or None if failed
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Failed to load JSON from {file_path}: {e}")
        return None


def safe_json_save(data: Any, file_path: Path, indent: int = 2) -> bool:
    """
    Safely save data to JSON file with error handling.
    
    :param data: Data to save
    :param file_path: Path to save file
    :param indent: JSON indentation
    :returns: True if successful, False otherwise
    """
    try:
        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, default=str)
        return True
    except (IOError, TypeError) as e:
        logger.error(f"Failed to save JSON to {file_path}: {e}")
        return False


def clean_old_files(directory: Path, pattern: str, max_files: int) -> None:
    """
    Clean old files matching pattern, keeping only the most recent ones.
    
    :param directory: Directory to clean
    :param pattern: File pattern to match
    :param max_files: Maximum number of files to keep
    """
    try:
        if not directory.exists():
            return
        
        # Find all matching files
        files = list(directory.glob(pattern))
        
        # Sort by modification time (newest first)
        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        # Remove excess files
        for file_to_remove in files[max_files:]:
            try:
                file_to_remove.unlink()
                logger.debug(f"Removed old file: {file_to_remove}")
            except OSError as e:
                logger.warning(f"Failed to remove file {file_to_remove}: {e}")
                
    except Exception as e:
        logger.error(f"Error cleaning old files: {e}")


def ensure_directory(path: Path) -> bool:
    """
    Ensure directory exists, creating it if necessary.
    
    :param path: Directory path
    :returns: True if directory exists or was created successfully
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
        return True
    except OSError as e:
        logger.error(f"Failed to create directory {path}: {e}")
        return False

