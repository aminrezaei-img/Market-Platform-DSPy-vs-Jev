"""
Experiment Registry - every eval run becomes experiment with full provenance
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from .base import RegistryEntry, RegistryBase
from datetime import datetime, timezone

class ExperimentManifest(RegistryEntry):
    id: str  # experiment_id
    version: str = "1"
    candidate: str = ""  # agent_id@version or program_id@version
    baseline: Optional[str] = None  # baseline experiment or agent version
    agent_id: str = ""
    agent_version: str = ""
    workflow_id: str = ""
    workflow_version: str = ""
    model_versions: Dict[str, str] = Field(default_factory=dict)  # supervisor, verifier, etc.
    program_version: Optional[str] = None
    prompt_version: Optional[str] = None
    tool_versions: Dict[str, str] = Field(default_factory=dict)
    dataset_versions: List[str] = Field(default_factory=list)
    scorer_versions: List[str] = Field(default_factory=list)
    suite_id: str = ""
    suite_version: str = ""
    git_commit: str = "local"
    environment: str = "local"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "completed"  # running, completed, failed
    evidence_type: str = "measured"  # measured, simulated, expected
    results: Dict[str, Any] = Field(default_factory=dict)
    artifacts_path: str = ""
    trace_path: str = ""
    owner: str = "platform"
    description: str = ""
    tags: List[str] = Field(default_factory=list)

    def is_measured(self) -> bool:
        return self.evidence_type == "measured"

    def is_simulated(self) -> bool:
        return self.evidence_type == "simulated"

class ExperimentRegistry(RegistryBase[ExperimentManifest]):
    def __init__(self, registry_root: str = "registry_store"):
        super().__init__("experiments", ExperimentManifest, registry_root)

    def get_by_agent(self, agent_id: str) -> List[ExperimentManifest]:
        return [e for e in self._cache.values() if e.agent_id == agent_id]

    def get_by_suite(self, suite_id: str) -> List[ExperimentManifest]:
        return [e for e in self._cache.values() if e.suite_id == suite_id]

    def get_measured(self) -> List[ExperimentManifest]:
        return [e for e in self._cache.values() if e.evidence_type == "measured"]

    def get_simulated(self) -> List[ExperimentManifest]:
        return [e for e in self._cache.values() if e.evidence_type == "simulated"]

    def get_baseline(self, suite_id: str) -> Optional[ExperimentManifest]:
        """Get explicitly named baseline for suite"""
        candidates = [e for e in self._cache.values() if e.suite_id == suite_id and "baseline" in e.tags]
        if not candidates:
            return None
        candidates.sort(key=lambda x: x.timestamp, reverse=True)
        return candidates[0]
