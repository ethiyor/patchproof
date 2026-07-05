from __future__ import annotations

import re
from pathlib import Path

from models.diff_models import Hunk, ParsedDiff, ParsedFile

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXTENSION_TO_LANGUAGE: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".cpp": "cpp",
    ".c": "c",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".md": "markdown",
    ".sql": "sql",
    ".sh": "shell",
    ".env": "env",
}

# Each tuple is (flag_name, substring_that_triggers_it).
# Checked against the lowercased file path using `in`.
RISKY_PATTERNS: list[tuple[str, str]] = [
    ("auth", "auth"),
    ("login", "login"),
    ("permissions", "permissions"),
    ("payments", "payments"),
    ("billing", "billing"),
    ("migration", "migration"),
    ("env_file", ".env"),
    ("config", "config"),
    ("middleware", "middleware"),
    ("security", "security"),
    ("routes", "routes"),
]

# A file path matching any of these substrings is treated as a test file.
TEST_INDICATORS: list[str] = [
    "test_",
    "_test.",
    "/tests/",
    "/test/",
    "/spec/",
    "_spec.",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DIFF_HEADER_RE = re.compile(r"^diff --git a/(.*) b/(.*)$")


def _detect_language(path: str) -> str | None:
    suffix = Path(path).suffix.lower()
    return EXTENSION_TO_LANGUAGE.get(suffix)


def _detect_risk_flags(path: str) -> list[str]:
    path_lower = path.lower()
    return [flag for flag, pattern in RISKY_PATTERNS if pattern in path_lower]


def _is_test_file(path: str) -> bool:
    path_lower = path.lower()
    return any(indicator in path_lower for indicator in TEST_INDICATORS)


# ---------------------------------------------------------------------------
# Core parser
# ---------------------------------------------------------------------------

def _parse_files(raw: str) -> list[ParsedFile]:
    """Split a raw unified diff into a list of per-file records."""
    lines = raw.splitlines()

    # We accumulate file and hunk data as plain dicts to avoid mutating
    # Pydantic models mid-construction, then build the models at the end.
    file_blocks: list[dict] = []
    current: dict | None = None
    current_hunk: dict | None = None

    def _save_hunk() -> None:
        """Push the current hunk dict into the current file block."""
        if current_hunk and current is not None:
            current["hunks"].append(
                {
                    "header": current_hunk["header"],
                    "lines": list(current_hunk["lines"]),
                    "additions": current_hunk["additions"],
                    "deletions": current_hunk["deletions"],
                }
            )
            current["additions"] += current_hunk["additions"]
            current["deletions"] += current_hunk["deletions"]

    for line in lines:
        # ------------------------------------------------------------------ #
        # New file block
        # ------------------------------------------------------------------ #
        if line.startswith("diff --git "):
            _save_hunk()
            current_hunk = None

            if current is not None:
                file_blocks.append(current)

            m = _DIFF_HEADER_RE.match(line)
            if m:
                new_path = m.group(2)
            else:
                # Fallback: take everything after the last " b/"
                new_path = line.split(" b/", 1)[-1] if " b/" in line else "unknown"

            current = {
                "path": new_path,
                "old_path": None,
                "status": "modified",
                "hunks": [],
                "additions": 0,
                "deletions": 0,
            }
            continue

        if current is None:
            continue  # preamble before the first diff block

        # ------------------------------------------------------------------ #
        # File-level status markers (appear before the first @@ line)
        # ------------------------------------------------------------------ #
        if line.startswith("new file mode"):
            current["status"] = "added"
            continue

        if line.startswith("deleted file mode"):
            current["status"] = "deleted"
            continue

        if line.startswith("rename from "):
            current["old_path"] = line[len("rename from "):]
            current["status"] = "renamed"
            continue

        if line.startswith("rename to "):
            # After a rename the canonical path is the destination.
            current["path"] = line[len("rename to "):]
            continue

        # Skip the --- / +++ file header lines (they appear before the first @@
        # and do not represent code changes).
        if line.startswith("--- ") or line.startswith("+++ "):
            continue

        # ------------------------------------------------------------------ #
        # Hunk header
        # ------------------------------------------------------------------ #
        if line.startswith("@@ "):
            _save_hunk()
            current_hunk = {
                "header": line,
                "lines": [],
                "additions": 0,
                "deletions": 0,
            }
            continue

        # ------------------------------------------------------------------ #
        # Hunk content
        # ------------------------------------------------------------------ #
        if current_hunk is not None:
            if line.startswith("+"):
                current_hunk["additions"] += 1
            elif line.startswith("-"):
                current_hunk["deletions"] += 1
            # context lines (start with space) and the rare "\ No newline"
            # are stored but not counted.
            current_hunk["lines"].append(line)

    # Flush the last hunk and file
    _save_hunk()
    if current is not None:
        file_blocks.append(current)

    # Build Pydantic models from the accumulated dicts
    result: list[ParsedFile] = []
    for block in file_blocks:
        path = block["path"]
        hunks = [Hunk(**h) for h in block["hunks"]]
        result.append(
            ParsedFile(
                path=path,
                old_path=block["old_path"],
                status=block["status"],  # type: ignore[arg-type]
                language=_detect_language(path),
                additions=block["additions"],
                deletions=block["deletions"],
                hunks=hunks,
                risk_flags=_detect_risk_flags(path),
                is_test_file=_is_test_file(path),
            )
        )

    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_diff(raw: str) -> ParsedDiff:
    """Parse a raw unified diff string into a structured :class:`ParsedDiff`."""
    if not raw or not raw.strip():
        return ParsedDiff(
            files=[],
            total_files=0,
            total_additions=0,
            total_deletions=0,
            has_test_changes=False,
            risky_files=[],
        )

    files = _parse_files(raw)

    return ParsedDiff(
        files=files,
        total_files=len(files),
        total_additions=sum(f.additions for f in files),
        total_deletions=sum(f.deletions for f in files),
        has_test_changes=any(f.is_test_file for f in files),
        risky_files=[f.path for f in files if f.risk_flags],
    )
