"""Shared dataclasses for orchestrator domain objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass(slots=True)
class Target:
    identifier: str
    kind: str
    attributes: Dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class ExperimentRun:
    run_id: str
    chaos_type: str
    target_id: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
    status: str
    report_path: Optional[Path] = None
    metadata: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, str]:
        return {
            "run_id": self.run_id,
            "chaos_type": self.chaos_type,
            "target_id": self.target_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status,
            "report_path": str(self.report_path) if self.report_path else None,
            "metadata": self.metadata,
        }
