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
from typing import List, Dict
from src.rss_reader import get_recent_news
from src.article_extractor import get_content
from src.ai_adapter import get_ai_response
from src.telegram_adapter import send_message
from src.file_manager import read_file, write_file
from src.config import get_config
from src.prompts import NEWS_ANALYSIS_PROMPT, NEWS_GROUPING_PROMPT, DIGEST_PREPARATION_PROMPT, CHANNEL_REVIEW_PROMPT
from src.history import update_history, read_history

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def collect_articles(output_path: str = "/tmp/articles.json") -> None:
    """
    Collect recent news articles with full content and save to file.

    Args:
        output_path: Path to the output JSON file (default: "articles.json")
    """
    logger.info("Starting article collection")

    # Fetch recent news items from RSS feeds
    news_items = get_recent_news()
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
                'source': source
            }
            articles.append(article)
        else:
            logger.warning(f"Failed to extract content for: {title} - skipping")

    logger.info(f"Content extraction has been finished. Collected {len(articles)} articles with full content")

    # Add IDs to articles before saving
    for idx, article in enumerate(articles, start=1):
        article['id'] = str(idx)

    write_file(articles, output_path, force_local=True)

    logger.info(f"Saved {len(articles)} articles to {output_path}")


def categorize_articles(input_path: str = "/tmp/articles.json", output_path: str = "/tmp/categorization.json") -> None:
    """
    Categorize articles using AI analysis.

    Args:
        input_path: Path to the input articles file (default: "articles.json")
        output_path: Path to the output categorization file (default: "categorization.json")
    """
    logger.info(f"Starting article categorization from {input_path}")
    articles = read_file(input_path, force_local=True)

    logger.info(f"Read {len(articles)} articles from {input_path}")

    # Send articles to Gemini in batches of 50
    batch_size = 50
    all_results = []

    # JSON schema for structured output
    json_schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "entities": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "topics": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "relevance": {"type": "integer"},
                "id": {"type": "string"}
            },
            "required": ["summary", "entities", "topics", "relevance", "id"]
        }
    }

    for i in range(0, len(articles), batch_size):
        batch = articles[i:i + batch_size]
        logger.info(f"Processing batch {(i // batch_size) + 1}/{(len(articles) + batch_size - 1) // batch_size} ({len(batch)} articles)")

        # Prepare news data for the prompt
        news_data = ""
        for article in batch:
            news_data += f"ID: {article['id']}\n"
            news_data += f"Title: {article['title']}\n"
            news_data += f"Text: {article['text']}\n"
            news_data += "-------------\n"

        prompt = NEWS_ANALYSIS_PROMPT.format(news_data=news_data)
        try:
            response = get_ai_response(prompt, json_schema=json_schema)
            result = json.loads(response)
            all_results.extend(result)
            logger.info(f"Batch {(i // batch_size) + 1} completed successfully")

        except Exception as e:
            logger.error(f"Error processing batch {(i // batch_size) + 1}: {e}")
            for article in batch:
                all_results.append({
                    "summary": "Analysis failed",
                    "entities": [],
                    "topics": [],
                    "id": article['id']
                })

    write_file(all_results, output_path, force_local=True)

    logger.info(f"Saved {len(all_results)} categorized articles to {output_path}")


def group_articles(input_path: str = "/tmp/categorization.json", output_path: str = "/tmp/groups.json") -> None:
    """
    Group articles into clusters using AI analysis.

    Args:
        input_path: Path to the input categorization file (default: "categorization.json")
        output_path: Path to the output groups file (default: "groups.json")
    """
    logger.info(f"Starting article grouping from {input_path}")
    articles = read_file(input_path, force_local=True)
    logger.info(f"Read {len(articles)} categorized articles from {input_path}")

    filtered_articles = [article for article in articles if not ('relevance' in article and article['relevance'] <= 4)]
    logger.info(f"Filtered out {len(articles) - len(filtered_articles)} articles with relevance <= 4. Remaining: {len(filtered_articles)}")
    articles = filtered_articles

    # Prepare news metadata for the prompt
    news_metadata = ""
    for article in articles:
        news_metadata += f"ID: {article['id']}\n"
        news_metadata += f"Brief description: {article['summary']}\n"
        news_metadata += f"Topics: {', '.join(article['topics'])}\n"
        news_metadata += f"Entities: {', '.join(article['entities'])}\n"
        news_metadata += "-------------\n"

    # Build the prompt
    prompt = NEWS_GROUPING_PROMPT.format(news_metadata=news_metadata)

    # JSON schema for structured output
    json_schema = {
        "type": "object",
        "properties": {
            "clusters": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string"},
                        "news_ids": {
                            "type": "array",
                            "items": {"type": "integer"}
                        }
                    },
                    "required": ["topic", "news_ids"]
                }
            }
        },
        "required": ["clusters"]
    }

    try:
        response = get_ai_response(prompt, json_schema=json_schema)
        result = json.loads(response)
        write_file(result, output_path, force_local=True)

        logger.info(f"Saved {len(result['clusters'])} groups to {output_path}")

    except Exception as e:
        logger.error(f"Error grouping articles: {e}")


def prepare_digest(groups_path: str = "/tmp/groups.json", articles_path: str = "/tmp/articles.json", output_path: str = "/tmp/digest.json", history_path: str = "/tmp/history.json") -> None:
    """
    Prepare news digest from grouped articles.

    Args:
        groups_path: Path to the input groups file (default: "groups.json")
        articles_path: Path to the input articles file (default: "articles.json")
        output_path: Path to the output digest file (default: "digest.json")
        history_path: Path to the history file with previously published articles (default: "history.json")
    """
    logger.info(f"Starting digest preparation from {groups_path} and {articles_path}")

    # Read groups and articles from JSON files
    groups = read_file(groups_path, force_local=True)
    articles = read_file(articles_path, force_local=True)

    logger.info(f"Read {len(groups['clusters'])} groups and {len(articles)} articles")

    # Create a mapping from article id to article data
    articles_map = {article['id']: article for article in articles}

    # Prepare cluster news data by replacing news_ids with full article details
    cluster_news = ""
    for cluster in groups['clusters']:
        cluster_news += f"Topic: {cluster['topic']}\n"
        cluster_news += "Articles:\n"
        for news_id in cluster['news_ids']:
            article = articles_map.get(str(news_id))
            if article:
                cluster_news += f"  Title: {article['title']}\n"
                cluster_news += f"  Text: {article['text']}\n"
                cluster_news += f"  Link: {article['link']}\n"
                cluster_news += "  ---\n"
        cluster_news += "======END OF CLUSTER=======\n"

    # Read and format history
    history = read_history(history_path)
    history_news = ""
    for entry in history:
        history_news += f"Title: {entry.get('title', '')}\n"
        history_news += f"Text: {entry.get('text', '')}\n"
        history_news += "---\n"

    # Build the prompt
    prompt = DIGEST_PREPARATION_PROMPT.format(cluster_news=cluster_news, history=history_news)

    # JSON schema for structured output
    json_schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "link": {"type": "string"},
                "resolution": {"type": "integer"},
                "justification": {"type": "string"}
            },
            "required": ["title", "description", "link", "resolution"]
        }
    }

    try:
        response = get_ai_response(prompt, json_schema=json_schema)
        result = json.loads(response)

        # Save digest to file
        write_file(result, output_path)

    except Exception as e:
        logger.error(f"Error preparing digest: {e}")


def publish_to_telegram(digest_path: str = "/tmp/digest.json") -> None:
    """
    Publish news digest to Telegram channel.

    Args:
        digest_path: Path to the input digest file (default: "digest.json")
    """
    logger.info("Starting Telegram publish")

    # Read digest from JSON file
    digest = read_file(digest_path)
    logger.info(f"Read {len(digest)} items from {digest_path}")

    # Transform digest to Telegram message format
    message_parts = []
    for item in digest:
        title = item.get('title', '')
        description = item.get('description', '')
        link = item.get('link', '')

        # Format: title (bold), description, link
        message_parts.append(f"<b>{title}</b>")
        message_parts.append(description)
        message_parts.append(link)
        message_parts.append("")  # Empty line separator

    message = "\n".join(message_parts).strip()

    # Send to Telegram using the adapter
    send_message(message)


def publish_article_to_telegram(digest_path: str = "/tmp/digest.json", history_path: str = "/tmp/history.json") -> None:
    """
    Publish single article from digest to Telegram.

    Args:
        digest_path: Path to the input/output digest file (default: "digest.json")
        history_path: Path to the history file for tracking published articles (default: "history.json")
    """
    logger.info("Starting single article publish to Telegram")

    # Read digest from JSON file
    digest = read_file(digest_path)
    logger.info(f"Read {len(digest)} items from {digest_path}")

    while digest and digest[0].get('resolution') == 0:
        digest = digest[1:]
        logger.info(f"Skipped non-published article. Remaining items: {len(digest)}")

    if not digest:
        logger.warning("Digest is empty, nothing to publish")
        return
    first_item = digest[0]
    logger.info(f"Publishing article: {first_item.get('title', 'Untitled')}")

    # Transform first item to Telegram message format
    title = first_item.get('title', '')
    description = first_item.get('description', '')
    link = first_item.get('link', '')

    # Format: title (bold), description, link
    message = f"<b>{title}</b>\n\n{description}\n\n{link}"

    # Send to Telegram using the adapter
    send_message(message)

    # Record to history
    update_history(history_path, title, description)

    # Remove the first item from digest
    updated_digest = digest[1:]
    logger.info(f"Removed published article. Remaining items: {len(updated_digest)}")

    # Write updated digest back
    write_file(updated_digest, digest_path)


def review_channel(message_limit: int = 15, history_path: str = "/tmp/history.json") -> None:
    """
    Review recent published messages from history and suggest prompt improvements.

    This function reads the history file containing published articles,
    analyzes them against the current digest prompt, and sends
    suggestions for prompt improvements to a review channel.

    Args:
        message_limit: Number of recent messages to analyze (default: 15)
        history_path: Path to the history file (default: "/tmp/history.json")
    """
    logger.info(f"Starting channel review with message limit: {message_limit}")

    # Read history file
    history = read_history(history_path)
    
    if not history:
        logger.warning("No messages found in history, skipping review")
        return

    # Get the most recent messages (history is in chronological order, so take from end)
    recent_messages = history[-message_limit:] if len(history) > message_limit else history
    logger.info(f"Analyzing {len(recent_messages)} recent messages from history")

    # Format messages for the prompt - reconstruct the Telegram message format
    messages_text = ""
    for idx, entry in enumerate(recent_messages, 1):
        title = entry.get('title', '')
        text = entry.get('text', '')
        message = f"<b>{title}</b>\n\n{text}"
        messages_text += f"Message {idx}:\n{message}\n{'-'*50}\n"

    # Build the review prompt
    prompt = CHANNEL_REVIEW_PROMPT.format(
        current_prompt=DIGEST_PREPARATION_PROMPT,
        messages=messages_text
    )

    # JSON schema for structured output
    json_schema = {
        "type": "object",
        "properties": {
            "needs_improvement": {"type": "boolean"},
            "new_prompt": {"type": "string"},
            "justification": {"type": "string"}
        },
        "required": ["needs_improvement", "justification"]
    }

    try:
        response = get_ai_response(prompt, json_schema=json_schema)
        result = json.loads(response)
        
        logger.info(f"Review completed. Needs improvement: {result.get('needs_improvement')}")
        config = get_config()
        review_channel_id = config.get('telegram_channel_review_id', '')
        
        if not review_channel_id:
            logger.warning("Review channel ID not configured, skipping notification")
            return

        if result.get('needs_improvement'):
            message = f"<b>Channel Review: Prompt Improvement Suggested</b>\n\n"
            message += f"<b>Justification:</b>\n{result.get('justification', '')}\n\n"
            message += f"<b>Suggested New Prompt:</b>\n<pre>{result.get('new_prompt', '')}</pre>"
        else:
            message = f"<b>Channel Review: No Issues Found</b>\n\n"
            message += result.get('justification', 'Messages meet quality standards.')

        send_message(message, channel_id=review_channel_id)
        logger.info("Review results sent to review channel")

    except Exception as e:
        logger.error(f"Error during channel review: {e}")


if __name__ == "__main__":
    collect_articles()
    categorize_articles()
    group_articles()
    prepare_digest()
    publish_to_telegram()