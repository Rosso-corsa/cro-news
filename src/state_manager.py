#!/usr/bin/env python3
"""
State Manager Module

This module handles persistent state for the streaming mode.
It reads and writes state from local files or S3 storage.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from src.file_manager import read_file, write_file

logger = logging.getLogger(__name__)


def read_state(state_path: str) -> Dict:
    try:
        state = read_file(state_path, force_local=False)
        if state == {}:
            logger.info(f"State file not found, initializing new state")
            return initialize_state()
        logger.info(f"Read state from {state_path}")
        return state
    except Exception as e:
        logger.error(f"Error reading state: {e}")
        return initialize_state()


def write_state(state: Dict, state_path: str) -> None:
    try:
        write_file(state, state_path, force_local=False)
        logger.info(f"Saved state to {state_path}")
    except Exception as e:
        logger.error(f"Error writing state: {e}")
        raise


def initialize_state() -> Dict:
    twelve_hours_ago = datetime.now() - timedelta(hours=12)
    return {
        'last_check_time': twelve_hours_ago.isoformat(),
        'unpublished_news': []
    }


def update_last_check_time(state: Dict) -> Dict:
    state['last_check_time'] = datetime.now().isoformat()
    return state


def add_to_unpublished(state: Dict, news_item: Dict) -> Dict:
    original_texts = news_item.get('original_texts', [])
    if not original_texts:
        original_texts = []

    new_item = {
        'id': f"news_{len(state['unpublished_news']) + 1}_{int(datetime.now().timestamp())}",
        'topic_text': news_item.get('topic_text', ''),
        'last_update_time': news_item.get('pub_date', datetime.now().isoformat()),
        'publish_meter': 0.0,
        'fit_level': news_item.get('fit_level', 5),
        'original_texts': original_texts,
        'link': news_item.get('link', '')
    }
    state['unpublished_news'].append(new_item)
    logger.info(f"Added new item to unpublished: {new_item['id']}")
    return state


def update_unpublished_item(state: Dict, item_id: str, updates: Dict) -> Dict:
    for item in state['unpublished_news']:
        if item['id'] == item_id:
            for key, value in updates.items():
                if key == 'original_texts' and isinstance(value, str):
                    if 'original_texts' not in item:
                        item['original_texts'] = []
                    item['original_texts'].append(value)
                elif key == 'last_update_time':
                    if value is None:
                        item[key] = datetime.now().isoformat()
                    else:
                        item[key] = value
                elif value is not None:
                    item[key] = value
            logger.info(f"Updated unpublished item {item_id}: {updates}")
            return state
    logger.warning(f"Item {item_id} not found in unpublished news")
    return state


def remove_from_unpublished(state: Dict, item_id: str) -> Dict:
    initial_count = len(state['unpublished_news'])
    state['unpublished_news'] = [item for item in state['unpublished_news'] if item['id'] != item_id]
    if len(state['unpublished_news']) < initial_count:
        logger.info(f"Removed item {item_id} from unpublished news")
    else:
        logger.warning(f"Item {item_id} not found in unpublished news")
    return state


def get_top_unpublished_item(state: Dict) -> Dict:
    if not state['unpublished_news']:
        return None
    return max(state['unpublished_news'], key=lambda x: x.get('publish_meter', 0))
