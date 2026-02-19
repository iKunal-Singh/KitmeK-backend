"""Custom exception classes for KitmeK Lesson Generation API.

All domain-level errors should be raised as one of these typed exceptions so
that FastAPI exception handlers can convert them to structured HTTP responses.
"""


class KBLoadError(Exception):
    """Raised when knowledge base files cannot be loaded or parsed.

    Args:
        message: Human-readable description of the failure.
        missing_files: List of filenames that could not be found.
    """

    def __init__(self, message: str, missing_files: list[str] | None = None) -> None:
        super().__init__(message)
        self.missing_files: list[str] = missing_files or []


class TopicNotFoundError(Exception):
    """Raised when a requested topic does not exist in the database.

    Args:
        topic_id: The integer primary key that was not found.
    """

    def __init__(self, topic_id: int) -> None:
        super().__init__(f"Topic with id={topic_id} not found")
        self.topic_id: int = topic_id


class LessonGenerationError(Exception):
    """Raised when lesson generation via Claude API fails after all retries.

    Args:
        message: Description of the failure (last exception message).
        attempt: The retry attempt number on which generation ultimately failed.
    """

    def __init__(self, message: str, attempt: int = 1) -> None:
        super().__init__(message)
        self.attempt: int = attempt


class ValidationError(Exception):
    """Raised when a generated lesson fails KB validation checks.

    Args:
        message: Summary of which checks failed.
        validation_report: The full structured report from the validation pipeline.
    """

    def __init__(self, message: str, validation_report: dict | None = None) -> None:
        super().__init__(message)
        self.validation_report: dict = validation_report or {}


class DatabaseConnectionError(Exception):
    """Raised when a connection to PostgreSQL cannot be established.

    Args:
        message: Detail from the underlying driver exception.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
