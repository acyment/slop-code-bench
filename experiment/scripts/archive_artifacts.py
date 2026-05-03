#!/usr/bin/env python3
"""Archive pilot artifacts into a reproducible directory with file hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

from git import InvalidGitRepositoryError
from git import Repo

DEFAULT_INCLUDE_PATTERNS = [
    "docs/experiment/**",
    "experiment/README.md",
    "experiment/REPRODUCIBILITY.md",
    "experiment/FORK_SETUP.md",
    "experiment/configs/**",
    "experiment/features/**",
    "experiment/prompts/**",
    "experiment/steps/**",
    "experiment/scripts/**",
    "experiment/schemas/**",
    "experiment/locks/**",
    "experiment/results/problem_inventory.jsonl",
    "experiment/results/problem_selection_report.md",
    "experiment/results/m10_mvp_dry_run/**",
    "experiment/results/m11_full_pilot_preflight/**",
    "experiment/results/m12_pilot_report/**",
]
EXCLUDED_PARTS = {
    ".git",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


class ArchiveError(ValueError):
    """Raised when artifact archiving cannot proceed."""


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def utc_now() -> str:
    return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")


def sha256_bytes(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def repo_metadata(root: Path) -> dict[str, Any]:
    try:
        repo = Repo(root)
    except InvalidGitRepositoryError:
        return {"branch": "unknown", "head_commit": "unknown"}
    return {
        "branch": repo.active_branch.name,
        "head_commit": repo.head.commit.hexsha,
    }


def rel_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ArchiveError(f"{path} is outside archive root {root}") from exc


def should_exclude(path: Path, repo_root: Path, output_dir: Path) -> bool:
    if output_dir.resolve() in [path.resolve(), *path.resolve().parents]:
        return True
    if any(part in EXCLUDED_PARTS for part in path.parts):
        return True
    if path.suffix in EXCLUDED_SUFFIXES:
        return True
    rel = rel_path(path, repo_root)
    return (
        "auth" in rel.lower()
        or "secret" in rel.lower()
        or "credential" in rel.lower()
        or "token" in rel.lower()
    )


def expand_patterns(
    *, repo_root: Path, output_dir: Path, patterns: list[str]
) -> list[Path]:
    files: dict[str, Path] = {}
    for pattern in patterns:
        matches = sorted(repo_root.glob(pattern))
        for match in matches:
            if match.is_dir():
                candidates = sorted(path for path in match.rglob("*") if path.is_file())
            else:
                candidates = [match] if match.is_file() else []
            for path in candidates:
                if should_exclude(path, repo_root, output_dir):
                    continue
                files[rel_path(path, repo_root)] = path
    return [files[key] for key in sorted(files)]


def archive_files(
    *, repo_root: Path, output_dir: Path, files: list[Path]
) -> list[dict[str, Any]]:
    archive_root = output_dir / "files"
    rows: list[dict[str, Any]] = []
    for source in files:
        relative = rel_path(source, repo_root)
        destination = archive_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        stat = source.stat()
        rows.append(
            {
                "path": relative,
                "archive_path": rel_path(destination, output_dir),
                "sha256": sha256_bytes(source),
                "size_bytes": stat.st_size,
            }
        )
    return rows


def markdown_manifest(manifest: dict[str, Any]) -> str:
    lines = [
        "# Pilot Artifact Archive Manifest",
        "",
        f"Generated at: `{manifest['generated_at']}`",
        f"Archive status: `{manifest['archive_status']}`",
        f"File count: `{manifest['file_count']}`",
        f"Total bytes: `{manifest['total_size_bytes']}`",
        f"Head commit: `{manifest['git']['head_commit']}`",
        "",
        "## Files",
        "",
        "| path | bytes | sha256 |",
        "| --- | --- | --- |",
    ]
    for row in manifest["files"]:
        lines.append(
            f"| {row['path']} | {row['size_bytes']} | `{row['sha256']}` |"
        )
    return "\n".join(lines)


def build_archive(
    *, repo_root: Path, output_dir: Path, include_patterns: list[str]
) -> dict[str, Any]:
    files = expand_patterns(
        repo_root=repo_root,
        output_dir=output_dir,
        patterns=include_patterns,
    )
    if not files:
        raise ArchiveError("Archive input patterns selected no files")
    rows = archive_files(repo_root=repo_root, output_dir=output_dir, files=files)
    manifest = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "archive_status": "pre_evidence_artifact_archive",
        "archive_type": "directory_copy",
        "git": repo_metadata(repo_root),
        "include_patterns": include_patterns,
        "excluded_parts": sorted(EXCLUDED_PARTS),
        "excluded_suffixes": sorted(EXCLUDED_SUFFIXES),
        "file_count": len(rows),
        "total_size_bytes": sum(int(row["size_bytes"]) for row in rows),
        "files": rows,
    }
    write_json(output_dir / "archive_manifest.json", manifest)
    write_text(output_dir / "archive_manifest.md", markdown_manifest(manifest))
    return manifest


def parse_args() -> argparse.Namespace:
    repo_root = repo_root_from_script()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=repo_root)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=repo_root / "experiment/results/m12_archive/pre_evidence_archive",
    )
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        help="Additional include pattern relative to repo root.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.root.resolve()
    output_dir = args.output_dir.resolve()
    include_patterns = DEFAULT_INCLUDE_PATTERNS + list(args.include)
    manifest = build_archive(
        repo_root=repo_root,
        output_dir=output_dir,
        include_patterns=include_patterns,
    )
    print(
        json.dumps(
            {
                "archive_dir": output_dir.as_posix(),
                "file_count": manifest["file_count"],
                "total_size_bytes": manifest["total_size_bytes"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
