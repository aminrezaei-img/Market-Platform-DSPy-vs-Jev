"""
Program Registry - DSPy program lineage tracking
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from .base import RegistryEntry, RegistryBase

class ProgramManifest(RegistryEntry):
    id: str  # e.g. query_planner
    version: str
    dspy_signature: str = "DecomposeBankerRequest"
    dspy_module: str = "Predict"  # Predict, ChainOfThought, ReAct
    optimizer: str = "none"  # none, MIPROv2, GEPA
    optimizer_run: Optional[str] = None  # run id
    parent_program: Optional[str] = None  # parent id@version
    training_dataset: Optional[str] = None  # dataset id@version
    metric: str = "control_metric"
    artifact_path: str = ""
    compile_run_id: Optional[str] = None
    optimizer_provenance: Dict[str, Any] = Field(default_factory=dict)
    dspy_version: str = "3.3.1"
    lm_model: str = "mock"
    evidence_type: str = "measured"  # measured, simulated, expected
    owner: str = "platform"
    description: str = ""
    status: str = "active"
    lineage: List[str] = Field(default_factory=list)  # full lineage chain

    def full_lineage(self) -> str:
        return " -> ".join(self.lineage + [self.full_id()])

class ProgramRegistry(RegistryBase[ProgramManifest]):
    def __init__(self, registry_root: str = "registry_store"):
        super().__init__("programs", ProgramManifest, registry_root)

    def get_lineage(self, program_id: str, version: str) -> List[ProgramManifest]:
        """Get full lineage chain for a program"""
        manifest = self.get(program_id, version)
        if not manifest:
            return []

        lineage = []
        current = manifest
        visited = set()

        while current and current.full_id() not in visited:
            lineage.insert(0, current)
            visited.add(current.full_id())
            if current.parent_program:
                try:
                    parent_id, parent_version = current.parent_program.split("@")
                    current = self.get(parent_id, parent_version)
                except:
                    break
            else:
                break

        return lineage

    def get_by_optimizer(self, optimizer: str) -> List[ProgramManifest]:
        return [e for e in self._cache.values() if e.optimizer == optimizer]
