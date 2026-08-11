from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping


class LLMError(RuntimeError):
    pass


@dataclass(frozen=True)
class LLMResult:
    payload: Mapping[str, Any]
    request_id: str | None = None


class OpenAICompatibleLLM:
    """Small OpenAI-compatible client used only by the agent container."""

    def __init__(
        self,
        *,
        provider: str,
        base_url: str,
        api_key: str,
        model: str,
        reasoning_effort: str,
        timeout_seconds: int = 180,
    ) -> None:
        self.provider = provider
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.timeout_seconds = timeout_seconds

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResult:
        endpoint, body = self._request_payload(system_prompt, user_prompt)
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "neurovi-doc-reconciliator/0.1",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout_seconds
            ) as response:
                response_body = response.read().decode("utf-8")
                request_id = response.headers.get("x-request-id")
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:2000]
            raise LLMError(
                f"{self.provider} returned HTTP {error.code}: {detail}"
            ) from error
        except (urllib.error.URLError, TimeoutError) as error:
            raise LLMError(f"{self.provider} request failed: {error}") from error

        try:
            decoded = json.loads(response_body)
        except json.JSONDecodeError as error:
            raise LLMError(f"{self.provider} returned invalid JSON.") from error
        content = self._extract_content(decoded)
        return LLMResult(self._decode_object(content), request_id=request_id)

    def _request_payload(
        self, system_prompt: str, user_prompt: str
    ) -> tuple[str, dict[str, Any]]:
        if self.base_url.endswith("/responses"):
            return self.base_url, {
                "model": self.model,
                "instructions": system_prompt,
                "input": user_prompt,
                "reasoning": {"effort": self.reasoning_effort},
            }
        endpoint = (
            self.base_url
            if self.base_url.endswith("/chat/completions")
            else f"{self.base_url}/chat/completions"
        )
        return endpoint, {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "reasoning_effort": self.reasoning_effort,
        }

    @staticmethod
    def _extract_content(decoded: Mapping[str, Any]) -> str:
        output_text = decoded.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text

        choices = decoded.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, Mapping):
                message = first.get("message")
                if isinstance(message, Mapping):
                    content = message.get("content")
                    if isinstance(content, str):
                        return content
                    if isinstance(content, list):
                        text_parts = [
                            item.get("text", "")
                            for item in content
                            if isinstance(item, Mapping)
                            and isinstance(item.get("text"), str)
                        ]
                        if text_parts:
                            return "".join(text_parts)

        output = decoded.get("output")
        if isinstance(output, list):
            text_parts = []
            for item in output:
                if not isinstance(item, Mapping):
                    continue
                content = item.get("content")
                if not isinstance(content, list):
                    continue
                for part in content:
                    if isinstance(part, Mapping) and isinstance(
                        part.get("text"), str
                    ):
                        text_parts.append(part["text"])
            if text_parts:
                return "".join(text_parts)
        raise LLMError("LLM response does not contain text output.")

    @staticmethod
    def _decode_object(content: str) -> Mapping[str, Any]:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
        try:
            decoded = json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start < 0 or end <= start:
                raise LLMError("LLM response is not a JSON object.")
            try:
                decoded = json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError as error:
                raise LLMError("LLM response is not a valid JSON object.") from error
        if not isinstance(decoded, Mapping):
            raise LLMError("LLM response must be a JSON object.")
        return decoded
