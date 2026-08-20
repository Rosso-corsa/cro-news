#!/usr/bin/env python3
"""
Editor Module

This module combines RSS feed reading with article content extraction.
It fetches recent news items and extracts full article text for each.

Public functions of this module must satisfy Pipeline Functions requirements:
- Pipeline functions are dedicated public functions which perform one business goal
- Each function should read input (if required) from json file and write result to json file
- Each function should log the start of work and end of work
"""

import json
import logging
import os
import time
from typing import List, Dict
from src.rss_reader import get_recent_news
from src.article_extractor import get_content
from src.ai_adapter import get_ai_response
from src.telegram_adapter import send_message
from src.file_manager import read_file, write_file
from src.config import get_config
from src.prompts import (
    NEWS_ANALYSIS_PROMPT, NEWS_ANALYSIS_JSON_SCHEMA,
    STREAM_PUBLISH_PREPARATION_PROMPT, STREAM_PUBLISH_PREPARATION_JSON_SCHEMA,
)
from src.history import update_history, read_history
from src.state_manager import read_state, write_state, initialize_state, update_last_check_time, add_to_unpublished, update_unpublished_item, remove_from_unpublished, get_top_unpublished_item
from src.news_matcher import bulk_deduplicate_and_match
from src.publish_meter import recalculate_all_publish_meters

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def stream_collect_articles(state_path: str = "/tmp/stream_state.json", articles_output: str = "/tmp/stream_articles.json") -> None:
    """
    Collect news articles newer than last check time for streaming mode.

    Args:
        state_path: Path to the state file (default: "/tmp/stream_state.json")
        articles_output: Path to the output articles file (default: "/tmp/stream_articles.json")
    """
    logger.info("Starting streaming article collection")

    # Read state to get last_check_time
    state = read_state(state_path)
    last_check_time = state.get('last_check_time', None)

    logger.info(f"Fetching articles newer than: {last_check_time}")

    # Fetch news items newer than last_check_time
    news_items = get_recent_news(since_timestamp=last_check_time)
    logger.info(f"Fetched {len(news_items)} news items from RSS feeds. Starting content extraction...")

    articles = []

    for item in news_items:
        link = item.get('link', '')
        title = item.get('title', '')
        source = item.get('source_feed', '')

        if not link:
            logger.warning(f"Skipping item with no link: {title}")
            continue

        # Extract article content
        text = get_content(link)

        if text:
            article = {
                'title': title,
                'text': text,
                'link': link,
                'source': source,
                'pub_date': item.get('pub_date', '')
            }
            articles.append(article)
        else:
            logger.warning(f"Failed to extract content for: {title} - skipping")

    logger.info(f"Content extraction finished. Collected {len(articles)} articles with full content")

    # Add IDs to articles before saving (use timestamp + index for uniqueness)
    timestamp = int(time.time())
    for idx, article in enumerate(articles, start=1):
        article['id'] = f"article_{timestamp}_{idx}"

    write_file(articles, articles_output, force_local=True)

    logger.info(f"Saved {len(articles)} articles to {articles_output}")


def stream_categorize_articles(articles_path: str = "/tmp/stream_articles.json", categorized_path: str = "/tmp/stream_categorized.json") -> None:
    """
    Categorize articles for streaming mode: categorize with AI and filter by relevance >= 5.

    Args:
        articles_path: Path to the input articles file (default: "/tmp/stream_articles.json")
        categorized_path: Path to the output categorized articles file (default: "/tmp/stream_categorized.json")
    """
    logger.info(f"Starting streaming article categorization from {articles_path}")

    # Read articles
    articles = read_file(articles_path, force_local=True)

    logger.info(f"Read {len(articles)} articles from {articles_path}")

    if not articles:
        logger.info("No articles to categorize")
        write_file([], categorized_path, force_local=True)
        return

    logger.info("Categorizing articles with AI")
    # Get categorization model from config (falls back to default ai_model)
    config = get_config()
    categorization_model = config.get('ai_model_categorization') or config.get('ai_model')
    # Prepare news data for the prompt
    news_data = ""
    for article in articles:
        news_data += f"ID: {article['id']}\n"
        news_data += f"Title: {article['title']}\n"
        news_data += f"Text: {article['text']}\n"
        news_data += "-------------\n"

    prompt = NEWS_ANALYSIS_PROMPT.format(news_data=news_data)
    try:
        response = get_ai_response(prompt, json_schema=NEWS_ANALYSIS_JSON_SCHEMA, model=categorization_model)
        categorization_results = json.loads(response)
        logger.info(f"Categorization completed for {len(categorization_results)} articles")

        # Merge categorization results with articles
        categorized_articles = []
        for result in categorization_results:
            article = next((a for a in articles if a['id'] == result['id']), None)
            if article:
                article.update(result)
                categorized_articles.append(article)

    except Exception as e:
        logger.error(f"Error during categorization: {e}")
        return

    # Filter by fit-level >= 5
    logger.info("Filtering articles by relevance >= 5")
    filtered_articles = [article for article in categorized_articles if article.get('relevance', 0) >= 5]
    logger.info(f"Filtered out {len(categorized_articles) - len(filtered_articles)} articles with relevance < 5. Remaining: {len(filtered_articles)}")

    write_file(filtered_articles, categorized_path, force_local=True)
    logger.info(f"Saved {len(filtered_articles)} categorized articles to {categorized_path}")


def stream_deduplicate_articles(categorized_path: str = "/tmp/stream_categorized.json", state_path: str = "/tmp/stream_state.json", history_path: str = "/tmp/history.json") -> None:
    """
    Deduplicate articles for streaming mode: bulk AI deduplication, update state, recalculate publish-meters, update last_check_time.

    Args:
        categorized_path: Path to the input categorized articles file (default: "/tmp/stream_categorized.json")
        state_path: Path to the state file (default: "/tmp/stream_state.json")
        history_path: Path to the history file (default: "/tmp/history.json")
    """
    logger.info(f"Starting streaming article deduplication from {categorized_path}")

    # Read categorized articles and state
    filtered_articles = read_file(categorized_path, force_local=True)
    state = read_state(state_path)

    logger.info(f"Read {len(filtered_articles)} categorized articles from {categorized_path}")

    if not filtered_articles:
        logger.info("No articles to deduplicate")
        # Still update last_check_time even if no articles
        state = update_last_check_time(state)
        write_state(state, state_path)
        return

    # Read history (3-day window)
    logger.info("Reading history for deduplication")
    history = read_history(history_path)
    logger.info(f"Read {len(history)} entries from history")

    # Bulk AI deduplication
    logger.info("Performing bulk AI deduplication")
    unpublished_news = state.get('unpublished_news', [])

    deduplication_results = bulk_deduplicate_and_match(filtered_articles, unpublished_news, history)

    # Process AI results
    logger.info("Processing deduplication results")

    # First pass: create mapping from article_id to unpublished_item_id for "new" articles
    article_to_unpublished_id = {}

    for article in filtered_articles:
        article_id = article.get('id')
        result = deduplication_results.get(article_id, {'status': 'new', 'matched_id': None, 'confidence': 0.0})

        if result['status'] == 'new':
            new_item = {
                'topic_text': article.get('summary', article.get('title', '')),
                'fit_level': article.get('relevance', 5),
                'original_texts': [article.get('text', '')],
                'link': article.get('link', ''),
                'pub_date': article.get('pub_date', '')
            }
            state = add_to_unpublished(state, new_item)
            created_item = state['unpublished_news'][-1]
            article_to_unpublished_id[article_id] = created_item['id']
            logger.info(f"Added new article {article_id} to unpublished as {created_item['id']}")

    # Second pass: process remaining articles
    for article in filtered_articles:
        article_id = article.get('id')
        result = deduplication_results.get(article_id, {'status': 'new', 'matched_id': None, 'confidence': 0.0})

        # Skip articles already processed as "new"
        if article_id in article_to_unpublished_id:
            continue

        if result['status'] == 'match_unpublished':
            matched_id = result.get('matched_id')
            if matched_id:
                if matched_id in article_to_unpublished_id:
                    actual_unpublished_id = article_to_unpublished_id[matched_id]
                else:
                    actual_unpublished_id = matched_id

                existing_item = next((item for item in state.get('unpublished_news', []) if item['id'] == actual_unpublished_id), None)
                if existing_item:
                    new_text = article.get('text', '')
                    new_pub_date = article.get('pub_date', '')
                    updates = {
                        'original_texts': new_text
                    }
                    if new_pub_date:
                        updates['last_update_time'] = new_pub_date
                    else:
                        updates['last_update_time'] = None
                    state = update_unpublished_item(state, actual_unpublished_id, updates)
                    logger.info(f"Updated unpublished item {actual_unpublished_id}. Added new text version")
                else:
                    logger.warning(f"Matched item {actual_unpublished_id} not found in unpublished news, treating as new")
                    new_item = {
                        'topic_text': article.get('summary', article.get('title', '')),
                        'fit_level': article.get('relevance', 5),
                        'original_texts': [article.get('text', '')],
                        'link': article.get('link', ''),
                        'pub_date': article.get('pub_date', '')
                    }
                    state = add_to_unpublished(state, new_item)

        elif result['status'] == 'match_history':
            logger.info(f"Article {article_id} matches history, discarding")

    # Recalculate all publish_meters (removing items with time_coef = 0)
    logger.info("Recalculating publish-meters")
    unpublished_news = state.get('unpublished_news', [])
    updated_unpublished = recalculate_all_publish_meters(unpublished_news)
    state['unpublished_news'] = updated_unpublished

    # Update last_check_time
    state = update_last_check_time(state)

    # Save updated state
    write_state(state, state_path)
    logger.info(f"Saved updated state with {len(state['unpublished_news'])} unpublished items and updated last_check_time")


def stream_publish_top(state_path: str = "/tmp/stream_state.json", history_path: str = "/tmp/history.json") -> None:
    """
    Publish the top unpublished item based on publish-meter.

    Args:
        state_path: Path to the state file (default: "/tmp/stream_state.json")
        history_path: Path to the history file (default: "/tmp/history.json")
    """
    logger.info("Starting streaming publish top item")

    # Read state
    state = read_state(state_path)

    # Get top unpublished item
    top_item = get_top_unpublished_item(state)

    if not top_item:
        logger.info("No unpublished items to publish")
        return

    logger.info(f"Top item: {top_item.get('id')} with publish-meter {top_item.get('publish_meter', 0)}")

    # Prepare message using AI from collected original texts
    topic_summary = top_item.get('topic_text', '')
    original_texts = top_item.get('original_texts', [])

    if not topic_summary:
        logger.warning(f"Top item {top_item.get('id')} has no topic_text, skipping")
        return

    if not original_texts:
        logger.warning(f"Top item {top_item.get('id')} has no original_texts, skipping")
        return

    # Prepare text versions for the prompt
    original_texts_text = ""
    for idx, text in enumerate(original_texts, start=1):
        original_texts_text += f"Version {idx}:\n{text}\n\n"

    # Build the prompt
    prompt = STREAM_PUBLISH_PREPARATION_PROMPT.format(
        topic_summary=topic_summary,
        original_texts=original_texts_text
    )

    try:
        response = get_ai_response(prompt, json_schema=STREAM_PUBLISH_PREPARATION_JSON_SCHEMA)
        result = json.loads(response)

        title = result.get('title', '')
        description = result.get('description', '')

        logger.info(f"AI prepared message: {title}")

        if not title:
            logger.warning(f"AI failed to prepare message for item {top_item.get('id')}, using topic_text")
            title = topic_summary

    except Exception as e:
        logger.error(f"Error preparing message with AI: {e}, using topic_text")
        return
    # Publish to Telegram
    try:
        message = f"<b>{title}</b>\n\n{description}"
        link = top_item.get('link', '')
        if link:
            message += f"\n\n{link}"
        send_message(message)
        logger.info(f"Published item {top_item.get('id')} to Telegram")

        update_history(history_path, title, description)

        # Remove from unpublished_news
        state = remove_from_unpublished(state, top_item.get('id'))

        # Save updated state
        write_state(state, state_path)
        logger.info(f"Removed published item from unpublished and saved state")

    except Exception as e:
        logger.error(f"Error publishing item: {e}")


