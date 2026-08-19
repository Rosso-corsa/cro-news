#!/usr/bin/env python3
"""Unit tests for AI model selection and fallback behavior."""

import logging
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src import ai_adapter


@pytest.fixture(autouse=True)
def reset_backup_state():
    ai_adapter._BACKUP_MODEL_ACTIVE = False
    yield
    ai_adapter._BACKUP_MODEL_ACTIVE = False


def _config(backup_model="backup-model"):
    return {
        "ai_api_key": "test-key",
        "ai_model": "primary-model",
        "ai_backup_model": backup_model,
    }


def _exhausted_failure(status_code):
    provider_error = RuntimeError(f"{status_code} provider failure")
    provider_error.response = SimpleNamespace(status_code=status_code)
    exhausted_error = RuntimeError("provider unavailable")
    exhausted_error.__cause__ = provider_error
    return exhausted_error


def test_primary_success_does_not_activate_backup():
    with patch.object(ai_adapter, "get_config", return_value=_config()), patch.object(
        ai_adapter, "_invoke_model", return_value="primary response"
    ) as invoke:
        assert ai_adapter.get_ai_response("prompt") == "primary response"

    invoke.assert_called_once_with("prompt", None, "primary-model", "test-key")
    assert ai_adapter._BACKUP_MODEL_ACTIVE is False


@pytest.mark.parametrize("status_code", [429, 503])
def test_exhausted_eligible_failure_switches_to_backup(status_code, caplog):
    failure = _exhausted_failure(status_code)

    with patch.object(ai_adapter, "get_config", return_value=_config()), patch.object(
        ai_adapter,
        "_invoke_model",
        side_effect=[failure, "backup response"],
    ) as invoke, caplog.at_level(logging.WARNING, logger=ai_adapter.__name__):
        assert ai_adapter.get_ai_response("prompt") == "backup response"

    assert ai_adapter._BACKUP_MODEL_ACTIVE is True
    assert "switching to backup model 'backup-model'" in caplog.text
    assert [call.args[2] for call in invoke.call_args_list] == [
        "primary-model",
        "backup-model",
    ]


def test_backup_remains_active_for_later_calls():
    ai_adapter._BACKUP_MODEL_ACTIVE = True

    with patch.object(ai_adapter, "get_config", return_value=_config()), patch.object(
        ai_adapter, "_invoke_model", return_value="backup response"
    ) as invoke:
        assert ai_adapter.get_ai_response("prompt", model="other-primary") == "backup response"

    invoke.assert_called_once_with("prompt", None, "backup-model", "test-key")


def test_non_eligible_failure_does_not_switch():
    failure = _exhausted_failure(500)

    with patch.object(ai_adapter, "get_config", return_value=_config()), patch.object(
        ai_adapter, "_invoke_model", side_effect=failure
    ):
        with pytest.raises(RuntimeError, match="provider unavailable"):
            ai_adapter.get_ai_response("prompt")

    assert ai_adapter._BACKUP_MODEL_ACTIVE is False


def test_missing_or_same_backup_does_not_switch():
    failure = _exhausted_failure(503)

    for backup_model in [None, "primary-model"]:
        with patch.object(ai_adapter, "get_config", return_value=_config(backup_model)), patch.object(
            ai_adapter, "_invoke_model", side_effect=failure
        ):
            with pytest.raises(RuntimeError):
                ai_adapter.get_ai_response("prompt")
        assert ai_adapter._BACKUP_MODEL_ACTIVE is False