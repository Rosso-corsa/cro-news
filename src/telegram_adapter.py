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
from src.config import get_config

logger = logging.getLogger(__name__)


def send_message(message: str) -> None:
    """
    Send a message to Telegram channel.

    This function reads the Telegram credentials from global config and sends the message.
    If the message exceeds Telegram's 4096 character limit, it will be split into
    multiple messages at topic boundaries (empty lines).

    Args:
        message: The message text to send (can include HTML formatting)
    """
    # Read configuration for Telegram credentials
    config = get_config()
    bot_token = config.get('telegram_bot_token', '')
    channel_id = config.get('telegram_channel_id', '')

    if not bot_token or not channel_id:
        logger.error("Telegram bot token or channel ID not found in config")
        return

    # Split message if it exceeds Telegram's limit
    TELEGRAM_MESSAGE_LIMIT = 4096
    messages_to_send = []

    if len(message) <= TELEGRAM_MESSAGE_LIMIT:
        messages_to_send.append(message)
    else:
        # Split at topic boundaries (double newlines) to keep topics intact
        topics = message.split('\n\n')
        current_message = ""
        
        for topic in topics:
            # Check if adding this topic would exceed the limit
            if len(current_message) + len(topic) + 2 <= TELEGRAM_MESSAGE_LIMIT:
                if current_message:
                    current_message += "\n\n" + topic
                else:
                    current_message = topic
            else:
                if current_message:
                    messages_to_send.append(current_message)
                current_message = topic
        
        if current_message:
            messages_to_send.append(current_message)
        
        logger.info(f"Message split into {len(messages_to_send)} parts due to size limit")

    async def send_message_async():
        bot = Bot(token=bot_token)
        async with bot:
            for idx, msg in enumerate(messages_to_send, 1):
                await bot.send_message(chat_id=channel_id, text=msg, parse_mode='HTML')
                logger.info(f"Sent message part {idx}/{len(messages_to_send)}")

    try:
        asyncio.run(send_message_async())
        logger.info("Successfully published digest to Telegram")

    except TelegramError as e:
        logger.error(f"Telegram API error: {e}")
    except Exception as e:
        logger.error(f"Error publishing to Telegram: {e}")
