from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PrdMcpDeploymentTests(unittest.TestCase):
    def test_compose_is_separate_read_only_and_does_not_create_a_bridge(self) -> None:
        compose = (ROOT / "compose.mcp.yaml").read_text(encoding="utf-8")

        self.assertIn("container_name: neurovi-prd-mcp", compose)
        self.assertIn(":/repository:ro", compose)
        self.assertIn("network_mode: host", compose)
        self.assertNotIn("ports:", compose)
        self.assertNotIn("networks:", compose)
        self.assertIn("read_only: true", compose)
        self.assertIn("cap_drop:\n      - ALL", compose)
        self.assertIn("no-new-privileges:true", compose)
        self.assertIn("pids_limit: 128", compose)

    def test_reconciliation_agent_gateway_is_exposed_only_on_loopback(self) -> None:
        compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
        environment = (ROOT / ".env.example").read_text(encoding="utf-8")
        expected_binding = "127.0.0.1:$" + "{NEUROVI_AGENT_HOST_PORT:-8080}:8080"

        self.assertIn(expected_binding, compose)
        self.assertIn("NEUROVI_AGENT_HOST_PORT=8080", environment)

    def test_mcp_image_contains_only_the_read_runtime(self) -> None:
        dockerfile = (ROOT / "Dockerfile.mcp").read_text(encoding="utf-8")
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

        self.assertIn('mcp = ["mcp==1.29.0"]', pyproject)
        self.assertIn('neurovi-prd-mcp = "neurovi_prd_server.mcp_server:main"', pyproject)
        self.assertNotIn("openssh", dockerfile)
        self.assertNotIn("git ", dockerfile)
        self.assertIn("USER 10003:10003", dockerfile)

    def test_installer_rejects_unsafe_network_defaults_and_keeps_secret_outside_git(self) -> None:
        setup = (ROOT / "setup-prd-mcp.sh").read_text(encoding="utf-8")
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

        subprocess.run(["bash", "-n", str(ROOT / "setup-prd-mcp.sh")], check=True)
        self.assertIn("private IPv4 LAN or loopback", setup)
        self.assertIn("listener.bind", setup)
        self.assertIn("NEUROVI_PRD_MCP_BIND_HOST=$HOST_IP", setup)
        self.assertIn(
            "NEUROVI_PRD_MCP_AGENT_GATEWAY_URL=$AGENT_GATEWAY_URL", setup
        )
        self.assertIn("existing_value NEUROVI_PRD_MCP_ACTOR_ID", setup)
        self.assertIn("--project-name neurovi-prd-mcp", setup)
        self.assertIn("-m 0600", setup)
        self.assertIn("/prd-mcp.env", ignore)

    def test_client_documentation_uses_remote_url_and_bearer_environment(self) -> None:
        documentation = (ROOT / "docs/prd-mcp-server.md").read_text(encoding="utf-8")

        self.assertIn("--url http://192.168.1.20:8767/mcp", documentation)
        self.assertIn(
            "--bearer-token-env-var NEUROVI_PRD_MCP_TOKEN", documentation
        )
        self.assertIn("network_mode: host", documentation)
        self.assertIn("start_prd_reconciliation", documentation)
        self.assertIn(
            "NEUROVI_PRD_MCP_AGENT_GATEWAY_URL=http://127.0.0.1:8080/invoke",
            documentation,
        )
        self.assertIn("confirmation=USER_CONFIRMED", documentation)
        self.assertIn("confirmation=STOP_SESSION", documentation)
        self.assertIn("default port `8767`", documentation)


if __name__ == "__main__":
    unittest.main()
