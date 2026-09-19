"""MCP server for controlled access to local brain notes."""

from __future__ import annotations

import logging
import os
from typing import Any

from mcp.server.mcpserver import MCPServer

from .brain import list_notes, read_note, search_notes, write_note
from .config import load_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

settings = load_settings()
app = MCPServer(name="brain-mcp")


@app.tool(name="search_notes", description="Search notes by filename and content using a case-insensitive query.")
def search_notes_tool(query: str) -> dict[str, Any]:
	"""Search notes for a query string."""
	return search_notes(settings=settings, query=query)


@app.tool(name="list_notes", description="List files and folders in the brain directory, optionally under a subpath.")
def list_notes_tool(path: str | None = None) -> dict[str, Any]:
	"""List notes from root or a specific subpath."""
	return list_notes(settings=settings, path=path)


@app.tool(name="read_note", description="Read a single note file from the brain directory.")
def read_note_tool(path: str) -> dict[str, Any]:
	"""Read one note file by relative path."""
	return read_note(settings=settings, path=path)


@app.tool(name="write_note", description="Write or overwrite a note in the brain directory. Use Inbox/ as default folder when no specific path is given.")
def write_note_tool(path: str, content: str) -> dict[str, Any]:
	"""Write a note at a relative path within the brain."""
	return write_note(settings=settings, path=path, content=content)


def main() -> None:
	transport = os.getenv("MCP_TRANSPORT", "stdio")
	if transport == "http":
		host = os.getenv("MCP_HOST", "0.0.0.0")
		port = int(os.getenv("PORT", "8002"))
		logger.info(f"Starting brain MCP server with SSE transport on {host}:{port}...")
		app.run("sse", host=host, port=port)
	else:
		logger.info("Starting brain MCP server with stdio transport...")
		app.run("stdio")


if __name__ == "__main__":
	main()

