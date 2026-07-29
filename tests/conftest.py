"""Shared pytest fixtures for the quantStock1 test suite.

Tests that need a database connect to the server-test PostgreSQL/TimescaleDB
instance (compose.test.yml).  The DSN is read from the environment variable
``QUANTSTOCK1_TEST_DATABASE_URL`` falling back to a local default.

All DB-dependent tests are marked ``@pytest.mark.integration`` so they can be
skipped with ``-m "not integration"`` when no PG is available.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

TEST_DSN = os.environ.get(
    "QUANTSTOCK1_TEST_DATABASE_URL",
    "postgresql+psycopg://quantstock1_test:change_me@localhost:15432/quantstock1_test",
)


def _pg_available() -> bool:
    try:
        engine = create_engine(TEST_DSN)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


PG_AVAILABLE = _pg_available()
skip_no_pg = pytest.mark.skipif(not PG_AVAILABLE, reason="PostgreSQL not available")


@pytest.fixture(scope="session")
def db_engine():
    """Session-scoped engine connected to the test PG."""
    if not PG_AVAILABLE:
        pytest.skip("PostgreSQL not available")
    engine = create_engine(TEST_DSN, future=True)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def db_session_factory(db_engine) -> sessionmaker:
    return sessionmaker(bind=db_engine, future=True)


@pytest.fixture
def db_session(db_session_factory) -> Generator[Session, None, None]:
    """Function-scoped session that rolls back after each test."""
    session = db_session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def trace_id() -> uuid.UUID:
    return uuid.uuid4()
