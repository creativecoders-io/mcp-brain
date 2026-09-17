# mcp-brain

A Model Context Protocol (MCP) server that provides controlled access to local Brain notes.

## Features

This MCP server implements the following tools:

- search_notes(query) - Search note filenames and note content (case-insensitive)
- list_notes(path?) - List folders and files under the configured Brain path
- read_note(path) - Read one note file by relative path

Built-in safeguards:

- Path traversal protection (cannot read outside the configured Brain root)
- Configurable file size limit for reads/search
- Configurable maximum number of search results

## Prerequisites

- Python 3.11 or higher
- A local notes folder (default is ./brain)

## Installation

### Local Installation (.venv)

1. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install the project:

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

3. Optional: copy environment template:

```bash
cp .env.example .env
```

4. Run the server (stdio transport):

```bash
BRAIN_PATH=./brain brain-mcp
```

## Docker

### Build image

```bash
docker build -t mcp-brain .
```

### Run container

```bash
docker run -i \
	-e BRAIN_PATH=/brain \
	-e BRAIN_MAX_RESULTS=10 \
	-e BRAIN_MAX_FILE_SIZE=1048576 \
	-v "$(pwd)/brain:/brain:ro" \
	mcp-brain
```

## Docker Compose

The included compose file follows the same structure as the reference project and starts a stdio-oriented container.

1. Optional: copy the environment template:

```bash
cp .env.example .env
```

2. Start the service:

```bash
docker compose -f compose.yml up --build
```

3. Run it as a one-off interactive test:

```bash
docker compose -f compose.yml run --rm brain-mcp
```

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| BRAIN_PATH | No | Root path of notes directory (default: ./brain locally, /brain in container) |
| BRAIN_MAX_RESULTS | No | Maximum returned search hits (default: 10) |
| BRAIN_MAX_FILE_SIZE | No | Max readable file size in bytes (default: 1048576) |

## MCP Client Integration

### Claude Desktop

Add a server entry to your configuration:

```json
{
	"mcpServers": {
		"brain": {
			"command": "/absolute/path/to/mcp-brain/.venv/bin/brain-mcp",
			"env": {
				"BRAIN_PATH": "/absolute/path/to/mcp-brain/brain",
				"BRAIN_MAX_RESULTS": "10",
				"BRAIN_MAX_FILE_SIZE": "1048576"
			}
		}
	}
}
```

### VS Code MCP Settings

```json
{
	"mcp": {
		"servers": {
			"brain": {
				"command": "/absolute/path/to/mcp-brain/.venv/bin/brain-mcp",
				"env": {
					"BRAIN_PATH": "/absolute/path/to/mcp-brain/brain",
					"BRAIN_MAX_RESULTS": "10",
					"BRAIN_MAX_FILE_SIZE": "1048576"
				}
			}
		}
	}
}
```

## Testing

### Unit Tests

```bash
./.venv/bin/python -m pytest -q
```

### End-to-End MCP Smoke Test (Tool Calls)

This starts your server over stdio and calls all tools via the MCP Python client.

```bash
BRAIN_PATH=./brain ./.venv/bin/python - <<'PY'
import anyio
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

async def main():
		params = StdioServerParameters(
				command="brain-mcp",
				env={
						"BRAIN_PATH": "./brain",
						"BRAIN_MAX_RESULTS": "10",
						"BRAIN_MAX_FILE_SIZE": "1048576",
				},
		)
		async with stdio_client(params) as (read_stream, write_stream):
				async with ClientSession(read_stream, write_stream) as session:
						await session.initialize()

						tools = await session.list_tools()
						print("TOOLS:", [tool.name for tool in tools.tools])

						print("LIST:", (await session.call_tool("list_notes", {"path": "People"})).model_dump())
						print("READ:", (await session.call_tool("read_note", {"path": "People/John Smith.md"})).model_dump())
						print("SEARCH:", (await session.call_tool("search_notes", {"query": "john"})).model_dump())

anyio.run(main)
PY
```

### One-Command Quick Test Script

Use the helper script if you only want to pass a query string and get a quick response.

Local server mode:

```bash
./.venv/bin/python scripts/quick_mcp_test.py "john"
```

With custom list path:

```bash
./.venv/bin/python scripts/quick_mcp_test.py "festival" --list-path Projects
```

Against a running Docker container:

```bash
./.venv/bin/python scripts/quick_mcp_test.py "john" --container brain-mcp
```

## Tools Reference

### search_notes

Search filenames and file contents for a query.

Input:

```json
{
	"query": "john"
}
```

Output (example):

```json
{
	"query": "john",
	"files_scanned": 12,
	"count": 2,
	"max_results": 10,
	"matches": [
		{
			"path": "People/John Smith.md",
			"size": 321,
			"line": 1,
			"snippet": "John is a designer..."
		}
	]
}
```

### list_notes

List files and folders under the root or a subpath.

Input:

```json
{
	"path": "People"
}
```

Output (example):

```json
{
	"path": "People",
	"count": 1,
	"entries": [
		{
			"name": "John Smith.md",
			"path": "People/John Smith.md",
			"type": "file",
			"size": 321
		}
	]
}
```

### read_note

Read one note file by relative path.

Input:

```json
{
	"path": "People/John Smith.md"
}
```

Output (example):

```json
{
	"path": "People/John Smith.md",
	"size": 321,
	"content": "...full note text..."
}
```

## Troubleshooting

### AttributeError: 'Server' object has no attribute 'list_tools'

Cause: old MCP v1 server style with MCP v2 runtime.

Fix: this project already uses MCP v2 MCPServer APIs and depends on mcp>=2.0.0 in pyproject.toml. Reinstall:

```bash
./.venv/bin/python -m pip install -e .
```

### Brain path does not exist

Set BRAIN_PATH correctly and ensure the folder exists:

```bash
BRAIN_PATH=./brain brain-mcp
```

### Path is outside of the configured brain directory

This is expected protection against path traversal. Use a path relative to BRAIN_PATH.

## Project Structure

```text
mcp-brain/
├── src/brain_mcp/
│   ├── __init__.py
│   ├── brain.py
│   ├── config.py
│   ├── security.py
│   └── server.py
├── tests/
│   └── test_brain.py
├── brain/
├── Dockerfile
├── compose.yml
├── pyproject.toml
├── .env.example
└── README.md
```

## License

MIT License - see LICENSE.
