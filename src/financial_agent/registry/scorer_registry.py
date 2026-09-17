"""
Scorer Registry - versioned evaluators
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from .base import RegistryEntry, RegistryBase

class ScorerManifest(RegistryEntry):
    id: str
    version: str
    description: str = ""
    scorer_type: str = "deterministic"  # deterministic, llm_judge, hybrid
    input_contract: Dict[str, Any] = Field(default_factory=dict)
    output_contract: Dict[str, Any] = Field(default_factory=dict)
    calibration_dataset: Optional[str] = None
    owner: str = "platform"
    tags: List[str] = Field(default_factory=list)
    status: str = "active"

class ScorerRegistry(RegistryBase[ScorerManifest]):
    def __init__(self, registry_root: str = "registry_store"):
        super().__init__("scorers", ScorerManifest, registry_root)
