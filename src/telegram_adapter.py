#!/usr/bin/env python3
"""
Telegram Adapter Module

This module handles sending messages to Telegram channels.
"""

import json
import logging
import asyncio
from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


def send_message(message: str, config_path: str = "config.json") -> None:
    """
    Send a message to Telegram channel.

    This function reads the Telegram credentials from config and sends the message.

    Args:
        message: The message text to send (can include HTML formatting)
        config_path: Path to the configuration file with Telegram credentials (default: "config.json")
    """
    # Read configuration for Telegram credentials
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    bot_token = config.get('telegram_bot_token', '')
    channel_id = config.get('telegram_channel_id', '')

    if not bot_token or not channel_id:
        logger.error("Telegram bot token or channel ID not found in config")
        return

    async def send_message_async():
        bot = Bot(token=bot_token)
        async with bot:
            await bot.send_message(chat_id=channel_id, text=message, parse_mode='HTML')

    try:
        asyncio.run(send_message_async())
        logger.info("Successfully published digest to Telegram")

    except TelegramError as e:
        logger.error(f"Telegram API error: {e}")
    except Exception as e:
        logger.error(f"Error publishing to Telegram: {e}")
