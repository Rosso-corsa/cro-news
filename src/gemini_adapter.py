#!/usr/bin/env python3
"""
Gemini AI adapter module for interacting with Google's Gemini API.
"""

import json
import logging
import random
import time
from typing import Optional
from google import genai
from src.config import get_config

logger = logging.getLogger(__name__)

# Retriable HTTP status codes
_RETRIABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}
_RETRIABLE_ERROR_KEYWORDS = frozenset(["rate limit", "timeout", "network", "temporary", "try again"])


def get_ai_response(
    prompt: str,
    json_schema: Optional[dict] = None
) -> str:
    """
    Generate a response from Gemini AI based on the given prompt.

    Args:
        prompt:      The text prompt to send to the AI.
        json_schema: Optional JSON schema for structured output.
                     When provided, the response will conform to this schema.
        max_retries: Maximum number of retry attempts for retriable errors.
        base_delay:  Base delay in seconds for exponential backoff.

    Returns:
        The AI's response as a string (JSON string when json_schema is provided).

    Raises:
        ValueError:  If the API key is missing, empty, or rejected by the API.
        RuntimeError: If all retry attempts are exhausted.
        Exception:   For non-retriable API errors.
    """
    config_dict = get_config()
    api_key = config_dict.get('gemini_api_key', '')
    model_name = config_dict.get('gemini_model', 'gemini-3.5-flash')

    if not api_key:
        raise ValueError("gemini_api_key is missing or empty in config")

    client = genai.Client(api_key=api_key)
    config = _build_config(json_schema)

    last_exception: Optional[Exception] = None
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
            return response.text

        except Exception as exc:
            last_exception = exc
            _raise_if_auth_error(exc)

            if not _is_retriable(exc):
                raise

            if attempt < 2:
                delay = _backoff_delay(1.0, attempt)
                logger.warning(
                    "Retriable error on attempt %d/3, retrying in %.1fs: %s",
                    attempt + 1, delay, exc,
                )
                time.sleep(delay)
            else:
                logger.error("All 3 retry attempts exhausted.")

    raise RuntimeError(
        "Gemini API unavailable after 3 attempts"
    ) from last_exception


# ── Helpers ──────────────────────────────────────────────────────────────────

def _build_config(json_schema: Optional[dict]) -> dict:
    """Build the generation config, injecting the schema when provided."""
    if not json_schema:
        return {}
    return {
        "response_mime_type": "application/json",
        "response_schema": json_schema,
    }


def _is_retriable(exc: Exception) -> bool:
    """Return True if the exception represents a transient, retriable failure."""
    if hasattr(exc, "response") and hasattr(exc.response, "status_code"):
        return exc.response.status_code in _RETRIABLE_STATUS_CODES
    error_str = str(exc).lower()
    return any(kw in error_str for kw in _RETRIABLE_ERROR_KEYWORDS)


def _raise_if_auth_error(exc: Exception) -> None:
    """Re-raise authentication errors immediately as ValueError."""
    is_401 = (
        hasattr(exc, "response")
        and hasattr(exc.response, "status_code")
        and exc.response.status_code == 401
    )
    if is_401 or "api key" in str(exc).lower():
        raise ValueError(f"Invalid API key: {exc}") from exc


def _backoff_delay(base: float, attempt: int) -> float:
    """Exponential backoff with full jitter to avoid thundering herd."""
    ceiling = base * (2 ** attempt)
    return random.uniform(0, ceiling)
