#!/usr/bin/env python3
"""
Main entry point for the cro-news application.
"""

import logging
import argparse
from src.config import load_config
from src.editor import collect_articles, categorize_articles, group_articles, prepare_digest, publish_article_to_telegram, review_channel, stream_collect_articles, stream_process_articles, stream_publish_top

logging.getLogger().setLevel(logging.INFO)

def handler(mode: str = "FULL", message_limit: int = 15):
    if mode == "FULL":
        collect_articles()
        categorize_articles()
        group_articles()
        prepare_digest()
    elif mode == "ONLY_PUBLISH":
        publish_article_to_telegram()
    elif mode == "CHANNEL_REVIEW":
        review_channel(message_limit=message_limit)
    elif mode == "STREAM":
        stream_collect_articles()
        stream_process_articles()
        stream_publish_top()
    else:
        raise ValueError(f"Invalid mode: {mode}. Must be 'FULL', 'ONLY_PUBLISH', 'CHANNEL_REVIEW', or 'STREAM'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the cro-news handler")
    parser.add_argument("--mode", type=str, default="FULL", choices=["FULL", "ONLY_PUBLISH", "CHANNEL_REVIEW", "STREAM"],
                        help="Mode of operation (FULL, ONLY_PUBLISH, CHANNEL_REVIEW, or STREAM)")
    parser.add_argument("--message-limit", type=int, default=15,
                        help="Number of messages to analyze in CHANNEL_REVIEW mode (default: 15)")
    parser.add_argument("--ai-api-key", type=str, default=None,
                        help="AI API key (overrides .env)")
    parser.add_argument("--ai-model", type=str, default=None,
                        help="AI model name (overrides .env)")
    parser.add_argument("--ai-model-categorization", type=str, default=None,
                        help="AI model name for categorization (overrides .env)")
    parser.add_argument("--telegram-bot-token", type=str, default=None,
                        help="Telegram bot token (overrides .env)")
    parser.add_argument("--telegram-channel-id", type=str, default=None,
                        help="Telegram channel ID (overrides .env)")
    parser.add_argument("--telegram-channel-review-id", type=str, default=None,
                        help="Telegram review channel ID (overrides .env)")
    parser.add_argument("--s3-access-key", type=str, default=None,
                        help="S3 access key (overrides .env)")
    parser.add_argument("--s3-secret-key", type=str, default=None,
                        help="S3 secret key (overrides .env)")
    args = parser.parse_args()

    # Load configuration with secrets
    load_config(
        ai_api_key=args.ai_api_key,
        ai_model=args.ai_model,
        ai_model_categorization=args.ai_model_categorization,
        telegram_bot_token=args.telegram_bot_token,
        telegram_channel_id=args.telegram_channel_id,
        telegram_channel_review_id=args.telegram_channel_review_id,
        s3_access_key=args.s3_access_key,
        s3_secret_key=args.s3_secret_key
    )

    handler(args.mode, message_limit=args.message_limit)
