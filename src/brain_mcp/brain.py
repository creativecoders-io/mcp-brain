"""Core note operations for the brain MCP server."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import Settings
from .security import resolve_user_path


def _require_root_exists(settings: Settings) -> None:
	if not settings.brain_path.exists():
		raise FileNotFoundError(f"Brain path does not exist: {settings.brain_path}")
	if not settings.brain_path.is_dir():
		raise NotADirectoryError(f"Brain path is not a directory: {settings.brain_path}")


def _to_relative(settings: Settings, path: Path) -> str:
	return path.resolve().relative_to(settings.brain_path).as_posix()


def list_notes(settings: Settings, path: str | None = None) -> dict[str, Any]:
	"""List files and folders under the requested path (default root)."""
	_require_root_exists(settings)
	target = resolve_user_path(settings.brain_path, path)

	if not target.exists():
		raise FileNotFoundError(f"Path does not exist: {path or '.'}")
	if not target.is_dir():
		raise NotADirectoryError(f"Path is not a directory: {path}")

	entries: list[dict[str, Any]] = []
	for item in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
		entry: dict[str, Any] = {
			"name": item.name,
			"path": _to_relative(settings, item),
			"type": "directory" if item.is_dir() else "file",
		}
		if item.is_file():
			entry["size"] = item.stat().st_size
		entries.append(entry)

	return {
		"path": _to_relative(settings, target) if target != settings.brain_path else ".",
		"count": len(entries),
		"entries": entries,
	}


def read_note(settings: Settings, path: str) -> dict[str, Any]:
	"""Read a single note file by relative path."""
	_require_root_exists(settings)
	target = resolve_user_path(settings.brain_path, path)

	if not target.exists():
		raise FileNotFoundError(f"Note does not exist: {path}")
	if not target.is_file():
		raise IsADirectoryError(f"Path points to a directory, not a file: {path}")

	size = target.stat().st_size
	if size > settings.max_file_size:
		raise ValueError(
			f"File too large ({size} bytes). Max allowed: {settings.max_file_size} bytes"
		)

	content = target.read_text(encoding="utf-8")
	return {
		"path": _to_relative(settings, target),
		"size": size,
		"content": content,
	}


def search_notes(settings: Settings, query: str) -> dict[str, Any]:
	"""Search note file names and contents for a case-insensitive query."""
	_require_root_exists(settings)

	needle = query.strip().lower()
	if not needle:
		raise ValueError("query must not be empty")

	matches: list[dict[str, Any]] = []
	files_scanned = 0

	for file_path in sorted(settings.brain_path.rglob("*")):
		if not file_path.is_file():
			continue

		files_scanned += 1

		size = file_path.stat().st_size
		if size > settings.max_file_size:
			continue

		rel = _to_relative(settings, file_path)
		haystack_name = file_path.name.lower()

		content = ""
		try:
			content = file_path.read_text(encoding="utf-8")
		except UnicodeDecodeError:
			# Skip binary/non-text files.
			continue

		haystack_content = content.lower()

		if needle not in haystack_name and needle not in haystack_content:
			continue

		snippet = ""
		line_number = None
		for idx, line in enumerate(content.splitlines(), start=1):
			if needle in line.lower():
				line_number = idx
				snippet = line.strip()
				if len(snippet) > 240:
					snippet = f"{snippet[:237]}..."
				break

		matches.append(
			{
				"path": rel,
				"size": size,
				"line": line_number,
				"snippet": snippet,
			}
		)

		if len(matches) >= settings.max_results:
			break

	return {
		"query": query,
		"files_scanned": files_scanned,
		"count": len(matches),
		"max_results": settings.max_results,
		"matches": matches,
	}

