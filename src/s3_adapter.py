#!/usr/bin/env python3
"""
S3 Adapter Module

This module handles reading and writing JSON files to S3-compatible storage.
Uses Yandex Cloud Storage with hardcoded endpoint and bucket.
"""

import json
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Hardcoded S3 configuration
S3_ENDPOINT = "https://storage.yandexcloud.net"
S3_BUCKET = "cro-news"

# Cached S3 credentials
_cached_access_key = None
_cached_secret_key = None
_credentials_loaded = False


def _load_s3_credentials(config_path: str = "config.json") -> None:
    global _cached_access_key, _cached_secret_key, _credentials_loaded

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        _cached_access_key = config.get('s3_access_key', '')
        _cached_secret_key = config.get('s3_secret_key', '')
        _credentials_loaded = True

    except Exception as e:
        logger.error(f"Error loading S3 credentials: {e}")
        _cached_access_key = ''
        _cached_secret_key = ''
        _credentials_loaded = True


def is_s3_enabled(config_path: str = "config.json") -> bool:
    global _credentials_loaded

    if not _credentials_loaded:
        _load_s3_credentials(config_path)

    return bool(_cached_access_key and _cached_secret_key)


def read_from_s3(s3_key: str, config_path: str = "config.json") -> dict:
    logger.info(f"Reading from S3: {s3_key}")

    # Ensure credentials are loaded
    if not _credentials_loaded:
        _load_s3_credentials(config_path)

    try:
        s3_client = boto3.client(
            's3',
            endpoint_url=S3_ENDPOINT,
            aws_access_key_id=_cached_access_key,
            aws_secret_access_key=_cached_secret_key
        )

        response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        content = response['Body'].read().decode('utf-8')
        data = json.loads(content)

        logger.info(f"Successfully read from S3: {s3_key}")
        return data

    except ClientError as e:
        logger.error(f"S3 client error reading {s3_key}: {e}")
        raise
    except Exception as e:
        logger.error(f"Error reading from S3 {s3_key}: {e}")
        raise


def write_to_s3(data: dict, s3_key: str, config_path: str = "config.json") -> None:
    logger.info(f"Writing to S3: {s3_key}")

    # Ensure credentials are loaded
    if not _credentials_loaded:
        _load_s3_credentials(config_path)

    try:
        s3_client = boto3.client(
            's3',
            endpoint_url=S3_ENDPOINT,
            aws_access_key_id=_cached_access_key,
            aws_secret_access_key=_cached_secret_key
        )

        content = json.dumps(data, ensure_ascii=False, indent=2)
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=content.encode('utf-8'),
            ContentType='application/json'
        )

        logger.info(f"Successfully wrote to S3: {s3_key}")

    except ClientError as e:
        logger.error(f"S3 client error writing {s3_key}: {e}")
        raise
    except Exception as e:
        logger.error(f"Error writing to S3 {s3_key}: {e}")
        raise
