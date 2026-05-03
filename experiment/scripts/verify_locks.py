#!/usr/bin/env python3
"""Create and verify protected-file lock manifests for experiment runs."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Iterable
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

EXCLUDED_DIR_NAMES = {"__pycache__", ".git", ".mypy_cache", ".pytest_cache"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


class LockManifestError(ValueError):
    """Raised when a lock manifest cannot be created or verified."""


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def utc_now() -> str:
    return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise LockManifestError(f"Expected YAML mapping at {path}")
    return payload


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise LockManifestError(f"Expected JSON object at {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha256_bytes(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_json(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def unique_preserving_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            output.append(item)
    return output


def normalize_rel_path(path: str | Path) -> str:
    text = path.as_posix() if isinstance(path, Path) else path.replace("\\", "/")
    if text.startswith("./"):
        text = text[2:]
    return text.lstrip("/")


def path_relative_to_root(root: Path, path: Path) -> str:
    try:
        return normalize_rel_path(path.resolve().relative_to(root.resolve()))
    except ValueError as exc:
        msg = f"{path} is outside lock root {root}"
        raise LockManifestError(msg) from exc


def should_skip(path: Path, excluded_paths: set[str], root: Path) -> bool:
    rel_path = path_relative_to_root(root, path)
    if rel_path in excluded_paths:
        return True
    if any(part in EXCLUDED_DIR_NAMES for part in path.parts):
        return True
    return path.suffix in EXCLUDED_SUFFIXES


def locked_paths_from_config(config_path: Path) -> list[str]:
    payload = load_yaml(config_path)
    lock_policy = payload.get("lock_policy", {})
    if not isinstance(lock_policy, dict):
        raise LockManifestError(f"{config_path} lock_policy must be a mapping")
    paths = lock_policy.get("locked_paths", [])
    if not isinstance(paths, list):
        raise LockManifestError(f"{config_path} locked_paths must be a list")
    return [str(path) for path in paths]


def collect_locked_files(
    *,
    root: Path,
    locked_paths: list[str],
    excluded_paths: list[str],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    root = root.resolve()
    excluded = {normalize_rel_path(path) for path in excluded_paths}
    files: dict[str, dict[str, Any]] = {}
    missing_patterns: list[str] = []

    for pattern in locked_paths:
        if Path(pattern).is_absolute():
            raise LockManifestError("locked paths must be relative to the repo root")
        glob_pattern = f"{pattern}/*" if pattern.endswith("/**") else pattern
        matches = sorted(root.glob(glob_pattern))
        file_matches = [
            path
            for path in matches
            if path.is_file() and not should_skip(path, excluded, root)
        ]
        if not file_matches:
            missing_patterns.append(pattern)
            continue
        for path in file_matches:
            rel_path = path_relative_to_root(root, path)
            stat = path.stat()
            files[rel_path] = {
                "sha256": sha256_bytes(path),
                "size_bytes": stat.st_size,
            }

    return dict(sorted(files.items())), missing_patterns


def canonical_manifest_payload(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": manifest["schema_version"],
        "locked_paths": manifest["locked_paths"],
        "excluded_paths": manifest["excluded_paths"],
        "missing_patterns": manifest["missing_patterns"],
        "files": manifest["files"],
    }


def build_manifest(
    *,
    root: Path,
    locked_paths: list[str],
    excluded_paths: list[str] | None = None,
) -> dict[str, Any]:
    normalized_locked_paths = unique_preserving_order(
        normalize_rel_path(path) for path in locked_paths
    )
    normalized_excluded_paths = unique_preserving_order(
        normalize_rel_path(path) for path in (excluded_paths or [])
    )
    files, missing_patterns = collect_locked_files(
        root=root,
        locked_paths=normalized_locked_paths,
        excluded_paths=normalized_excluded_paths,
    )
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "created_at": utc_now(),
        "root": root.resolve().as_posix(),
        "locked_paths": normalized_locked_paths,
        "excluded_paths": normalized_excluded_paths,
        "missing_patterns": missing_patterns,
        "files": files,
    }
    manifest["manifest_hash"] = sha256_json(canonical_manifest_payload(manifest))
    return manifest


def verify_manifest(
    *,
    baseline_manifest: dict[str, Any],
    root: Path,
) -> dict[str, Any]:
    current_manifest = build_manifest(
        root=root,
        locked_paths=list(baseline_manifest["locked_paths"]),
        excluded_paths=list(baseline_manifest.get("excluded_paths", [])),
    )
    baseline_files = baseline_manifest["files"]
    current_files = current_manifest["files"]
    baseline_paths = set(baseline_files)
    current_paths = set(current_files)

    added_files = sorted(current_paths - baseline_paths)
    removed_files = sorted(baseline_paths - current_paths)
    changed_files = []
    for path in sorted(baseline_paths & current_paths):
        before = baseline_files[path]
        after = current_files[path]
        if before["sha256"] != after["sha256"]:
            changed_files.append(
                {
                    "path": path,
                    "before_sha256": before["sha256"],
                    "after_sha256": after["sha256"],
                    "before_size_bytes": before["size_bytes"],
                    "after_size_bytes": after["size_bytes"],
                }
            )

    status = (
        "unchanged"
        if not added_files and not removed_files and not changed_files
        else "changed"
    )
    return {
        "schema_version": 1,
        "checked_at": utc_now(),
        "status": status,
        "protocol_violation": status == "changed",
        "root": root.resolve().as_posix(),
        "manifest_hash": baseline_manifest["manifest_hash"],
        "current_manifest_hash": current_manifest["manifest_hash"],
        "file_count_before": len(baseline_files),
        "file_count_after": len(current_files),
        "added_files": added_files,
        "removed_files": removed_files,
        "changed_files": changed_files,
        "missing_patterns_before": baseline_manifest.get("missing_patterns", []),
        "missing_patterns_after": current_manifest.get("missing_patterns", []),
    }


def output_exclusion(root: Path, output_path: Path | None) -> list[str]:
    if output_path is None:
        return []
    try:
        return [path_relative_to_root(root, output_path)]
    except LockManifestError:
        return []


def parse_snapshot_args(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("snapshot", help="Write a lock manifest.")
    parser.add_argument("--root", type=Path, default=repo_root_from_script())
    parser.add_argument("--config", type=Path, help="Run matrix YAML path.")
    parser.add_argument(
        "--locked-path",
        action="append",
        default=[],
        help="Additional protected path or glob, repeatable.",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--print-json", action="store_true")


def parse_verify_args(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("verify", help="Verify a lock manifest.")
    parser.add_argument("--root", type=Path, default=repo_root_from_script())
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--print-json", action="store_true")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    parse_snapshot_args(subparsers)
    parse_verify_args(subparsers)
    return parser.parse_args()


def snapshot_from_args(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.resolve()
    config_paths = locked_paths_from_config(args.config) if args.config else []
    locked_paths = unique_preserving_order([*config_paths, *args.locked_path])
    manifest = build_manifest(
        root=root,
        locked_paths=locked_paths,
        excluded_paths=output_exclusion(root, args.output),
    )
    write_json(args.output, manifest)
    return manifest


def verify_from_args(args: argparse.Namespace) -> dict[str, Any]:
    result = verify_manifest(
        baseline_manifest=load_json(args.manifest),
        root=args.root.resolve(),
    )
    if args.output is not None:
        write_json(args.output, result)
    return result


def main() -> int:
    args = parse_args()
    if args.command == "snapshot":
        payload = snapshot_from_args(args)
        exit_code = 0
    elif args.command == "verify":
        payload = verify_from_args(args)
        exit_code = 0 if payload["status"] == "unchanged" else 1
    else:  # pragma: no cover - argparse prevents this path
        raise LockManifestError(f"Unknown command: {args.command}")

    if args.print_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(payload.get("manifest_hash") or payload["current_manifest_hash"])
        if "status" in payload:
            print(f"status: {payload['status']}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
