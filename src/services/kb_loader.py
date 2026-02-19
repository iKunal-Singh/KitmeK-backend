"""Knowledge Base loader and parser for KitmeK lesson generation.

Reads all Markdown files from the configured ``kb_path``, parses structured
data (language constraints, interaction types, Bloom's distributions) using
only stdlib ``re``, and caches results in memory after the first load.

Usage::

    from src.services.kb_loader import KBLoader

    loader = KBLoader()
    loader.load()                            # raises KBLoadError if required files missing
    ceiling = loader.get_language_ceiling("3")
    dist = loader.get_bloom_distribution("3")
    interactions = loader.get_allowed_interactions("3")
"""

import hashlib
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.config import get_settings
from src.exceptions import KBLoadError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------


@dataclass
class LanguageCeiling:
    """Language complexity constraints for a specific grade.

    Attributes:
        grade: Grade code, e.g. ``"3"``.
        max_sentence_length: Upper bound on words per sentence.
        max_new_vocab: Maximum new vocabulary items per lesson.
        allowed_connectors: Conjunction words allowed in sentences.
        can_use_because: Whether ``"because"`` clauses are allowed.
    """

    grade: str
    max_sentence_length: int
    max_new_vocab: int
    allowed_connectors: list[str] = field(default_factory=list)
    can_use_because: bool = False


@dataclass
class KBData:
    """Container for all parsed knowledge base data.

    Attributes:
        version: KB version string (currently always ``"1.0"``).
        checksum: SHA-256 hex digest of all loaded file contents.
        files_loaded: Sorted list of filenames successfully loaded.
        raw_content: Mapping of filename → raw UTF-8 markdown text.
        language_ceilings: Grade → ``LanguageCeiling`` mapping.
        bloom_distributions: Grade → ``{"L1": n, "L2": n, ...}`` mapping.
        allowed_interactions: Grade → list of interaction type names.
    """

    version: str
    checksum: str
    files_loaded: list[str]
    raw_content: dict[str, str]
    language_ceilings: dict[str, LanguageCeiling]
    bloom_distributions: dict[str, dict[str, int]]
    allowed_interactions: dict[str, list[str]]


# ---------------------------------------------------------------------------
# Main loader class
# ---------------------------------------------------------------------------


class KBLoader:
    """Load, parse, and cache knowledge base files from disk.

    The loader is intentionally side-effect-free at construction time —
    no files are read until :meth:`load` is called explicitly (or
    implicitly via any ``get_*`` method).

    Args:
        kb_path: Directory containing the ``.md`` KB files.
                 Defaults to ``Settings.kb_path``.
    """

    def __init__(self, kb_path: str | None = None) -> None:
        settings = get_settings()
        self.kb_path: Path = Path(kb_path or settings.kb_path)
        self._cache: KBData | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> KBData:
        """Load and parse all KB files, caching results in memory.

        Returns:
            Fully parsed :class:`KBData` object.

        Raises:
            KBLoadError: If required files are missing from ``kb_path``.
        """
        if self._cache is not None:
            return self._cache

        settings = get_settings()
        self._validate_required_files(settings.kb_required_files)

        raw_content = self._read_files(settings.kb_expected_files)
        checksum = self._compute_checksum(raw_content)

        language_ceilings = self._parse_language_guidelines(
            raw_content.get("language_guidelines.md", "")
        )
        bloom_distributions = self._parse_bloom_distributions(
            raw_content.get("NCERT_Pedagogical_Style_Knowledge.md", "")
        )
        allowed_interactions = self._parse_allowed_interactions(
            raw_content.get("digital_interactions.md", "")
        )

        self._cache = KBData(
            version="1.0",
            checksum=checksum,
            files_loaded=sorted(raw_content.keys()),
            raw_content=raw_content,
            language_ceilings=language_ceilings,
            bloom_distributions=bloom_distributions,
            allowed_interactions=allowed_interactions,
        )
        logger.info(
            "KB loaded: %d files, checksum=%s",
            len(raw_content),
            checksum[:16],
        )
        return self._cache

    def reload(self) -> KBData:
        """Invalidate the in-memory cache and reload all KB files from disk.

        Returns:
            Freshly parsed :class:`KBData`.

        Raises:
            KBLoadError: If required files are missing.
        """
        self._cache = None
        return self.load()

    def get_language_ceiling(self, grade: str) -> LanguageCeiling:
        """Return the language complexity ceiling for a grade.

        Args:
            grade: Grade code (``K``, ``1``, ``2``, ``3``, ``4``, ``5``).

        Returns:
            :class:`LanguageCeiling` for the requested grade.
        """
        kb = self.load()
        if grade not in kb.language_ceilings:
            logger.warning(
                "Grade %r not in language_ceilings; using Grade 5 ceiling", grade
            )
            grade = "5"
        return kb.language_ceilings[grade]

    def get_bloom_distribution(self, grade: str) -> dict[str, int]:
        """Return the required Bloom's taxonomy distribution for a grade's quiz.

        Args:
            grade: Grade code.

        Returns:
            dict mapping Bloom's level (``"L1"``–``"L5"``) to question count.
        """
        kb = self.load()
        if grade not in kb.bloom_distributions:
            logger.warning("Grade %r not in bloom_distributions; using Grade 3", grade)
            grade = "3"
        return dict(kb.bloom_distributions[grade])

    def get_allowed_interactions(self, grade: str) -> list[str]:
        """Return the allowed interaction type names for a grade.

        Args:
            grade: Grade code.

        Returns:
            List of canonical interaction type names (from the enum in
            ``digital_interactions.md``).
        """
        kb = self.load()
        if grade not in kb.allowed_interactions:
            logger.warning(
                "Grade %r not in allowed_interactions; using Grade 5 set", grade
            )
            grade = "5"
        return list(kb.allowed_interactions[grade])

    def get_definition(self, concept: str, grade: str) -> str | None:
        """Return the authoritative KB definition for a concept, if available.

        Args:
            concept: The concept or term to look up.
            grade: Grade context (currently unused; reserved for future filtering).

        Returns:
            Raw markdown snippet for the concept heading, or ``None`` if not found.
        """
        kb = self.load()
        content = kb.raw_content.get("definitions_and_examples.md", "")
        if not content:
            return None
        pattern = rf"(?im)^#{{1,3}}\s+{re.escape(concept)}\b"
        match = re.search(pattern, content)
        if not match:
            return None
        start = match.end()
        next_heading = re.search(r"\n#{1,3}\s+", content[start:])
        snippet = (
            content[start : start + next_heading.start()]
            if next_heading
            else content[start:]
        )
        return snippet.strip() or None

    def get_full_content(self, filename: str) -> str:
        """Return the raw markdown content of a specific KB file.

        Args:
            filename: Filename relative to ``kb_path``, e.g. ``"language_guidelines.md"``.

        Returns:
            Full UTF-8 markdown text, or an empty string if not loaded.
        """
        kb = self.load()
        return kb.raw_content.get(filename, "")

    def get_kb_version(self) -> dict[str, Any]:
        """Return version metadata for the currently loaded KB.

        Returns:
            dict with keys ``kb_version``, ``checksum``, and ``files_loaded``.
            If not yet loaded, ``kb_version`` is ``"not_loaded"``.
        """
        if self._cache is None:
            return {"kb_version": "not_loaded", "checksum": "", "files_loaded": []}
        return {
            "kb_version": self._cache.version,
            "checksum": self._cache.checksum,
            "files_loaded": self._cache.files_loaded,
        }

    def is_loaded(self) -> bool:
        """Return ``True`` if KB data is cached in memory."""
        return self._cache is not None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _validate_required_files(self, required: list[str]) -> None:
        """Raise :exc:`KBLoadError` if any required file is absent."""
        missing = [f for f in required if not (self.kb_path / f).exists()]
        if missing:
            raise KBLoadError(
                f"Required KB files missing from {self.kb_path}: {missing}",
                missing_files=missing,
            )

    def _read_files(self, expected: list[str]) -> dict[str, str]:
        """Read all .md files from kb_path.

        First reads every .md file found by glob; then warns about expected
        files that were not found (optional files).

        Args:
            expected: Full expected filenames list (required + optional).

        Returns:
            Mapping of filename → UTF-8 content for all successfully read files.
        """
        result: dict[str, str] = {}
        for md_file in sorted(self.kb_path.glob("*.md")):
            try:
                result[md_file.name] = md_file.read_text(encoding="utf-8")
                logger.debug(
                    "Loaded KB file: %s (%d bytes)",
                    md_file.name,
                    len(result[md_file.name]),
                )
            except OSError as exc:
                logger.warning("Could not read KB file %s: %s", md_file, exc)

        for fname in expected:
            if fname not in result:
                logger.warning(
                    "Optional KB file not found (will be skipped): %s", fname
                )

        return result

    def _compute_checksum(self, raw_content: dict[str, str]) -> str:
        """Return SHA-256 hex digest of all file contents in sorted name order."""
        h = hashlib.sha256()
        for name in sorted(raw_content.keys()):
            h.update(name.encode("utf-8"))
            h.update(raw_content[name].encode("utf-8"))
        return h.hexdigest()

    # ------------------------------------------------------------------
    # Parsers — stdlib regex only
    # ------------------------------------------------------------------

    def _parse_language_guidelines(self, content: str) -> dict[str, LanguageCeiling]:
        """Parse ``language_guidelines.md`` into per-grade ``LanguageCeiling`` objects.

        Splits the document on level-2 headings of the form ``## Grade <code>``.
        Within each grade section extracts:
        - Upper bound of ``Maximum sentence length: X–Y words``
        - Upper bound of ``New words per lesson: X–Y``
        - Connectors quoted in the text (``"and"``, ``"because"``, etc.)

        Args:
            content: Raw markdown text.

        Returns:
            Mapping of grade code to :class:`LanguageCeiling`.
        """
        ceilings: dict[str, LanguageCeiling] = {}
        if not content:
            return ceilings

        section_re = re.compile(r"^## Grade (\w+)", re.MULTILINE)
        sections = section_re.split(content)
        # sections[0] = preamble; then pairs: grade_code, section_body
        it = iter(sections[1:])
        for grade_code, body in zip(it, it):
            grade_code = grade_code.strip()

            # Maximum sentence length (upper bound of range)
            # Supports both en-dash (–, U+2013) and ASCII hyphen
            sent_match = re.search(
                r"Maximum sentence length:\s*\d+[\u2013\-]\s*(\d+)\s*words",
                body,
                re.IGNORECASE,
            )
            max_sentence = int(sent_match.group(1)) if sent_match else 18

            # New words per lesson (upper bound of range)
            vocab_match = re.search(
                r"New words per lesson:\s*\d+[\u2013\-]\s*(\d+)",
                body,
                re.IGNORECASE,
            )
            max_vocab = int(vocab_match.group(1)) if vocab_match else 10

            # Connectors: find the specific "Allowed connectors:" line to avoid
            # picking up connectors mentioned in negative context (e.g. "no 'because'")
            conn_match = re.search(
                r"Allowed connectors:\s*(.+?)$", body, re.MULTILINE | re.IGNORECASE
            )
            if conn_match:
                conn_line = conn_match.group(1)
                # If the line says "all common conjunctions", expand to full list
                if re.search(r"\ball\b", conn_line, re.IGNORECASE):
                    connectors: list[str] = [
                        "and",
                        "but",
                        "or",
                        "so",
                        "because",
                        "when",
                        "if",
                        "although",
                        "however",
                        "therefore",
                    ]
                else:
                    connectors = re.findall(
                        r'"(and|but|or|so|because|when|if|although),?"',
                        conn_line,
                        re.IGNORECASE,
                    )
            else:
                connectors = []
            connectors = list(dict.fromkeys(c.lower() for c in connectors))

            can_because = "because" in connectors

            ceilings[grade_code] = LanguageCeiling(
                grade=grade_code,
                max_sentence_length=max_sentence,
                max_new_vocab=max_vocab,
                allowed_connectors=connectors,
                can_use_because=can_because,
            )

        return ceilings

    def _parse_bloom_distributions(self, content: str) -> dict[str, dict[str, int]]:
        """Parse the Bloom's distribution table from NCERT_Pedagogical_Style_Knowledge.md.

        Looks for markdown table rows of the form::

            | K | 4 | 4 | 2 | 0 | 0 | 10 |
            | 3 | 2 | 3 | 3 | 1 | 1 | 10 |

        Columns are interpreted as Grade | L1 | L2 | L3 | L4 | L5 | Total.

        Args:
            content: Raw markdown text.

        Returns:
            Mapping of grade code to Bloom's level counts.
        """
        distributions: dict[str, dict[str, int]] = {}
        if not content:
            return distributions

        row_re = re.compile(
            r"\|\s*([K1-5])\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|"
        )
        for match in row_re.finditer(content):
            grade = match.group(1)
            distributions[grade] = {
                "L1": int(match.group(2)),
                "L2": int(match.group(3)),
                "L3": int(match.group(4)),
                "L4": int(match.group(5)),
                "L5": int(match.group(6)),
            }
        return distributions

    def _parse_allowed_interactions(self, content: str) -> dict[str, list[str]]:
        """Parse the allowed interaction types per grade from ``digital_interactions.md``.

        Splits on level-2 headings ``## Grade <code>``, then within each section
        extracts the ``### Allowed Types`` subsection and collects all items from
        lines of the form ``**Category:** Type1, Type2, ...``.

        Args:
            content: Raw markdown text.

        Returns:
            Mapping of grade code to list of allowed interaction type strings.
        """
        interactions: dict[str, list[str]] = {}
        if not content:
            return interactions

        section_re = re.compile(r"^## Grade (\w+)", re.MULTILINE)
        sections = section_re.split(content)

        it = iter(sections[1:])
        for grade_code, body in zip(it, it):
            grade_code = grade_code.strip()

            allowed_start = body.find("### Allowed Types")
            if allowed_start == -1:
                continue

            allowed_body = body[allowed_start:]
            # Trim to just the Allowed Types subsection
            next_sub = re.search(r"\n###", allowed_body[len("### Allowed Types") :])
            if next_sub:
                allowed_body = allowed_body[
                    : len("### Allowed Types") + next_sub.start()
                ]

            # Extract all types from bold-category lines
            types: list[str] = []
            cat_re = re.compile(r"\*\*[^:]+:\*\*\s*(.+)")
            for cat_match in cat_re.finditer(allowed_body):
                items = [t.strip() for t in cat_match.group(1).split(",") if t.strip()]
                types.extend(items)

            if types:
                interactions[grade_code] = types

        return interactions
