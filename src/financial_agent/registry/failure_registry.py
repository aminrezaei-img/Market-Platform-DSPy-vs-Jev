"""
Failure Registry - canonical failure taxonomy
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from .base import RegistryEntry, RegistryBase

class FailureManifest(RegistryEntry):
    id: str  # e.g. SEC.PRIVACY.CROSS_CLIENT
    version: str = "1"
    description: str = ""
    category: str = ""  # privacy, tool, data, retrieval, agent, output, hitl, ops
    severity: str = "P2"  # P0, P1, P2, P3, P4
    owner: str = "platform"
    blocking_policy: str = "BLOCK"  # BLOCK, WARNING, INFO
    detection_method: str = ""  # how to detect
    remediation: str = ""
    tags: List[str] = Field(default_factory=list)

class FailureRegistry(RegistryBase[FailureManifest]):
    def __init__(self, registry_root: str = "registry_store"):
        super().__init__("failures", FailureManifest, registry_root)

    def get_by_severity(self, severity: str) -> List[FailureManifest]:
        return [e for e in self._cache.values() if e.severity == severity]

    def get_blocking(self) -> List[FailureManifest]:
        return [e for e in self._cache.values() if e.blocking_policy == "BLOCK"]

    def get_p0(self) -> List[FailureManifest]:
        return self.get_by_severity("P0")

    def get_p1(self) -> List[FailureManifest]:
        return self.get_by_severity("P1")
