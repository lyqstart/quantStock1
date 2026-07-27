TASK_TRANSITIONS: dict[str, set[str]] = {
    "PENDING": {"RUNNING", "CANCELLED"},
    "RUNNING": {"SUCCEEDED", "PARTIAL", "FAILED", "PAUSED", "CANCELLED", "WAITING_SOURCE", "WAITING_DEPENDENCY", "CAPACITY_BLOCKED"},
    "WAITING_SOURCE": {"PENDING", "FAILED", "CANCELLED"},
    "WAITING_DEPENDENCY": {"PENDING", "FAILED", "CANCELLED"},
    "CAPACITY_BLOCKED": {"PENDING", "CANCELLED"},
    "PAUSED": {"PENDING", "CANCELLED"},
    "PARTIAL": {"PENDING", "FAILED", "CANCELLED"},
    "SUCCEEDED": set(),
    "FAILED": set(),
    "CANCELLED": set(),
}

SLICE_TRANSITIONS: dict[str, set[str]] = {
    "PENDING": {"RUNNING", "CANCELLED"},
    "RUNNING": {"SUCCEEDED", "FAILED", "RETRY_WAIT", "SPLIT", "CANCELLED", "LOST"},
    "RETRY_WAIT": {"PENDING", "CANCELLED"},
    "LOST": {"PENDING", "CANCELLED"},
    "SUCCEEDED": set(),
    "FAILED": set(),
    "SPLIT": set(),
    "CANCELLED": set(),
}


def ensure_transition(current: str, target: str, transitions: dict[str, set[str]]) -> None:
    if target not in transitions.get(current, set()):
        raise ValueError(f"illegal state transition: {current} -> {target}")
