#!/usr/bin/env python3
"""
Main entry point for the cro-news application.
"""

import logging
from src.editor import collect_articles, categorize_articles, group_articles, prepare_digest, publish_to_telegram

logging.getLogger().setLevel(logging.INFO)

def handler():
    collect_articles()
    categorize_articles()
    group_articles()
    prepare_digest()
    publish_to_telegram()


if __name__ == "__main__":
    handler()
