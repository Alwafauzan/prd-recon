from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping


class AgentGatewayError(RuntimeError):
    pass


@dataclass(frozen=True)
class AgentResponse:
    message: str
    status: str | None = None
    session_id: str | None = None
    raw: Mapping[str, Any] | None = None


class AgentGateway:
    def __init__(
        self, url: str, token: str | None = None, timeout_seconds: int = 180
    ):
        self.url = url
        self.token = token
        self.timeout_seconds = timeout_seconds

    def invoke(
        self,
        capability: str,
        parameters: Mapping[str, Any],
        actor: Mapping[str, Any],
    ) -> AgentResponse:
        payload = json.dumps(
            {
                "capability": capability,
                "parameters": dict(parameters),
                "actor": dict(actor),
            },
            ensure_ascii=False,
        ).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(
            self.url, data=payload, headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout_seconds
            ) as response:
                body = response.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError) as error:
            raise AgentGatewayError(f"Agent gateway request failed: {error}") from error
        try:
            decoded = json.loads(body)
        except json.JSONDecodeError as error:
            raise AgentGatewayError("Agent gateway returned invalid JSON.") from error
        message = decoded.get("message")
        if not isinstance(message, str) or not message.strip():
            raise AgentGatewayError("Agent gateway response must contain a message.")
        return AgentResponse(
            message=message,
            status=decoded.get("status"),
            session_id=decoded.get("session_id"),
            raw=decoded,
        )
