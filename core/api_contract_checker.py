from __future__ import annotations

import re
from models.diff_models import ParsedDiff


def check_api_contracts(diff: ParsedDiff) -> list[dict]:
    """
    Heuristic check for frontend/backend API contract mismatches.

    Looks for JSON field names returned by changed backend routes and
    compares them against field accesses in changed frontend files.

    Returns a list of potential mismatch findings.
    """
    backend_fields: dict[str, list[str]] = {}
    frontend_accesses: dict[str, list[str]] = {}

    for f in diff.files:
        path_lower = f.path.lower()
        is_backend = "routes" in path_lower or "views" in path_lower
        is_frontend = any(ext in f.path for ext in [".tsx", ".ts", ".jsx", ".js"])

        additions = [
            line[1:] for hunk in f.hunks
            for line in hunk.lines if line.startswith("+")
        ]

        if is_backend:
            fields = _extract_json_keys(additions)
            if fields:
                backend_fields[f.path] = fields

        if is_frontend:
            accesses = _extract_field_accesses(additions)
            if accesses:
                frontend_accesses[f.path] = accesses

    return _find_mismatches(backend_fields, frontend_accesses)


def _extract_json_keys(lines: list[str]) -> list[str]:
    """Extract JSON key names from return statement dict literals."""
    keys: list[str] = []
    for line in lines:
        for match in re.finditer(r'"([a-z_][a-z_0-9]*)"\s*:', line):
            keys.append(match.group(1))
    return keys


def _extract_field_accesses(lines: list[str]) -> list[str]:
    """Extract .field_name accesses from frontend API response handling."""
    fields: list[str] = []
    for line in lines:
        for match in re.finditer(r'(?:response|data|res)\.([a-z_][a-z_0-9]*)', line):
            fields.append(match.group(1))
    return fields


def _find_mismatches(
    backend: dict[str, list[str]],
    frontend: dict[str, list[str]],
) -> list[dict]:
    all_backend = {f for fields in backend.values() for f in fields}
    all_frontend = {f for fields in frontend.values() for f in fields}

    mismatches = all_frontend - all_backend
    findings = []

    for field in sorted(mismatches):
        findings.append({
            "category": "api_contract",
            "severity": "warning",
            "title": f"Frontend reads '{field}' — not found in backend response",
            "description": (
                f"The frontend accesses response.{field} but this key was not found "
                f"in the backend route additions. Possible mismatch."
            ),
            "evidence": f"Frontend reads: .{field} | Backend keys: {sorted(all_backend)}",
        })

    return findings
