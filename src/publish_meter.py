#!/usr/bin/env python3
"""
Publish Meter Module

This module handles calculation of the publish-meter metric for news items.
"""

import logging
import math
from datetime import datetime, timedelta
from typing import List, Dict

logger = logging.getLogger(__name__)


def calculate_time_coef(last_update_time: str) -> float:
    try:
        last_update = datetime.fromisoformat(last_update_time)
        now = datetime.now()
        time_diff = now - last_update
        hours = time_diff.total_seconds() / 3600

        if hours < 3:
            return 1.0
        elif hours < 6:
            return 0.8
        elif hours < 12:
            return 0.6
        elif hours < 24:
            return 0.4
        else:
            return 0.0

    except Exception as e:
        logger.error(f"Error calculating time coefficient for {last_update_time}: {e}")
        return 0.0


def calculate_publish_meter(fit_level: int, time_coef: float, original_texts: list) -> float:
    appearances_count = len(original_texts) if original_texts else 1
    appearances_sqrt = math.sqrt(max(1, appearances_count))

    publish_meter = fit_level * time_coef * appearances_sqrt

    logger.debug(f"Publish meter calculation: fit={fit_level}, time_coef={time_coef}, text_count={appearances_count}, result={publish_meter}")

    return publish_meter


def recalculate_all_publish_meters(unpublished_news: List[Dict]) -> List[Dict]:
    updated_news = []
    removed_count = 0

    for item in unpublished_news:
        fit_level = item.get('fit_level', 5)
        last_update_time = item.get('last_update_time', datetime.now().isoformat())
        original_texts = item.get('original_texts', [])

        time_coef = calculate_time_coef(last_update_time)

        if time_coef == 0.0:
            removed_count += 1
            logger.info(f"Removing old item {item.get('id')} from unpublished (>= 24 hours)")
            continue

        publish_meter = calculate_publish_meter(fit_level, time_coef, original_texts)
        item['publish_meter'] = publish_meter

        updated_news.append(item)

    if removed_count > 0:
        logger.info(f"Removed {removed_count} old items from unpublished news")

    logger.info(f"Recalculated publish-meters for {len(updated_news)} items")

    return updated_news
