import hashlib

from sqlalchemy import text
from sqlalchemy.orm import Session


def advisory_lock_key(environment: str) -> int:
    digest = hashlib.sha256(f"quantstock1:scheduler:{environment}".encode()).digest()
    value = int.from_bytes(digest[:8], byteorder="big", signed=False)
    return value & 0x7FFF_FFFF_FFFF_FFFF


def try_acquire_scheduler_lock(session: Session, environment: str) -> bool:
    key = advisory_lock_key(environment)
    return bool(session.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": key}))


def release_scheduler_lock(session: Session, environment: str) -> bool:
    key = advisory_lock_key(environment)
    return bool(session.scalar(text("SELECT pg_advisory_unlock(:key)"), {"key": key}))
