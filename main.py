#!/usr/bin/env python3
"""
Main entry point for the cro-news application.
"""

import logging
import argparse
from src.editor import collect_articles, categorize_articles, group_articles, prepare_digest, publish_to_telegram

logging.getLogger().setLevel(logging.INFO)

def handler(mode: str = "FULL"):
    if mode == "FULL":
        collect_articles()
        categorize_articles()
        group_articles()
        prepare_digest()
        publish_to_telegram()
    elif mode == "ONLY_PUBLISH":
        publish_to_telegram()
    else:
        raise ValueError(f"Invalid mode: {mode}. Must be 'FULL' or 'ONLY_PUBLISH'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the cro-news handler")
    parser.add_argument("--mode", type=str, default="FULL", choices=["FULL", "ONLY_PUBLISH"],
                        help="Mode of operation (FULL or ONLY_PUBLISH)")
    args = parser.parse_args()
    handler(args.mode)
