#!/usr/bin/env python3
"""
AI Adapter Module

This module provides a unified interface for interacting with multiple AI providers
including Google Gemini and OpenRouter (which supports various models like NVIDIA Nemotron).
"""

import json
import logging
import random
import time
from typing import Optional
import requests
from google import genai
from src.config import get_config

logger = logging.getLogger(__name__)

# Retriable HTTP status codes
_RETRIABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}
_RETRIABLE_ERROR_KEYWORDS = frozenset(["rate limit", "timeout", "network", "temporary", "try again"])

_MAX_RETRIES = 5
_DELAY_BASE = 20.0

# OpenRouter API endpoint
_OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


def get_ai_response(
    prompt: str,
    json_schema: Optional[dict] = None
) -> str:
    """
    Generate a response from an AI provider based on the given prompt.

    The provider is automatically detected based on the model configuration:
    - Models starting with "nvidia/", "anthropic/", "openai/", etc. use OpenRouter
    - Other models use Google Gemini

    Args:
        prompt:      The text prompt to send to the AI.
        json_schema: Optional JSON schema for structured output.
                     When provided, the response will conform to this schema.

    Returns:
        The AI's response as a string (JSON string when json_schema is provided).

    Raises:
        ValueError:  If the API key is missing, empty, or rejected by the API.
        RuntimeError: If all retry attempts are exhausted.
        Exception:   For non-retriable API errors.
    """
    config_dict = get_config()
    model_name = config_dict.get('ai_model', 'gemini-2.0-flash-exp')
    api_key = config_dict.get('ai_api_key', '')
    
    if not api_key:
        raise ValueError("ai_api_key is missing or empty in config")
    
    # Detect provider based on model name
    if _is_gemini_model(model_name):
        return _get_gemini_response(prompt, json_schema, model_name, api_key)
    else:
        return _get_openrouter_response(prompt, json_schema, model_name, api_key)


def _is_gemini_model(model_name: str) -> bool:
    """Check if the model name indicates a Google Gemini provider."""
    return model_name.startswith("gemini-")


def _get_gemini_response(
    prompt: str,
    json_schema: Optional[dict],
    model_name: str,
    api_key: str
) -> str:
    """Get response from Google Gemini API with retry logic."""
    client = genai.Client(api_key=api_key)
    config = _build_gemini_config(json_schema)

    last_exception: Optional[Exception] = None
    for attempt in range(_MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
            
            # Log token usage if available
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                input_tokens = response.usage_metadata.prompt_token_count or 0
                output_tokens = response.usage_metadata.candidates_token_count or 0
                total_tokens = response.usage_metadata.total_token_count or 0
                logger.info(
                    "Token usage - Input: %d, Output: %d, Total: %d",
                    input_tokens, output_tokens, total_tokens
                )
            
            return response.text

        except Exception as exc:
            last_exception = exc
            _raise_if_auth_error(exc)

            if not _is_retriable(exc):
                raise

            if attempt < _MAX_RETRIES - 1:
                delay = _backoff_delay(_DELAY_BASE, attempt)
                logger.warning(
                    "Retriable error on attempt %d/%d, retrying in %.1fs: %s",
                    attempt + 1, _MAX_RETRIES, delay, exc,
                )
                time.sleep(delay)
            else:
                logger.error("All %d retry attempts exhausted.", _MAX_RETRIES)

    raise RuntimeError(
        f"Gemini API unavailable after {_MAX_RETRIES} attempts"
    ) from last_exception


def _get_openrouter_response(
    prompt: str,
    json_schema: Optional[dict],
    model_name: str,
    api_key: str
) -> str:
    """Get response from OpenRouter API with retry logic."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    data = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
    }
    
    # Add JSON schema if provided (via response_format)
    if json_schema:
        data["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "response", "strict": True, "schema": json_schema}
        }

    last_exception: Optional[Exception] = None
    for attempt in range(_MAX_RETRIES):
        try:
            response = requests.post(
                url=_OPENROUTER_API_URL,
                headers=headers,
                data=json.dumps(data),
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Log token usage if available
            usage = result.get('usage', {})
            if usage:
                input_tokens = usage.get('prompt_tokens', 0)
                output_tokens = usage.get('completion_tokens', 0)
                total_tokens = usage.get('total_tokens', input_tokens + output_tokens)
                logger.info(
                    "Token usage - Input: %d, Output: %d, Total: %d",
                    input_tokens, output_tokens, total_tokens
                )
            
            return result['choices'][0]['message']['content']

        except requests.exceptions.RequestException as exc:
            last_exception = exc
            _raise_if_auth_error_openrouter(exc)

            if not _is_retriable_openrouter(exc):
                raise

            if attempt < _MAX_RETRIES - 1:
                delay = _backoff_delay(_DELAY_BASE, attempt)
                logger.warning(
                    "Retriable error on attempt %d/%d, retrying in %.1fs: %s",
                    attempt + 1, _MAX_RETRIES, delay, exc,
                )
                time.sleep(delay)
            else:
                logger.error("All %d retry attempts exhausted.", _MAX_RETRIES)

    raise RuntimeError(
        f"OpenRouter API unavailable after {_MAX_RETRIES} attempts"
    ) from last_exception


# ── Helpers ──────────────────────────────────────────────────────────────────

def _build_gemini_config(json_schema: Optional[dict]) -> dict:
    """Build the generation config for Gemini, injecting the schema when provided."""
    if not json_schema:
        return {}
    return {
        "response_mime_type": "application/json",
        "response_schema": json_schema,
    }


def _is_retriable(exc: Exception) -> bool:
    """Return True if the exception represents a transient, retriable failure (Gemini)."""
    if hasattr(exc, "response") and hasattr(exc.response, "status_code"):
        return exc.response.status_code in _RETRIABLE_STATUS_CODES
    error_str = str(exc).lower()
    return any(kw in error_str for kw in _RETRIABLE_ERROR_KEYWORDS)


def _is_retriable_openrouter(exc: Exception) -> bool:
    """Return True if the exception represents a transient, retriable failure (OpenRouter)."""
    if isinstance(exc, requests.exceptions.RequestException):
        if hasattr(exc, "response") and exc.response is not None:
            return exc.response.status_code in _RETRIABLE_STATUS_CODES
    error_str = str(exc).lower()
    return any(kw in error_str for kw in _RETRIABLE_ERROR_KEYWORDS)


def _raise_if_auth_error(exc: Exception) -> None:
    """Re-raise authentication errors immediately as ValueError (Gemini)."""
    is_401 = (
        hasattr(exc, "response")
        and hasattr(exc.response, "status_code")
        and exc.response.status_code == 401
    )
    if is_401 or "api key" in str(exc).lower():
        raise ValueError(f"Invalid API key: {exc}") from exc


def _raise_if_auth_error_openrouter(exc: Exception) -> None:
    """Re-raise authentication errors immediately as ValueError (OpenRouter)."""
    if isinstance(exc, requests.exceptions.RequestException):
        if hasattr(exc, "response") and exc.response is not None:
            if exc.response.status_code == 401:
                raise ValueError(f"Invalid OpenRouter API key: {exc}") from exc
    if "api key" in str(exc).lower() or "unauthorized" in str(exc).lower():
        raise ValueError(f"Invalid OpenRouter API key: {exc}") from exc


def _backoff_delay(base: float, attempt: int) -> float:
    """Exponential backoff with full jitter to avoid thundering herd."""
    ceiling = base * (2 ** attempt)
    return random.uniform(ceiling/2, ceiling)
