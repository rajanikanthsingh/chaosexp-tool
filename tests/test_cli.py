"""Smoke tests for the ChaosMonkey CLI."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from chaosmonkey import cli

runner = CliRunner()


def test_discover_outputs_services() -> None:
    result = runner.invoke(cli.app, ["discover"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "services" in payload
    assert isinstance(payload["services"], list)


def test_execute_dry_run_creates_report() -> None:
    with runner.isolated_filesystem():
        result = runner.invoke(cli.app, ["execute", "--dry-run"])
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["status"] == "dry-run"

        reports_dir = Path("reports")
        assert reports_dir.exists()
        artifacts = list(reports_dir.glob("*.json"))
        assert artifacts, "Expected JSON report artifact to be created"
