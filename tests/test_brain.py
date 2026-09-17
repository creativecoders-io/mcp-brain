from pathlib import Path

import pytest

from brain_mcp.brain import list_notes, read_note, search_notes
from brain_mcp.config import Settings


@pytest.fixture
def brain_settings(tmp_path: Path) -> Settings:
	brain_root = tmp_path / "brain"
	(brain_root / "People").mkdir(parents=True)
	(brain_root / "Projects").mkdir(parents=True)

	(brain_root / "People" / "John Smith.md").write_text(
		"John is a designer and volunteers on weekends.\n",
		encoding="utf-8",
	)
	(brain_root / "Projects" / "Community Festival.md").write_text(
		"This project has John as the lead organizer.\n",
		encoding="utf-8",
	)

	return Settings(brain_path=brain_root, max_results=10, max_file_size=1024 * 1024)


def test_list_notes_root_contains_directories(brain_settings: Settings) -> None:
	result = list_notes(brain_settings)

	assert result["path"] == "."
	assert result["count"] == 2
	assert [entry["name"] for entry in result["entries"]] == ["People", "Projects"]


def test_list_notes_subpath_lists_files(brain_settings: Settings) -> None:
	result = list_notes(brain_settings, "People")

	assert result["path"] == "People"
	assert result["count"] == 1
	assert result["entries"][0]["name"] == "John Smith.md"
	assert result["entries"][0]["type"] == "file"


def test_read_note_returns_content(brain_settings: Settings) -> None:
	result = read_note(brain_settings, "People/John Smith.md")

	assert result["path"] == "People/John Smith.md"
	assert "designer" in result["content"]


def test_read_note_rejects_path_traversal(brain_settings: Settings) -> None:
	with pytest.raises(ValueError, match="outside"):
		read_note(brain_settings, "../secret.txt")


def test_search_notes_matches_filename_and_content(brain_settings: Settings) -> None:
	result = search_notes(brain_settings, "john")

	assert result["count"] == 2
	paths = {match["path"] for match in result["matches"]}
	assert "People/John Smith.md" in paths
	assert "Projects/Community Festival.md" in paths


def test_search_notes_requires_non_empty_query(brain_settings: Settings) -> None:
	with pytest.raises(ValueError, match="must not be empty"):
		search_notes(brain_settings, "   ")