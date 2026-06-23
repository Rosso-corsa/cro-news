#!/usr/bin/env python3
"""
File Manager Module

This module provides a unified interface for reading and writing JSON files,
abstracting the storage backend (local filesystem or S3-compatible storage).
"""

import json
import logging
import os
from src.s3_adapter import is_s3_enabled, write_to_s3, read_from_s3

logger = logging.getLogger(__name__)


def read_file(file_path: str, config_path: str = "config.json") -> dict:
    """
    Read a JSON file from local filesystem or S3 storage.

    Args:
        file_path: Path to the file (local path or S3 key)
        config_path: Path to the configuration file (default: "config.json")

    Returns:
        dict: The parsed JSON data, or empty dict if file not found
    """
    try:
        if is_s3_enabled(config_path):
            s3_key = file_path.lstrip('/')
            try:
                data = read_from_s3(s3_key, config_path)
                return data
            except Exception as e:
                logger.warning(f"File not found in S3: {s3_key}, returning empty dict")
                return {}
        else:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data
            except FileNotFoundError:
                logger.warning(f"File not found locally: {file_path}, returning empty dict")
                return {}
            except Exception as e:
                logger.error(f"Error reading file from {file_path}: {e}")
                return {}
    except Exception as e:
        logger.error(f"Unexpected error reading file: {e}")
        return {}


def write_file(data: dict, file_path: str, config_path: str = "config.json") -> None:
    """
    Write JSON data to local filesystem or S3 storage.

    Args:
        data: The data to write (must be JSON-serializable)
        file_path: Path to the file (local path or S3 key)
        config_path: Path to the configuration file (default: "config.json")
    """
    try:
        if is_s3_enabled(config_path):
            s3_key = file_path.lstrip('/')
            write_to_s3(data, s3_key, config_path)
        else:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error writing file to {file_path}: {e}")
        raise
