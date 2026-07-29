"""Tests for task/slice state machine terminal-state irreversibility (DD-CORE-002/003)."""

import pytest

from app.collect.state_machine import (
    SLICE_TRANSITIONS,
    TASK_TRANSITIONS,
    ensure_transition,
)

TERMINAL_TASK_STATES = {"SUCCEEDED", "CANCELLED"}
TERMINAL_SLICE_STATES = {"SUCCEEDED", "CANCELLED", "SPLIT"}


class TestTaskStateMachine:
    def test_pending_to_running_allowed(self):
        ensure_transition("PENDING", "RUNNING", TASK_TRANSITIONS)

    def test_running_to_succeeded_allowed(self):
        ensure_transition("RUNNING", "SUCCEEDED", TASK_TRANSITIONS)

    @pytest.mark.parametrize("terminal", sorted(TERMINAL_TASK_STATES))
    def test_terminal_state_cannot_revert(self, terminal):
        with pytest.raises(ValueError, match="illegal state transition"):
            ensure_transition(terminal, "RUNNING", TASK_TRANSITIONS)

    @pytest.mark.parametrize("terminal", sorted(TERMINAL_TASK_STATES))
    def test_terminal_to_any_disallowed(self, terminal):
        for target in ("PENDING", "RUNNING", "FAILED"):
            with pytest.raises(ValueError):
                ensure_transition(terminal, target, TASK_TRANSITIONS)

    def test_failed_can_retry(self):
        ensure_transition("FAILED", "PENDING", TASK_TRANSITIONS)


class TestSliceStateMachine:
    def test_pending_to_running_allowed(self):
        ensure_transition("PENDING", "RUNNING", SLICE_TRANSITIONS)

    @pytest.mark.parametrize("terminal", sorted(TERMINAL_SLICE_STATES))
    def test_terminal_state_cannot_revert(self, terminal):
        with pytest.raises(ValueError):
            ensure_transition(terminal, "RUNNING", SLICE_TRANSITIONS)

    def test_lost_can_requeue(self):
        ensure_transition("LOST", "PENDING", SLICE_TRANSITIONS)
