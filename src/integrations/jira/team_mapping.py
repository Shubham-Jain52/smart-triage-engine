"""Load team → Jira field mapping for Phase 3 worker."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class TeamJiraMapping:
    component: Optional[str] = None
    assignee_account_id: Optional[str] = None
    labels: List[str] = field(default_factory=list)


def load_team_mapping(path: Optional[Path] = None) -> Dict[str, TeamJiraMapping]:
    """Parse jira-team-mapping JSON into structured mappings."""
    settings = get_settings()
    mapping_path = path or Path(settings.JIRA_TEAM_MAPPING_PATH)
    if not mapping_path.is_file():
        logger.warning("Team mapping file not found: %s", mapping_path)
        return {}

    with mapping_path.open(encoding="utf-8") as f:
        raw: Dict[str, Any] = json.load(f)

    out: Dict[str, TeamJiraMapping] = {}
    for key, value in raw.items():
        if not isinstance(value, dict):
            continue
        out[key] = TeamJiraMapping(
            component=value.get("component"),
            assignee_account_id=value.get("assigneeAccountId"),
            labels=list(value.get("labels") or []),
        )
    return out


def resolve_mapping(
    assigned_team: str,
    requires_hitl: bool,
    mapping: Dict[str, TeamJiraMapping],
) -> TeamJiraMapping:
    """Pick HITL mapping when flagged, otherwise team mapping."""
    if requires_hitl and "hitl" in mapping:
        return mapping["hitl"]
    return mapping.get(assigned_team, TeamJiraMapping())
