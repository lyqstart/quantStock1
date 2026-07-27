from __future__ import annotations

import ast
from pathlib import Path


MAX_ALEMBIC_REVISION_LENGTH = 32


def _revision_id(path: Path) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "revision" for target in node.targets):
            continue
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            return node.value.value
    raise AssertionError(f"revision not found in {path}")


def test_alembic_revision_ids_fit_default_version_table() -> None:
    version_dir = Path(__file__).resolve().parents[1] / "migrations" / "versions"
    revisions = {path.name: _revision_id(path) for path in version_dir.glob("*.py")}

    assert revisions, "no Alembic revisions found"
    too_long = {
        filename: revision
        for filename, revision in revisions.items()
        if len(revision) > MAX_ALEMBIC_REVISION_LENGTH
    }
    assert not too_long, f"Alembic revision IDs exceed {MAX_ALEMBIC_REVISION_LENGTH} chars: {too_long}"
