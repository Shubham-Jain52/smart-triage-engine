"""Tests for team mapping loader."""

import json
from pathlib import Path

from src.integrations.jira.team_mapping import load_team_mapping, resolve_mapping


def test_load_and_resolve_mapping(tmp_path, monkeypatch):
    mapping_file = tmp_path / "mapping.json"
    mapping_file.write_text(
        json.dumps(
            {
                "DevOps": {"component": "DevOps", "labels": ["auto-routed"]},
                "hitl": {"labels": ["hitl"]},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("JIRA_TEAM_MAPPING_PATH", str(mapping_file))
    from src.config import get_settings

    get_settings.cache_clear()

    mapping = load_team_mapping(Path(mapping_file))
    assert "DevOps" in mapping
    team = resolve_mapping("DevOps", requires_hitl=False, mapping=mapping)
    assert team.component == "DevOps"
    hitl = resolve_mapping("DevOps", requires_hitl=True, mapping=mapping)
    assert hitl.labels == ["hitl"]
