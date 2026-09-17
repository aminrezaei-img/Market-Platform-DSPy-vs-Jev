"""
Model Registry - lightweight model tracking
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from .base import RegistryEntry, RegistryBase

class ModelManifest(RegistryEntry):
    id: str  # e.g. anthropic.claude-x
    version: str
    provider: str  # anthropic, openai, local, mock
    model_id: str  # actual model id
    model_family: str = "unknown"
    context_window: int = 8192
    deployment: str = "api"  # api, local, bedrock
    cost_metadata: Dict[str, float] = Field(default_factory=dict)  # input_per_1k, output_per_1k
    capabilities: List[str] = Field(default_factory=list)  # reasoning, tool_use, vision
    status: str = "active"  # active, deprecated, blocked
    owner: str = "platform"
    description: str = ""

class ModelRegistry(RegistryBase[ModelManifest]):
    def __init__(self, registry_root: str = "registry_store"):
        super().__init__("models", ModelManifest, registry_root)

    def get_by_provider(self, provider: str) -> List[ModelManifest]:
        return [e for e in self._cache.values() if e.provider == provider]

    def get_active(self) -> List[ModelManifest]:
        return [e for e in self._cache.values() if e.status == "active"]
