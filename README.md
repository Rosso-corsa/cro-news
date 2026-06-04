# CRO News

A Python project for fetching and processing news from RSS feeds.

## Features

- Fetches news items from multiple RSS feeds
- Filters items from the last 24 hours
- Configurable feed sources via JSON configuration
- Graceful error handling with logging

## Installation

1. Create a virtual environment:
```bash
python -m venv venv
```

2. Activate the virtual environment:
- Windows: `venv\Scripts\activate`
- Unix/macOS: `source venv/bin/activate`

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

Edit `config.json` to add or modify RSS feed URLs:

```json
{
  "rss_feeds": [
    {
      "name": "Feed Name",
      "url": "https://example.com/feed.xml"
    }
  ]
}
```

## Usage

Run the main script to fetch and display recent news:
```bash
python main.py
```

Or use the RSS reader module directly in your code:

```python
from src.rss_reader import get_recent_news

# Fetch news from all configured feeds
news_items = get_recent_news()

# Process the returned data structure
for item in news_items:
    print(f"{item['title']} - {item['source_feed']}")
```

## Testing

Run the test suite to verify the implementation:

```bash
python tests/test_rss_reader.py
```

The test class includes two test functions:
- `test_fetch_all_feeds_from_config()`: Fetches news from all feeds in config.json
- `test_fetch_single_feed()`: Fetches news from a single feed specified by parameter

## Data Structure

The `get_recent_news()` function returns a list of dictionaries, each containing:
- `title`: News item title
- `link`: URL to the full article
- `description`: Article summary/description
- `pub_date`: Publication date
- `source_feed`: Name of the RSS feed source

## Development

Add your dependencies to `requirements.txt` and install them as needed.
