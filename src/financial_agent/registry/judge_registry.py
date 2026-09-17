"""
Judge Registry - LLM judges with calibration
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from .base import RegistryEntry, RegistryBase

class JudgeCalibration(BaseModel):
    agreement: float = 0.0  # human agreement %
    precision: float = 0.0
    recall: float = 0.0
    cohens_kappa: Optional[float] = None
    validated_on: int = 0  # sample count
    calibration_dataset: str = ""
    last_calibrated: str = ""

class JudgeManifest(RegistryEntry):
    id: str
    version: str
    model: str = "mock-judge-v1"
    prompt: str = ""
    rubric: str = ""
    description: str = ""
    calibration: JudgeCalibration = Field(default_factory=JudgeCalibration)
    owner: str = "platform"
    tags: List[str] = Field(default_factory=list)
    status: str = "active"

class JudgeRegistry(RegistryBase[JudgeManifest]):
    def __init__(self, registry_root: str = "registry_store"):
        super().__init__("judges", JudgeManifest, registry_root)

    def get_calibrated(self, min_agreement: float = 0.8) -> List[JudgeManifest]:
        return [e for e in self._cache.values() if e.calibration.agreement >= min_agreement]
