"""Runtime configuration for the brain MCP server."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
	"""Environment-backed settings for note discovery and safety limits."""

	brain_path: Path
	max_results: int
	max_file_size: int


def _get_env_int(name: str, default: int, minimum: int) -> int:
	raw = os.getenv(name)
	if raw is None:
		return default

	try:
		value = int(raw)
	except ValueError as exc:
		raise ValueError(f"{name} must be an integer") from exc

	if value < minimum:
		raise ValueError(f"{name} must be >= {minimum}")
	return value


def load_settings() -> Settings:
	"""Load and validate settings from environment variables."""
	raw_brain_path = os.getenv("BRAIN_PATH", "./brain")
	brain_path = Path(raw_brain_path).expanduser().resolve()
	max_results = _get_env_int("BRAIN_MAX_RESULTS", default=10, minimum=1)
	max_file_size = _get_env_int("BRAIN_MAX_FILE_SIZE", default=1024 * 1024, minimum=1)

	return Settings(
		brain_path=brain_path,
		max_results=max_results,
		max_file_size=max_file_size,
	)

