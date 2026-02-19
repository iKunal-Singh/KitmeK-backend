"""Top-level pytest configuration and shared fixtures for KitmeK test suite.

Environment variables are set at the top of this module *before* any src
imports so that ``src.database._build_engine()`` does not raise at import
time during testing.

Fixture hierarchy
-----------------
mock_kb_loader   → MockKBLoader with hardcoded Grade 3 (+ multi-grade) data
mock_db_session  → Async mock of SQLAlchemy AsyncSession
sample_topic     → Mock Topic ORM object (Grade 3, EVS, Types of Plants)
test_client      → FastAPI TestClient with DB + KB dependencies overridden
"""

from __future__ import annotations

import os

# ---------------------------------------------------------------------------
# Set environment variables BEFORE any src imports so the database module
# (which calls create_async_engine at import time) does not raise RuntimeError.
# ---------------------------------------------------------------------------
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://kitmeK:dev_password@localhost:5432/lesson_generation",
)
os.environ.setdefault("ANTHROPIC_API_KEY", "test_key_not_real")
os.environ.setdefault("KB_PATH", "/home/kunal/projects/kitmeK-lesson-backend/kb_files")

from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.fixtures.mock_kb_files import MockKBLoader
from tests.fixtures.sample_lessons import VALID_GRADE3_LESSON


# ---------------------------------------------------------------------------
# KB Loader fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_kb_loader() -> MockKBLoader:
    """Provide a MockKBLoader with hardcoded Grade 3 KB data.

    Returns a ``MockKBLoader`` instance whose methods return values sourced
    directly from the KB Markdown files.  Tests should use this instead of
    hitting the real filesystem or database.
    """
    return MockKBLoader()


# ---------------------------------------------------------------------------
# Async DB session mock
# ---------------------------------------------------------------------------


@pytest.fixture
async def mock_db_session() -> AsyncGenerator[AsyncMock, None]:
    """Provide an async mock of SQLAlchemy ``AsyncSession``.

    Yields an ``AsyncMock`` with all common session methods (execute, commit,
    rollback, close, add, flush) pre-configured.  The mock does not interact
    with any database.
    """
    session = AsyncMock()
    session.execute = AsyncMock(return_value=MagicMock())
    session.commit = AsyncMock(return_value=None)
    session.rollback = AsyncMock(return_value=None)
    session.close = AsyncMock(return_value=None)
    session.add = MagicMock(return_value=None)
    session.flush = AsyncMock(return_value=None)
    session.refresh = AsyncMock(return_value=None)
    session.scalar = AsyncMock(return_value=None)
    session.scalars = AsyncMock(return_value=MagicMock())
    # Support async context-manager usage: ``async with session`` (__aenter__/__aexit__)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    yield session


# ---------------------------------------------------------------------------
# Sample Topic ORM mock
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_topic() -> MagicMock:
    """Provide a mock Topic ORM object representing Grade 3, EVS, Types of Plants.

    The fixture mirrors the Topic model defined in ``src/models/topic.py`` and
    the curriculum row from Appendix B of the architecture document:
        grade=3, subject=EVS, chapter="Types of Plants", topic="Trees vs Shrubs"

    Returns:
        A ``MagicMock`` with all Topic fields populated with realistic values.
    """
    topic = MagicMock()
    topic.id = 42
    topic.topic_number = 1
    topic.topic_name = "Trees vs Shrubs"
    topic.topic_description = "Differences between trees and shrubs based on stem structure."
    topic.sequence_number = 1
    # JSON strings as stored in the DB column (see Topic ORM model)
    topic.prerequisites = "[]"
    topic.exclusions = '["climbers", "creepers"]'
    topic.context_narrative = (
        "Meera and her grandfather were walking in the park when they spotted "
        "a tall mango tree next to a short rose bush."
    )
    topic.chapter_id = 10
    # Related chapter mock
    topic.chapter = MagicMock()
    topic.chapter.id = 10
    topic.chapter.chapter_name = "Types of Plants"
    topic.chapter.chapter_number = 1
    # Related grade mock (via chapter → subject → grade chain)
    topic.chapter.subject = MagicMock()
    topic.chapter.subject.grade = MagicMock()
    topic.chapter.subject.grade.grade_code = "3"
    topic.chapter.subject.subject_name = "EVS"
    return topic


# ---------------------------------------------------------------------------
# FastAPI TestClient with overridden dependencies
# ---------------------------------------------------------------------------


@pytest.fixture
def test_client(mock_db_session: AsyncMock, mock_kb_loader: MockKBLoader):
    """Provide a FastAPI TestClient with DB and KB dependencies overridden.

    The ``get_async_db`` FastAPI dependency is replaced with one that yields
    *mock_db_session*.  If the application exposes a KB loader dependency it
    is replaced with *mock_kb_loader*.  The overrides are cleared after the
    test completes.

    Yields:
        A ``starlette.testclient.TestClient`` bound to the FastAPI app.
    """
    from fastapi.testclient import TestClient

    # Patch the database engine creation so importing src.database doesn't
    # attempt a real DB connection during TestClient startup.
    with patch("sqlalchemy.ext.asyncio.create_async_engine") as _mock_engine:
        _mock_engine.return_value = MagicMock()

        from src.main import app
        from src.database import get_async_db

        async def _override_get_db() -> AsyncGenerator[AsyncMock, None]:
            """Dependency override that yields the mock DB session."""
            yield mock_db_session

        app.dependency_overrides[get_async_db] = _override_get_db

        # Override KB loader dependency from src.api.dependencies
        from src.api.dependencies import get_kb_loader
        app.dependency_overrides[get_kb_loader] = lambda: mock_kb_loader

        with TestClient(app) as client:
            yield client

        app.dependency_overrides.clear()
