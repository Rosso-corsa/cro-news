#!/usr/bin/env python3
"""
Config Module

This module handles configuration loading and management.
It loads config.json once at startup and merges secrets from
CLI arguments or .env file.
"""

import json
import logging
import os
from typing import Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Global configuration dictionary
CONFIG = {}
_CONFIG_LOADED = False


def load_config(
    gemini_api_key: Optional[str] = None,
    telegram_bot_token: Optional[str] = None,
    telegram_channel_id: Optional[str] = None,
    s3_access_key: Optional[str] = None,
    s3_secret_key: Optional[str] = None,
    config_path: str = "config.json"
) -> dict:
    global CONFIG, _CONFIG_LOADED

    # Load .env file if it exists (for local development)
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
        logger.info(f"Loaded .env file from {env_path}")

    # Load base config from config.json
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            CONFIG = json.load(f)
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing configuration file: {e}")
        raise

    # Override secrets from CLI args or environment variables
    # CLI args take precedence over environment variables
    if gemini_api_key or os.getenv("GEMINI_API_KEY"):
        CONFIG["gemini_api_key"] = gemini_api_key or os.getenv("GEMINI_API_KEY")
    if telegram_bot_token or os.getenv("TELEGRAM_BOT_TOKEN"):
        CONFIG["telegram_bot_token"] = telegram_bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
    if telegram_channel_id or os.getenv("TELEGRAM_CHANNEL_ID"):
        CONFIG["telegram_channel_id"] = telegram_channel_id or os.getenv("TELEGRAM_CHANNEL_ID")
    if s3_access_key or os.getenv("S3_ACCESS_KEY"):
        CONFIG["s3_access_key"] = s3_access_key or os.getenv("S3_ACCESS_KEY")
    if s3_secret_key or os.getenv("S3_SECRET_KEY"):
        CONFIG["s3_secret_key"] = s3_secret_key or os.getenv("S3_SECRET_KEY")

    _CONFIG_LOADED = True
    logger.info("Configuration loaded successfully")
    return CONFIG


def get_config() -> dict:
    if not _CONFIG_LOADED:
        raise RuntimeError("Configuration has not been loaded. Call load_config() first.")
    return CONFIG
