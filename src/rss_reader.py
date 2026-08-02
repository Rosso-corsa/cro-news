#!/usr/bin/env python3
"""
RSS Feed Reader Module

This module connects to multiple RSS feeds, retrieves news items from the last 24 hours,
and returns them as Python data structures.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from dateutil import parser as date_parser
import feedparser
from src.config import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RSSReader:
    """RSS Feed Reader class for fetching and filtering news items."""

    def __init__(self):
        """
        Initialize the RSS Reader with global configuration.
        """
        config = get_config()
        self.feeds = config.get('rss_feeds', [])
    
    def _is_newer_than_timestamp(self, pub_date: Any, since_timestamp: str = None) -> bool:
        if not pub_date:
            return False
        try:
            # Parse the date if it's a string
            if isinstance(pub_date, str):
                parsed_date = date_parser.parse(pub_date)
            elif isinstance(pub_date, datetime):
                parsed_date = pub_date
            else:
                return False

            # Normalize to naive UTC
            if parsed_date.tzinfo is not None:
                parsed_date = parsed_date.astimezone(timezone.utc).replace(tzinfo=None)

            # Calculate the cutoff time
            if since_timestamp:
                cutoff_time = datetime.fromisoformat(since_timestamp)
                if cutoff_time.tzinfo is not None:
                    cutoff_time = cutoff_time.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                # Default to 24 hours ago (UTC, naive)
                cutoff_time = datetime.utcnow() - timedelta(hours=24)

            return parsed_date >= cutoff_time
        except Exception as e:
            logger.warning(f"Error parsing date '{pub_date}': {e}")
            return False    


    def fetch_feed(self, feed_config: Dict[str, str], since_timestamp: str = None) -> List[Dict[str, Any]]:
        """
        Fetch and parse items from a single RSS feed.

        Args:
            feed_config: Dictionary containing 'name' and 'url' of the feed
            since_timestamp: Optional ISO timestamp to filter items newer than this time

        Returns:
            List of news items from the last 24 hours (or since_timestamp if provided)
        """
        feed_name = feed_config.get('name', 'Unknown')
        feed_url = feed_config.get('url', '')
        if not feed_url:
            logger.warning(f"No URL provided for feed: {feed_name}")
            return []
        try:
            logger.info(f"Fetching feed: {feed_name} ({feed_url})")
            feed = feedparser.parse(feed_url)
            if feed.bozo:
                logger.warning(f"Feed parsing warning for {feed_name}: {feed.bozo_exception}")

            items = []
            for entry in feed.entries:
                # Extract publication date
                pub_date = entry.get('published') or entry.get('pubDate') or entry.get('updated')

                # Filter by time
                if self._is_newer_than_timestamp(pub_date, since_timestamp):
                    item = {
                        'title': entry.get('title', ''),
                        'link': entry.get('link', ''),
                        'description': entry.get('description', '') or entry.get('summary', ''),
                        'pub_date': pub_date,
                        'source_feed': feed_name
                    }
                    items.append(item)

            time_filter_desc = f"since {since_timestamp}" if since_timestamp else "in the last 24 hours"
            logger.info(f"Found {len(items)} items from {feed_name} {time_filter_desc}")
            return items

        except Exception as e:
            logger.error(f"Error fetching feed {feed_name}: {e}")
            return []
    
    def fetch_all_feeds(self, since_timestamp: str = None) -> List[Dict[str, Any]]:
        all_items = []

        for feed_config in self.feeds:
            items = self.fetch_feed(feed_config, since_timestamp)
            all_items.extend(items)

        logger.info(f"Total items fetched from all feeds: {len(all_items)}")
        return all_items


def get_recent_news(since_timestamp: str = None) -> List[Dict[str, Any]]:
    """
    Convenience function to fetch recent news from all configured feeds.

    Args:
        since_timestamp: Optional ISO timestamp to filter items newer than this time

    Returns:
        List of news items from the last 24 hours (or since_timestamp if provided)
    """
    reader = RSSReader()
    return reader.fetch_all_feeds(since_timestamp)


if __name__ == "__main__":
    # Test the module
    from src.config import load_config
    load_config()
    print("\n--- Test: Fetch all feeds from config ---")
    reader = RSSReader()
    news_items = reader.fetch_all_feeds()

    print(f"Total feeds configured: {len(reader.feeds)}")
    print(f"Total news items fetched: {len(news_items)}")

    for feed in reader.feeds:
        feed_items = [item for item in news_items if item['source_feed'] == feed['name']]
        print(f"  - {feed['name']}: {len(feed_items)} items")
        print(f"Example: {feed_items[0] if feed_items else ''}")