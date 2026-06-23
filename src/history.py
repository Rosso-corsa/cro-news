#!/usr/bin/env python3
"""
History Module

This module handles tracking published articles to avoid duplicates.
It reads and writes history from local files or S3 storage.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict
from src.file_manager import read_file, write_file

logger = logging.getLogger(__name__)


def read_history(history_path: str, config_path: str = "config.json") -> List[Dict]:
    try:
        history = read_file(history_path, config_path)
        logger.info(f"Read {len(history)} entries from history")
        return history
    except Exception as e:
        logger.error(f"Unexpected error reading history: {e}")
        return []


def update_history(history_path: str, title: str, text: str, config_path: str = "config.json") -> None:
    """
    Update history with a new article entry and remove entries older than 3 days.

    Args:
        history_path: Path to the history file (local or S3 key)
        title: Article title
        text: Article description/text
        config_path: Path to the configuration file (default: "config.json")
    """
    try:
        # Read existing history
        history = read_history(history_path, config_path)

        # Create new entry with current timestamp
        new_entry = {
            'title': title,
            'text': text,
            'publish_time': datetime.now().isoformat()
        }
        history.append(new_entry)
        logger.info(f"Added new history entry: {title}")

        # Remove entries older than 3 days
        cutoff_time = datetime.now() - timedelta(days=3)
        filtered_history = []
        removed_count = 0

        for entry in history:
            try:
                entry_time = datetime.fromisoformat(entry['publish_time'])
                if entry_time > cutoff_time:
                    filtered_history.append(entry)
                else:
                    removed_count += 1
            except (ValueError, KeyError) as e:
                logger.warning(f"Skipping invalid history entry: {e}")
                removed_count += 1

        if removed_count > 0:
            logger.info(f"Removed {removed_count} old entries from history")

        # Save updated history
        write_file(filtered_history, history_path, config_path)
        logger.info(f"Saved {len(filtered_history)} entries to history")

    except Exception as e:
        logger.error(f"Error updating history: {e}")
