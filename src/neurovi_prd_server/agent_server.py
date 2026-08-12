from __future__ import annotations

import argparse
import hmac
import json
import logging
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Mapping

from neurovi_prd_server.config import ConfigurationError, Settings
from neurovi_prd_server.llm_client import OpenAICompatibleLLM
from neurovi_prd_server.reconciliation_agent import (
    ReconciliationAgent,
    ReconciliationAgentError,
)


LOGGER = logging.getLogger("neurovi_prd_server.agent")
MAX_REQUEST_BYTES = 1_048_576


class ReconciliationHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        address: tuple[str, int],
        agent: ReconciliationAgent,
        bearer_token: str,
    ) -> None:
        super().__init__(address, ReconciliationRequestHandler)
        self.agent = agent
        self.bearer_token = bearer_token


class ReconciliationRequestHandler(BaseHTTPRequestHandler):
    server: ReconciliationHTTPServer

    def do_GET(self) -> None:
        if self.path != "/health":
            self._json(404, {"message": "Not found."})
            return
        self._json(
            200,
            {
                "status": "healthy",
                "model_profile": self.server.agent.model_profile,
            },
        )

    def do_POST(self) -> None:
        if self.path != "/invoke":
            self._json(404, {"message": "Not found."})
            return
        if not self._authorized():
            self._json(401, {"message": "Invalid agent gateway token."})
            return
        content_length = self.headers.get("Content-Length", "")
        try:
            size = int(content_length)
        except ValueError:
            self._json(400, {"message": "Invalid Content-Length."})
            return
        if size < 1 or size > MAX_REQUEST_BYTES:
            self._json(413, {"message": "Request body is empty or too large."})
            return
        try:
            payload = json.loads(self.rfile.read(size).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._json(400, {"message": "Request body must be valid JSON."})
            return
        if not isinstance(payload, Mapping):
            self._json(400, {"message": "Request body must be a JSON object."})
            return
        try:
            result = self.server.agent.invoke(payload)
        except ReconciliationAgentError as error:
            LOGGER.warning(
                "Reconciliation request rejected: capability=%s status=%s reason=%s",
                payload.get("capability", ""),
                error.status_code,
                error,
            )
            self._json(error.status_code, {"message": str(error), "status": "ERROR"})
            return
        except Exception:
            LOGGER.exception("Unhandled reconciliation agent error")
            self._json(
                500,
                {"message": "Internal reconciliation agent error.", "status": "ERROR"},
            )
            return
        self._json(200, result)

    def log_message(self, format: str, *args: Any) -> None:
        LOGGER.info("%s - %s", self.address_string(), format % args)

    def _authorized(self) -> bool:
        expected = f"Bearer {self.server.bearer_token}"
        supplied = self.headers.get("Authorization", "")
        return hmac.compare_digest(supplied, expected)

    def _json(self, status: int, payload: Mapping[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def build_agent(settings: Settings) -> ReconciliationAgent:
    settings.require_repository()
    settings.require_tools()
    settings.require_reconciliation_agent()
    assert settings.llm_provider is not None
    assert settings.llm_base_url is not None
    assert settings.llm_api_key is not None
    assert settings.llm_model is not None
    llm = OpenAICompatibleLLM(
        provider=settings.llm_provider,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        reasoning_effort=settings.llm_reasoning_effort,
        timeout_seconds=settings.llm_timeout_seconds,
    )
    return ReconciliationAgent(settings, llm)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Neurovi reconciliation agent")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("serve", help="Run the internal reconciliation HTTP service")
    health = subparsers.add_parser("health", help="Check the running agent service")
    health.add_argument("--host", default="127.0.0.1")
    return parser


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    args = build_parser().parse_args()
    command = args.command or "serve"
    try:
        settings = Settings.from_env()
        if command == "health":
            request = urllib.request.Request(
                f"http://{args.host}:{settings.agent_port}/health",
                headers={"Accept": "application/json"},
            )
            try:
                with urllib.request.urlopen(request, timeout=5) as response:
                    value = json.loads(response.read().decode("utf-8"))
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
                raise ConfigurationError(f"Agent health check failed: {error}") from error
            if value.get("status") != "healthy":
                raise ConfigurationError("Agent health check returned an unhealthy status.")
            print(json.dumps(value, ensure_ascii=False))
            return 0

        agent = build_agent(settings)
        assert settings.agent_gateway_token is not None
        server = ReconciliationHTTPServer(
            (settings.agent_bind_host, settings.agent_port),
            agent,
            settings.agent_gateway_token,
        )
        LOGGER.info(
            "Reconciliation agent listening on %s:%s with %s/%s effort=%s",
            settings.agent_bind_host,
            settings.agent_port,
            settings.llm_provider,
            settings.llm_model,
            settings.llm_reasoning_effort,
        )
        server.serve_forever()
        return 0
    except (ConfigurationError, ReconciliationAgentError) as error:
        LOGGER.error("%s", error)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
