"""
Base registry implementation - file-backed JSON store with in-memory cache.
Enterprise-shaped but local reference implementation.
"""
from typing import Dict, List, Optional, TypeVar, Generic, Any
from pydantic import BaseModel, Field
from pathlib import Path
import json
import hashlib
from datetime import datetime, timezone

T = TypeVar('T', bound=BaseModel)

class RegistryEntry(BaseModel):
    id: str
    version: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    owner: str = "platform"
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def full_id(self) -> str:
        return f"{self.id}@{self.version}"

    def hash(self) -> str:
        content = self.model_dump_json(exclude={"created_at", "updated_at"})
        return hashlib.sha256(content.encode()).hexdigest()[:12]


class RegistryBase(Generic[T]):
    """
    Generic file-backed registry.
    Stores entries as JSON under registry_root/{registry_name}/{id}/{version}.json
    """
    def __init__(self, registry_name: str, entry_class, registry_root: str = "registry_store"):
        self.registry_name = registry_name
        self.entry_class = entry_class
        self.registry_root = Path(registry_root) / registry_name
        self.registry_root.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, T] = {}
        self._load_all()

    def _load_all(self):
        for id_dir in self.registry_root.iterdir():
            if not id_dir.is_dir():
                continue
            for version_file in id_dir.glob("*.json"):
                try:
                    with open(version_file) as f:
                        data = json.load(f)
                    entry = self.entry_class(**data)
                    self._cache[entry.full_id()] = entry
                except Exception as e:
                    print(f"Warning: failed to load {version_file}: {e}")

    def register(self, entry: T) -> T:
        # Validate
        if not isinstance(entry, self.entry_class):
            entry = self.entry_class(**entry.model_dump() if hasattr(entry, 'model_dump') else entry)

        key = entry.full_id()
        entry.updated_at = datetime.now(timezone.utc).isoformat()

        # Persist
        id_dir = self.registry_root / entry.id
        id_dir.mkdir(parents=True, exist_ok=True)
        file_path = id_dir / f"{entry.version}.json"
        with open(file_path, "w") as f:
            json.dump(entry.model_dump(), f, indent=2)

        self._cache[key] = entry
        return entry

    def get(self, id: str, version: Optional[str] = None) -> Optional[T]:
        if version:
            return self._cache.get(f"{id}@{version}")
        # Return latest version if no version specified (lexicographic sort)
        candidates = [e for k, e in self._cache.items() if k.startswith(f"{id}@")]
        if not candidates:
            return None
        # Sort by version string, return latest
        candidates.sort(key=lambda x: x.version, reverse=True)
        return candidates[0]

    def list(self, owner: Optional[str] = None, tag: Optional[str] = None) -> List[T]:
        entries = list(self._cache.values())
        if owner:
            entries = [e for e in entries if e.owner == owner]
        if tag:
            entries = [e for e in entries if tag in e.tags]
        return entries

    def list_versions(self, id: str) -> List[T]:
        return [e for k, e in self._cache.items() if k.startswith(f"{id}@")]

    def delete(self, id: str, version: str) -> bool:
        key = f"{id}@{version}"
        if key in self._cache:
            del self._cache[key]
            file_path = self.registry_root / id / f"{version}.json"
            if file_path.exists():
                file_path.unlink()
            return True
        return False

    def exists(self, id: str, version: Optional[str] = None) -> bool:
        return self.get(id, version) is not None

    def count(self) -> int:
        return len(self._cache)
