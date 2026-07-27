import pytest

from app.collect.state_machine import TASK_TRANSITIONS, ensure_transition


def test_valid_transition() -> None:
    ensure_transition("PENDING", "RUNNING", TASK_TRANSITIONS)


def test_failed_cannot_be_rewritten_to_success() -> None:
    with pytest.raises(ValueError):
        ensure_transition("FAILED", "SUCCEEDED", TASK_TRANSITIONS)
