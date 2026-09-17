"""Security utilities for safe filesystem access."""

from __future__ import annotations

from pathlib import Path


def ensure_within_root(root: Path, candidate: Path) -> Path:
	"""Ensure candidate resolves to a location within root."""
	resolved_root = root.resolve()
	resolved_candidate = candidate.resolve()

	try:
		resolved_candidate.relative_to(resolved_root)
	except ValueError as exc:
		raise ValueError("Path is outside of the configured brain directory") from exc

	return resolved_candidate


def resolve_user_path(root: Path, user_path: str | None) -> Path:
	"""Resolve a user-provided path against the configured root safely."""
	normalized = (user_path or "").strip()
	# Avoid treating user input as absolute root by stripping leading separators.
	trimmed = normalized.lstrip("/")
	candidate = root / trimmed
	return ensure_within_root(root, candidate)

