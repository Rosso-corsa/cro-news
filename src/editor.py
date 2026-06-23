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
from src.gemini_adapter import get_ai_response
from src.telegram_adapter import send_message
from src.file_manager import read_file, write_file
from src.prompts import NEWS_ANALYSIS_PROMPT, NEWS_GROUPING_PROMPT, DIGEST_PREPARATION_PROMPT
from src.history import update_history

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def collect_articles(config_path: str = "config.json", output_path: str = "/tmp/articles.json") -> None:
    """
    Collect recent news articles with full content extracted and save to file.

    This function fetches recent news items from RSS feeds, extracts
    the full article text for each item, and saves them to a JSON file.
    Items where content extraction fails are skipped.

    Args:
        config_path: Path to the JSON configuration file (default: "config.json")
        output_path: Path to the output JSON file (default: "articles.json")
    """
    logger.info("Starting article collection")

    # Fetch recent news items from RSS feeds
    news_items = get_recent_news(config_path)
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

    # Write all articles to JSON file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    logger.info(f"Saved {len(articles)} articles to {output_path}")


def categorize_articles(input_path: str = "/tmp/articles.json", output_path: str = "/tmp/categorization.json") -> None:
    """
    Categorize articles using AI analysis.

    This function reads articles from a JSON file, sends them to
    Gemini AI for categorization in batches, and saves the results.

    Args:
        input_path: Path to the input articles file (default: "articles.json")
        output_path: Path to the output categorization file (default: "categorization.json")
    """
    logger.info(f"Starting article categorization from {input_path}")

    # Read articles from JSON file
    with open(input_path, "r", encoding="utf-8") as f:
        articles = json.load(f)

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
                "id": {"type": "string"}
            },
            "required": ["summary", "entities", "topics", "id"]
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

    # Save all results to categorization file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    logger.info(f"Saved {len(all_results)} categorized articles to {output_path}")


def group_articles(input_path: str = "/tmp/categorization.json", output_path: str = "/tmp/groups.json") -> None:
    """
    Group articles into meaningful clusters using AI analysis.

    This function reads categorized articles from a JSON file, sends them to
    Gemini AI for grouping into clusters, and saves the results.

    Args:
        input_path: Path to the input categorization file (default: "categorization.json")
        output_path: Path to the output groups file (default: "groups.json")
    """
    logger.info(f"Starting article grouping from {input_path}")

    # Read categorized articles from JSON file
    with open(input_path, "r", encoding="utf-8") as f:
        articles = json.load(f)

    logger.info(f"Read {len(articles)} categorized articles from {input_path}")

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

        # Save groups to file
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved {len(result['clusters'])} groups to {output_path}")

    except Exception as e:
        logger.error(f"Error grouping articles: {e}")


def prepare_digest(groups_path: str = "/tmp/groups.json", articles_path: str = "/tmp/articles.json", output_path: str = "/tmp/digest.json", config_path: str = "config.json") -> None:
    """
    Prepare a news digest by analyzing grouped articles and selecting key topics.

    This function reads groups and articles from JSON files, replaces news_ids with
    full article details (link, title, text), and sends them to Gemini AI to create
    a digest of 3-5 key topics of the day in Russian.

    Args:
        groups_path: Path to the input groups file (default: "groups.json")
        articles_path: Path to the input articles file (default: "articles.json")
        output_path: Path to the output digest file (default: "digest.json")
        config_path: Path to the configuration file (default: "config.json")
    """
    logger.info(f"Starting digest preparation from {groups_path} and {articles_path}")

    # Read groups and articles from JSON files
    with open(groups_path, "r", encoding="utf-8") as f:
        groups = json.load(f)

    with open(articles_path, "r", encoding="utf-8") as f:
        articles = json.load(f)

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

    # Build the prompt
    prompt = DIGEST_PREPARATION_PROMPT.format(cluster_news=cluster_news)

    # JSON schema for structured output
    json_schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "link": {"type": "string"},
                "importance_reason": {"type": "string"}
            },
            "required": ["title", "description", "link", "importance_reason"]
        }
    }

    try:
        response = get_ai_response(prompt, json_schema=json_schema)
        result = json.loads(response)

        # Save digest to file
        write_file(result, output_path, config_path)
        logger.info(f"Saved digest to {output_path}")

    except Exception as e:
        logger.error(f"Error preparing digest: {e}")


def publish_to_telegram(digest_path: str = "/tmp/digest.json", config_path: str = "config.json") -> None:
    """
    Publish news digest to Telegram channel.

    This function reads the digest from a JSON file (local or S3), transforms it to Telegram message format,
    and sends it to a Telegram channel using the telegram_adapter module. Each news item includes
    title (bold), description, and link. Items are combined into one message separated by empty lines.

    Args:
        digest_path: Path to the input digest file (default: "digest.json")
        config_path: Path to the configuration file with Telegram credentials (default: "config.json")
    """
    logger.info("Starting Telegram publish")

    # Read digest from JSON file
    digest = read_file(digest_path, config_path)
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
    send_message(message, config_path)


def publish_article_to_telegram(digest_path: str = "/tmp/digest.json", config_path: str = "config.json", history_path: str = "/tmp/history.json") -> None:
    """
    Publish the first article from digest to Telegram channel and remove it from digest.

    This function reads the digest from a JSON file (local or S3), takes the first news item,
    publishes it to Telegram, removes it from the digest, and writes the updated digest back.
    This allows publishing articles one at a time. Also records the published article to history.

    Args:
        digest_path: Path to the input/output digest file (default: "digest.json")
        config_path: Path to the configuration file with Telegram and S3 credentials (default: "config.json")
        history_path: Path to the history file for tracking published articles (default: "history.json")
    """
    logger.info("Starting single article publish to Telegram")

    # Read digest from JSON file
    digest = read_file(digest_path, config_path)
    logger.info(f"Read {len(digest)} items from {digest_path}")

    # Check if digest is empty
    if not digest:
        logger.warning("Digest is empty, nothing to publish")
        return

    # Take the first item
    first_item = digest[0]
    logger.info(f"Publishing article: {first_item.get('title', 'Untitled')}")

    # Transform first item to Telegram message format
    title = first_item.get('title', '')
    description = first_item.get('description', '')
    link = first_item.get('link', '')

    # Format: title (bold), description, link
    message = f"<b>{title}</b>\n\n{description}\n\n{link}"

    # Send to Telegram using the adapter
    send_message(message, config_path)

    # Record to history
    update_history(history_path, title, description, config_path)

    # Remove the first item from digest
    updated_digest = digest[1:]
    logger.info(f"Removed published article. Remaining items: {len(updated_digest)}")

    # Write updated digest back
    write_file(updated_digest, digest_path, config_path)
    logger.info(f"Updated digest saved to {digest_path}")


if __name__ == "__main__":
    collect_articles()
    #categorize_articles()
    #group_articles()
    #prepare_digest()
    #publish_to_telegram()