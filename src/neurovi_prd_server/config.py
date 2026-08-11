from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class ConfigurationError(RuntimeError):
    pass


REASONING_EFFORTS = frozenset(
    {"none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"}
)


def _optional_env(name: str) -> str | None:
    value = os.environ.get(name, "").strip()
    return value or None


def _parse_reasoning_effort(value: str | None) -> str:
    normalized = (value or "high").strip().casefold()
    if normalized not in REASONING_EFFORTS:
        allowed = ", ".join(sorted(REASONING_EFFORTS))
        raise ConfigurationError(
            f"Invalid NEUROVI_LLM_REASONING_EFFORT: {value}. Allowed: {allowed}"
        )
    return normalized


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().casefold()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(f"Invalid boolean value: {value}")


def _parse_ids(value: str | None) -> frozenset[int]:
    if not value:
        return frozenset()
    try:
        return frozenset(int(item.strip()) for item in value.split(",") if item.strip())
    except ValueError as error:
        raise ConfigurationError(f"Invalid Discord ID list: {value}") from error


@dataclass(frozen=True)
class Settings:
    repo_root: Path
    tools_root: Path
    command_timeout_seconds: int = 120
    discord_token: str | None = None
    discord_guild_ids: frozenset[int] = frozenset()
    discord_ephemeral: bool = True
    discord_text_help_enabled: bool = True
    discord_reconcile_role_ids: frozenset[int] = frozenset()
    discord_approver_role_ids: frozenset[int] = frozenset()
    agent_gateway_url: str | None = None
    agent_gateway_token: str | None = None
    agent_gateway_timeout_seconds: int = 180
    agent_bind_host: str = "0.0.0.0"
    agent_port: int = 8080
    llm_provider: str | None = None
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    llm_reasoning_effort: str = "high"
    llm_timeout_seconds: int = 180

    @classmethod
    def from_env(
        cls, repo_root: Path | None = None, tools_root: Path | None = None
    ) -> "Settings":
        root = repo_root or Path(
            os.environ.get("NEUROVI_REPO_ROOT", Path.cwd() / "neurovi-prd")
        )
        tools = tools_root or Path(
            os.environ.get("NEUROVI_TOOLS_ROOT", Path.cwd())
        )
        try:
            command_timeout = int(os.environ.get("NEUROVI_COMMAND_TIMEOUT_SECONDS", "120"))
            gateway_timeout = int(
                os.environ.get("NEUROVI_AGENT_GATEWAY_TIMEOUT_SECONDS", "180")
            )
            agent_port = int(os.environ.get("NEUROVI_AGENT_PORT", "8080"))
            llm_timeout = int(os.environ.get("NEUROVI_LLM_TIMEOUT_SECONDS", "180"))
        except ValueError as error:
            raise ConfigurationError(
                "Timeout values and NEUROVI_AGENT_PORT must be integers."
            ) from error
        if command_timeout < 1 or gateway_timeout < 1 or llm_timeout < 1:
            raise ConfigurationError("Timeout values must be positive.")
        if not 1 <= agent_port <= 65535:
            raise ConfigurationError("NEUROVI_AGENT_PORT must be between 1 and 65535.")
        return cls(
            repo_root=root.resolve(),
            tools_root=tools.resolve(),
            command_timeout_seconds=command_timeout,
            discord_token=os.environ.get("DISCORD_TOKEN"),
            discord_guild_ids=_parse_ids(os.environ.get("NEUROVI_DISCORD_GUILD_IDS")),
            discord_ephemeral=_parse_bool(
                os.environ.get("NEUROVI_DISCORD_EPHEMERAL"), True
            ),
            discord_text_help_enabled=_parse_bool(
                os.environ.get("NEUROVI_DISCORD_TEXT_HELP_ENABLED"), True
            ),
            discord_reconcile_role_ids=_parse_ids(
                os.environ.get("NEUROVI_DISCORD_RECONCILE_ROLE_IDS")
            ),
            discord_approver_role_ids=_parse_ids(
                os.environ.get("NEUROVI_DISCORD_APPROVER_ROLE_IDS")
            ),
            agent_gateway_url=_optional_env("NEUROVI_AGENT_GATEWAY_URL"),
            agent_gateway_token=_optional_env("NEUROVI_AGENT_GATEWAY_TOKEN"),
            agent_gateway_timeout_seconds=gateway_timeout,
            agent_bind_host=os.environ.get(
                "NEUROVI_AGENT_BIND_HOST", "0.0.0.0"
            ).strip()
            or "0.0.0.0",
            agent_port=agent_port,
            llm_provider=_optional_env("NEUROVI_LLM_PROVIDER"),
            llm_base_url=_optional_env("NEUROVI_LLM_BASE_URL"),
            llm_api_key=_optional_env("NEUROVI_LLM_API_KEY"),
            llm_model=_optional_env("NEUROVI_LLM_MODEL"),
            llm_reasoning_effort=_parse_reasoning_effort(
                os.environ.get("NEUROVI_LLM_REASONING_EFFORT")
            ),
            llm_timeout_seconds=llm_timeout,
        )

    def reconciliation_model_profile(self) -> dict[str, str]:
        missing = []
        if not self.llm_provider:
            missing.append("NEUROVI_LLM_PROVIDER")
        if not self.llm_model:
            missing.append("NEUROVI_LLM_MODEL")
        if missing:
            raise ConfigurationError(
                "Reconciliation model is not configured. Missing: "
                + ", ".join(missing)
            )
        return {
            "provider": self.llm_provider,
            "model": self.llm_model,
            "reasoning_effort": self.llm_reasoning_effort,
        }

    def require_reconciliation_agent(self) -> None:
        missing = []
        if not self.agent_gateway_token:
            missing.append("NEUROVI_AGENT_GATEWAY_TOKEN")
        if not self.llm_provider:
            missing.append("NEUROVI_LLM_PROVIDER")
        if not self.llm_base_url:
            missing.append("NEUROVI_LLM_BASE_URL")
        if not self.llm_api_key:
            missing.append("NEUROVI_LLM_API_KEY")
        if not self.llm_model:
            missing.append("NEUROVI_LLM_MODEL")
        if missing:
            raise ConfigurationError(
                "Reconciliation agent LLM configuration is incomplete. Missing: "
                + ", ".join(missing)
            )

    def require_discord(self) -> None:
        if not self.discord_token:
            raise ConfigurationError("DISCORD_TOKEN is required to start the Discord bot.")
        self.require_repository()
        self.require_tools()

    def require_repository(self) -> None:
        required = (
            self.repo_root / "AGENTS.md",
            self.repo_root / "catalog/document-index.json",
            self.repo_root / "reconciliation/e2e-inventory/e2e-domain-inventory.json",
        )
        missing = [str(path) for path in required if not path.is_file()]
        if missing:
            raise ConfigurationError(
                "NEUROVI_REPO_ROOT is not a valid Neurovi PRD repository. Missing: "
                + ", ".join(missing)
            )

    def require_tools(self) -> None:
        required = (
            self.tools_root / ".codex/skills/neurovi-show-prd/scripts/show_prd.py",
            self.tools_root / ".codex/skills/neurovi-show-e2e/scripts/show_e2e.py",
            self.tools_root / ".codex/skills/neurovi-gap-scanner/scripts/scan_gaps.py",
            self.tools_root / "scripts/build_structure.py",
        )
        missing = [str(path) for path in required if not path.is_file()]
        if missing:
            raise ConfigurationError(
                "NEUROVI_TOOLS_ROOT is not a valid reconciliator repository. Missing: "
                + ", ".join(missing)
            )
