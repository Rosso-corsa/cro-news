#!/usr/bin/env python3
"""
Test class for RSS Reader module.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config import load_config
from src.rss_reader import RSSReader, get_recent_news


def test_fetch_feed_skips_cloudflare_block_page(monkeypatch):
    """Blocked HTML pages should be ignored before XML parsing."""

    class FakeResponse:
        status_code = 403
        headers = {'content-type': 'text/html; charset=UTF-8'}
        text = '<html><body>Attention Required! | Cloudflare</body></html>'
        content = text.encode('utf-8')

    def fake_get(url, headers=None, timeout=None):
        return FakeResponse()

    def fail_parse(*args, **kwargs):
        raise AssertionError('feedparser.parse should not run on blocked HTML response')

    monkeypatch.setattr('src.rss_reader.requests.get', fake_get)
    monkeypatch.setattr('src.rss_reader.feedparser.parse', fail_parse)
    load_config(config_path='config.json')

    reader = RSSReader()
    items = reader.fetch_feed({'name': 'Blocked Feed', 'url': 'https://example.com/feed'})

    assert items == []


class TestRSSReader:
    """Test class for RSS Reader functionality."""
    
    def test_fetch_all_feeds_from_config(self):
        """
        Test fetching news from all feeds configured in config.json.
        """
        print("\n--- Test: Fetch all feeds from config ---")
        reader = RSSReader("config.json")
        news_items = reader.fetch_all_feeds()
        
        print(f"Total feeds configured: {len(reader.feeds)}")
        print(f"Total news items fetched: {len(news_items)}")
        
        for feed in reader.feeds:
            feed_items = [item for item in news_items if item['source_feed'] == feed['name']]
            print(f"  - {feed['name']}: {len(feed_items)} items")
            print(f"Example: {feed_items[0] if feed_items else ''}")
        
        assert isinstance(news_items, list), "News items should be a list"
        print("✓ Test passed: Returns list of news items")
    
    def test_fetch_single_feed(self):
        """
        Test fetching news from a single feed specified by parameter.
        """
        print("\n--- Test: Fetch single feed ---")
        reader = RSSReader("config.json")
        
        if not reader.feeds:
            print("No feeds configured in config.json")
            return
        
        # Use the first feed from config
        feed_config = reader.feeds[0]
        print(f"Testing feed: {feed_config['name']} ({feed_config['url']})")
        
        news_items = reader.fetch_feed(feed_config)
        
        print(f"News items fetched: {len(news_items)}")
        for item in news_items[:3]:  # Show first 3 items
            print(f"  - {item['title']}")
        
        assert isinstance(news_items, list), "News items should be a list"
        print("✓ Test passed: Returns list of news items from single feed")


if __name__ == "__main__":
    tester = TestRSSReader()
    
    # Run all tests
    tester.test_fetch_all_feeds_from_config()
    tester.test_fetch_single_feed()
    
    print("\n=== All tests completed ===")
