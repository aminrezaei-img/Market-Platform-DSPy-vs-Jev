"""
Suite Registry - suite != dataset
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from .base import RegistryEntry, RegistryBase

class SuiteManifest(RegistryEntry):
    id: str
    version: str
    datasets: List[str] = Field(default_factory=list)  # dataset_id@version
    metrics: List[str] = Field(default_factory=list)  # metric ids
    slices: List[str] = Field(default_factory=list)  # slice names
    lifecycle_policy: Dict[str, Any] = Field(default_factory=dict)  # p0_max, p1_max
    description: str = ""
    owner: str = "platform"
    tags: List[str] = Field(default_factory=list)
    status: str = "active"

class SuiteRegistry(RegistryBase[SuiteManifest]):
    def __init__(self, registry_root: str = "registry_store"):
        super().__init__("suites", SuiteManifest, registry_root)
