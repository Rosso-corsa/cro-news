#!/usr/bin/env python3
"""
News Matcher Module

This module handles bulk AI-based deduplication and matching of news items.
"""

import json
import logging
from typing import List, Dict
from src.ai_adapter import get_ai_response
from src.prompts import BULK_DEDUPLICATION_PROMPT, BULK_DEDUPLICATION_JSON_SCHEMA

logger = logging.getLogger(__name__)


def bulk_deduplicate_and_match(
    new_articles: List[Dict],
    unpublished_news: List[Dict],
    history: List[Dict]
) -> Dict[str, Dict]:
    """
    Perform bulk AI-based deduplication and matching.

    Args:
        new_articles: List of new articles to process (each must have: id, title, text, summary)
        unpublished_news: List of unpublished news items (each must have: id, topic_text, original_texts)
        history: List of published history items (each must have: title, text, publish_time)

    Returns:
        dict: Mapping of new_article_id -> {'status': 'new'|'match_unpublished'|'match_history', 'matched_id': id or None, 'confidence': float}
    """
    logger.info(f"Starting bulk deduplication for {len(new_articles)} new articles")

    # Prepare the data for the prompt
    new_articles_text = ""
    for article in new_articles:
        new_articles_text += f"ID: {article.get('id', '')}\n"
        new_articles_text += f"Title: {article.get('title', '')}\n"
        new_articles_text += f"Summary: {article.get('summary', '')}\n"
        new_articles_text += f"Text: {article.get('text', '')[:500]}...\n"  # Truncate for context
        new_articles_text += "-------------\n"

    unpublished_text = ""
    for item in unpublished_news:
        unpublished_text += f"ID: {item.get('id', '')}\n"
        unpublished_text += f"Topic: {item.get('topic_text', '')}\n"
        original_texts = item.get('original_texts', [])
        if original_texts:
            unpublished_text += f"Text: {original_texts[-1][:500]}...\n"
        unpublished_text += "-------------\n"

    history_text = ""
    for item in history:
        history_text += f"Title: {item.get('title', '')}\n"
        # Handle both string and list formats for text
        text = item.get('text', '')
        if isinstance(text, list):
            # Use the most recent text if it's a list
            text = text[-1] if text else ''
        history_text += f"Text: {str(text)[:500]}...\n"
        history_text += "-------------\n"

    # Build the prompt
    prompt = BULK_DEDUPLICATION_PROMPT.format(
        new_articles=new_articles_text,
        unpublished_news=unpublished_text if unpublished_text else "No unpublished news",
        history=history_text if history_text else "No history"
    )

    try:
        response = get_ai_response(prompt, json_schema=BULK_DEDUPLICATION_JSON_SCHEMA)
        result = json.loads(response)

        # Convert results to a dictionary mapping
        mapping = {}
        for item in result.get('results', []):
            mapping[item['id']] = {
                'status': item['status'],
                'matched_id': item.get('matched_id'),
                'confidence': item.get('confidence', 0.0)
            }

        logger.info(f"Bulk deduplication completed. Processed {len(mapping)} articles")
        return mapping

    except Exception as e:
        logger.error(f"Error in bulk deduplication: {e}")
        # Return all as new if AI fails
        return {article.get('id', ''): {'status': 'new', 'matched_id': None, 'confidence': 0.0} for article in new_articles}
