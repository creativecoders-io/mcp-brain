#!/usr/bin/env python3
"""Quick MCP smoke test for mcp-brain.

Usage examples:
  ./.venv/bin/python scripts/quick_mcp_test.py "john"
  ./.venv/bin/python scripts/quick_mcp_test.py "festival" --list-path People
  ./.venv/bin/python scripts/quick_mcp_test.py "john" --container brain-mcp
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import anyio
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Quick MCP smoke test for mcp-brain")
    parser.add_argument("query", help="Search string for search_notes")
    parser.add_argument(
        "--list-path",
        default="People",
        help="Path argument for list_notes (default: People)",
    )
    parser.add_argument(
        "--server-command",
        default=sys.executable,
        help="Server command in local mode (default: current Python executable)",
    )
    parser.add_argument(
        "--server-args",
        nargs="*",
        default=["-m", "brain_mcp.server"],
        help="Arguments for --server-command in local mode (default: -m brain_mcp.server)",
    )
    parser.add_argument(
        "--brain-path",
        default="./brain",
        help="BRAIN_PATH for local server mode (default: ./brain)",
    )
    parser.add_argument(
        "--container",
        default=None,
        help="Optional running container name. If set, script uses: docker exec -i <container> brain-mcp",
    )
    return parser.parse_args()


def _to_printable(result: Any) -> Any:
    if hasattr(result, "model_dump"):
        return result.model_dump()
    return result


async def run_smoke_test(args: argparse.Namespace) -> None:
    if args.container:
        server_params = StdioServerParameters(
            command="docker",
            args=["exec", "-i", args.container, "brain-mcp"],
            env={},
        )
    else:
        server_params = StdioServerParameters(
            command=args.server_command,
            args=args.server_args,
            env={
                "BRAIN_PATH": args.brain_path,
                "BRAIN_MAX_RESULTS": "10",
                "BRAIN_MAX_FILE_SIZE": "1048576",
            },
        )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            tools_result = await session.list_tools()
            tools = [tool.name for tool in tools_result.tools]

            list_result = await session.call_tool("list_notes", {"path": args.list_path})
            search_result = await session.call_tool("search_notes", {"query": args.query})

            output = {
                "tools": tools,
                "list_notes": _to_printable(list_result),
                "search_notes": _to_printable(search_result),
            }

            print(json.dumps(output, indent=2))


def main() -> None:
    args = parse_args()
    anyio.run(run_smoke_test, args)


if __name__ == "__main__":
    main()
