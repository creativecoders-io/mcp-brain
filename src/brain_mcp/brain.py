"""Core note operations for the brain MCP server."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .config import Settings
from .security import resolve_user_path

logger = logging.getLogger(__name__)

# In-process PDF text cache: (absolute_path, mtime) -> extracted text
# Invalidates automatically when a file is modified.
_pdf_cache: dict[tuple[str, float], str | None] = {}


def _extract_pdf_text(path: Path) -> str | None:
	"""Extract plain text from a PDF, using an in-memory cache keyed on (path, mtime)."""
	key = (str(path.resolve()), path.stat().st_mtime)
	if key not in _pdf_cache:
		try:
			from pypdf import PdfReader
			reader = PdfReader(str(path))
			pages = [page.extract_text() or "" for page in reader.pages]
			text = "\n".join(pages).strip()
			_pdf_cache[key] = text if text else None
		except Exception as exc:
			logger.debug("Could not extract text from %s: %s", path.name, exc)
			_pdf_cache[key] = None
	return _pdf_cache[key]


def _read_file_text(path: Path) -> str | None:
	"""Return the text content of a file, handling both plain text and PDFs."""
	if path.suffix.lower() == ".pdf":
		return _extract_pdf_text(path)
	try:
		return path.read_text(encoding="utf-8")
	except (UnicodeDecodeError, OSError):
		return None


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

	content = _read_file_text(target)
	if content is None:
		if target.suffix.lower() == ".pdf":
			raise ValueError(
				f"No extractable text in {path} — it may be a scanned image PDF."
			)
		raise ValueError(f"Could not read {path} as text.")

	return {
		"path": _to_relative(settings, target),
		"size": size,
		"format": "pdf" if target.suffix.lower() == ".pdf" else "text",
		"content": content,
	}


def search_notes(settings: Settings, query: str) -> dict[str, Any]:
	"""Search notes using BM25 ranking over filenames and content."""
	from rank_bm25 import BM25Plus

	_require_root_exists(settings)

	needle = query.strip()
	if not needle:
		raise ValueError("query must not be empty")

	# Collect all readable files
	candidates: list[tuple[Path, str]] = []
	for file_path in sorted(settings.brain_path.rglob("*")):
		if not file_path.is_file():
			continue
		if file_path.stat().st_size > settings.max_file_size:
			continue
		content = _read_file_text(file_path)
		if content is None:
			continue
		# Include filename in the indexed text so filename matches score well
		candidates.append((file_path, f"{file_path.stem} {content}"))

	if not candidates:
		return {"query": query, "files_scanned": 0, "count": 0,
				"max_results": settings.max_results, "matches": []}

	# Tokenise: lowercase split on whitespace/punctuation
	import re
	def tokenise(text: str) -> list[str]:
		return re.findall(r"[^\s\W]+", text.lower())

	corpus = [tokenise(doc) for _, doc in candidates]
	query_tokens = tokenise(needle)

	bm25 = BM25Plus(corpus)
	scores = bm25.get_scores(query_tokens)

	# Pair files with scores, filter zeros, sort descending
	ranked = sorted(
		[(candidates[i][0], float(scores[i])) for i in range(len(candidates)) if scores[i] > 0],
		key=lambda x: x[1],
		reverse=True,
	)

	matches: list[dict[str, Any]] = []
	for file_path, score in ranked[: settings.max_results]:
		content = _read_file_text(file_path) or ""
		rel = _to_relative(settings, file_path)

		# Find first matching line for the snippet
		snippet = ""
		line_number = None
		for idx, line in enumerate(content.splitlines(), start=1):
			if any(t in line.lower() for t in tokenise(needle)):
				line_number = idx
				snippet = line.strip()
				if len(snippet) > 240:
					snippet = f"{snippet[:237]}..."
				break

		matches.append({
			"path": rel,
			"size": file_path.stat().st_size,
			"score": round(score, 4),
			"line": line_number,
			"snippet": snippet,
		})

	return {
		"query": query,
		"files_scanned": len(candidates),
		"count": len(matches),
		"max_results": settings.max_results,
		"matches": matches,
	}


def write_note(settings: Settings, path: str, content: str) -> dict[str, Any]:
	"""Write or overwrite a note file within the brain directory."""
	_require_root_exists(settings)
	target = resolve_user_path(settings.brain_path, path)
	target.parent.mkdir(parents=True, exist_ok=True)
	target.write_text(content, encoding="utf-8")
	return {
		"path": _to_relative(settings, target),
		"size": target.stat().st_size,
		"written": True,
	}

