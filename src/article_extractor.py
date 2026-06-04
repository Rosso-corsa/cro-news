#!/usr/bin/env python3
"""
Article Content Extractor Module

This module extracts article text from URLs using the newspaper3k library.
It is designed to work with Croatian news sites and handles errors gracefully.
"""

import logging
from typing import Optional
import newspaper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_content(url: str) -> Optional[str]:
    """
    Extract article text from a given URL.
    
    Args:
        url: URL of the article to extract content from
    
    Returns:
        Article text as a string, or None if extraction fails
    """
    if not url:
        logger.warning("Empty URL provided")
        return None
    
    try:
        logger.debug(f"Extracting content from: {url}")
        
        # Create and configure the article
        article = newspaper.Article(url)
        
        # Download and parse the article
        article.download()
        article.parse()
        
        # Extract the text content
        if article.text:
            logger.debug(f"Successfully extracted {len(article.text)} characters from {url}")
            return article.text
        else:
            logger.warning(f"No text content found at: {url}")
            return None
            
    except newspaper.ArticleException as e:
        logger.warning(f"Newspaper library error for {url}: {e}")
        return None
    except Exception as e:
        logger.warning(f"Unexpected error extracting content from {url}: {e}")
        return None


if __name__ == "__main__":
    test_url = "https://www.index.hr/sport/clanak/arteta-mogao-nam-je-sudac-suditi-penal-proucavao-sam-sto-se-sve-sudilo/2797620.aspx"
    content = get_content(test_url)
    if content:
        print(f"Extracted content ({len(content)} characters):")
        print(content)
        print("---------------")
    else:
        print("Failed to extract content")
