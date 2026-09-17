"""
Dataset Registry - prevents accidental leakage
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from .base import RegistryEntry, RegistryBase

class DatasetManifest(RegistryEntry):
    id: str
    version: str
    source: str = "synthetic"  # synthetic, finagent, internal, external
    licence: str = "internal"
    task_count: int = 0
    task_families: List[str] = Field(default_factory=list)
    intended_use: str = "evaluation"  # training, evaluation, both
    training_allowed: bool = False
    evaluation_only: bool = True
    content_hash: str = ""  # renamed from hash to avoid shadowing
    path: str = ""
    description: str = ""
    owner: str = "platform"
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class DatasetRegistry(RegistryBase[DatasetManifest]):
    def __init__(self, registry_root: str = "registry_store"):
        super().__init__("datasets", DatasetManifest, registry_root)

    def get_training_allowed(self) -> List[DatasetManifest]:
        return [e for e in self._cache.values() if e.training_allowed]

    def get_evaluation_only(self) -> List[DatasetManifest]:
        return [e for e in self._cache.values() if e.evaluation_only]

    def check_training_allowed(self, dataset_id: str, version: str) -> bool:
        manifest = self.get(dataset_id, version)
        if not manifest:
            return False
        return manifest.training_allowed
