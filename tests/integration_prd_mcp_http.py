#!/usr/bin/env python3
"""Exercise the hardened PRD MCP image over Streamable HTTP."""

from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
IMAGE = os.environ.get("NEUROVI_PRD_MCP_TEST_IMAGE", "neurovi-prd-mcp:test")
TOKEN = "integration-token-" + "a" * 48
CLIENT_SCRIPT = r"""
import asyncio
import json
import os

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def main():
    headers = {"Authorization": f"Bearer {os.environ['MCP_TOKEN']}"}
    async with streamablehttp_client(os.environ["MCP_URL"], headers=headers) as streams:
        read_stream, write_stream, _ = streams
        async with ClientSession(read_stream, write_stream) as session:
            initialized = await session.initialize()
            tools = await session.list_tools()
            status = await session.call_tool("prd_status", {})
            task = await session.call_tool(
                "get_task_context",
                {
                    "task": "check-in mandiri",
                    "e2e": "E2E-RJ",
                    "document_limit": 1,
                    "section_families": ["scope", "flow_scenarios"],
                },
            )
    names = sorted(tool.name for tool in tools.tools)
    assert initialized.serverInfo.name == "neurovi-prd-readonly"
    assert len(names) == 6, names
    assert not status.isError
    assert not task.isError
    print(json.dumps({"server": initialized.serverInfo.name, "tools": names}))


asyncio.run(main())
"""


def available_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def request_status(url: str, token: str | None, host: str | None = None) -> int:
    payload = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "security-test", "version": "1.0"},
            },
        }
    ).encode()
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    if host is not None:
        headers["Host"] = host
    try:
        urlopen(Request(url, data=payload, headers=headers), timeout=5)
    except HTTPError as error:
        return error.code
    raise AssertionError("unauthorized MCP request unexpectedly succeeded")


def main() -> int:
    port = available_port()
    name = f"neurovi-prd-mcp-integration-{os.getpid()}"
    public_url = f"http://127.0.0.1:{port}/mcp"
    command = [
        "docker",
        "run",
        "--rm",
        "--detach",
        "--name",
        name,
        "--network",
        "host",
        "--read-only",
        "--tmpfs",
        "/tmp:size=64m,mode=1777",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
        "--pids-limit",
        "128",
        "--env",
        "NEUROVI_PRD_MCP_REPOSITORY=/repository",
        "--env",
        "NEUROVI_PRD_MCP_BIND_HOST=127.0.0.1",
        "--env",
        f"NEUROVI_PRD_MCP_PORT={port}",
        "--env",
        f"NEUROVI_PRD_MCP_PUBLIC_URL={public_url}",
        "--env",
        f"NEUROVI_PRD_MCP_TOKEN={TOKEN}",
        "--volume",
        f"{ROOT / 'neurovi-prd'}:/repository:ro",
        IMAGE,
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
    try:
        health_url = f"http://127.0.0.1:{port}/healthz"
        for _ in range(40):
            try:
                with urlopen(health_url, timeout=2) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(0.25)
        else:
            logs = subprocess.run(
                ["docker", "logs", name], capture_output=True, text=True
            )
            raise RuntimeError(logs.stdout + logs.stderr)

        assert request_status(public_url, None) == 401
        assert request_status(public_url, "wrong-token-" + "b" * 48) == 401
        assert request_status(public_url, TOKEN, "untrusted.example") == 421
        completed = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "--interactive",
                "--network",
                "host",
                "--env",
                f"MCP_URL={public_url}",
                "--env",
                f"MCP_TOKEN={TOKEN}",
                "--entrypoint",
                "python",
                IMAGE,
                "-",
            ],
            input=CLIENT_SCRIPT,
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        result = json.loads(completed.stdout)
        print(
            json.dumps(
                {
                    "auth_without_token": 401,
                    "auth_wrong_token": 401,
                    "dns_rebinding": 421,
                    "server": result["server"],
                    "tool_count": len(result["tools"]),
                },
                sort_keys=True,
            )
        )
    finally:
        subprocess.run(
            ["docker", "stop", "--time", "2", name],
            capture_output=True,
            text=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
