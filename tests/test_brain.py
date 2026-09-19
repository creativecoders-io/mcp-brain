from pathlib import Path

import pytest

from brain_mcp.brain import list_notes, read_note, search_notes, write_note
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


def test_search_notes_ranks_by_relevance(brain_settings: Settings) -> None:
	# "Community Festival" appears in filename AND content; should rank higher
	# than "John Smith.md" which only mentions "Festival" in content
	(brain_settings.brain_path / "Projects" / "Community Festival.md").write_text(
		"Festival organizer: John. Festival theme: music.\n", encoding="utf-8"
	)
	result = search_notes(brain_settings, "Festival")
	assert result["count"] >= 1
	assert "score" in result["matches"][0]


def test_search_notes_multi_term_returns_scores(brain_settings: Settings) -> None:
	result = search_notes(brain_settings, "john designer")
	assert result["count"] >= 1
	for match in result["matches"]:
		assert "score" in match
		assert isinstance(match["score"], float)


def test_write_note_creates_file(brain_settings: Settings) -> None:
	result = write_note(brain_settings, "Inbox/test-note.md", "# Test\nHello world.\n")
	assert result["path"] == "Inbox/test-note.md"
	written = (brain_settings.brain_path / "Inbox" / "test-note.md").read_text()
	assert "Hello world." in written


def test_write_note_creates_parent_dirs(brain_settings: Settings) -> None:
	write_note(brain_settings, "Decisions/2026/q3.md", "# Decision\nContent.\n")
	assert (brain_settings.brain_path / "Decisions" / "2026" / "q3.md").exists()


def test_write_note_overwrites_existing(brain_settings: Settings) -> None:
	write_note(brain_settings, "People/John Smith.md", "# Updated\nNew content.\n")
	content = (brain_settings.brain_path / "People" / "John Smith.md").read_text()
	assert "New content." in content
	assert "designer" not in content


def test_write_note_rejects_path_traversal(brain_settings: Settings) -> None:
	with pytest.raises(ValueError, match="outside"):
		write_note(brain_settings, "../../etc/passwd", "evil")