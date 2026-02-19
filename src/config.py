"""Application configuration using Pydantic BaseSettings.

Loads settings from environment variables with sensible defaults for
local development. All production values must be set via environment
or a .env file.
"""

from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://kitmeK:password@localhost:5432/lesson_generation",
        description="PostgreSQL async connection URL (must use asyncpg driver)",
    )

    # Anthropic
    anthropic_api_key: str = Field(
        default="",
        description="Anthropic API key for Claude lesson generation",
    )

    # Knowledge Base
    kb_path: str = Field(
        default="kb_files",
        description="Filesystem path to the directory containing KB markdown files",
    )

    kb_required_files: List[str] = Field(
        default=[
            "language_guidelines.md",
            "NCERT_Pedagogical_Style_Knowledge.md",
            "digital_interactions.md",
            "question_bank.md",
        ],
        description="KB files that MUST exist at startup; missing files raise KBLoadError",
    )

    kb_expected_files: List[str] = Field(
        default=[
            "language_guidelines.md",
            "NCERT_Pedagogical_Style_Knowledge.md",
            "digital_interactions.md",
            "question_bank.md",
            "definitions_and_examples.md",
            "KB_MASTER_GUIDE.md",
        ],
        description=(
            "Full set of expected KB files — the 4 required files plus 2 optional "
            "files (definitions_and_examples.md, KB_MASTER_GUIDE.md). "
            "Optional files are loaded when present; absence is logged as a warning."
        ),
    )

    # Runtime
    log_level: str = Field(default="INFO", description="Python logging level")
    debug: bool = Field(default=False, description="Enable FastAPI debug mode")
    app_version: str = Field(default="1.0.0", description="Application version string")


_settings_instance: Settings | None = None


def get_settings() -> Settings:
    """Return a cached singleton Settings instance.

    Returns:
        The application settings, loaded from environment on first call.
    """
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance
