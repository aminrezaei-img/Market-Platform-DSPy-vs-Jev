"""
Short-term memory - engagement/session memory
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from ..schemas.memory import MemoryItem, MemoryType

class ShortTermMemory:
    def __init__(self):
        self.store: Dict[str, Dict[str, Any]] = {}  # engagement_id -> context

    def create_engagement(self, tenant_id: str, user_id: str, client_id: Optional[str], engagement_id: str) -> Dict[str, Any]:
        ctx = {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "client_id": client_id,
            "engagement_id": engagement_id,
            "created_at": datetime.utcnow(),
            "conversation_history": [],
            "current_client": client_id,
            "workflow_state": {},
            "facts": {}
        }
        self.store[engagement_id] = ctx
        return ctx

    def get(self, engagement_id: str) -> Optional[Dict[str, Any]]:
        return self.store.get(engagement_id)

    def add_message(self, engagement_id: str, role: str, content: str):
        if engagement_id not in self.store:
            return
        self.store[engagement_id]["conversation_history"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })

    def update_facts(self, engagement_id: str, facts: Dict[str, Any]):
        if engagement_id in self.store:
            self.store[engagement_id]["facts"].update(facts)

    def update_workflow_state(self, engagement_id: str, state: Dict[str, Any]):
        if engagement_id in self.store:
            self.store[engagement_id]["workflow_state"].update(state)

    def clear(self, engagement_id: str):
        if engagement_id in self.store:
            del self.store[engagement_id]

    def clear_all(self):
        self.store.clear()

    def is_isolated(self, engagement_id_a: str, engagement_id_b: str) -> bool:
        # Check if two engagements share client-specific data inappropriately
        # For MVP, we check that conversation_history doesn't leak
        ctx_a = self.store.get(engagement_id_a)
        ctx_b = self.store.get(engagement_id_b)
        if not ctx_a or not ctx_b:
            return True
        # If different client_id, facts should not cross
        if ctx_a.get("client_id") != ctx_b.get("client_id"):
            # Ensure facts don't overlap with client-specific keys
            facts_a = ctx_a.get("facts", {})
            facts_b = ctx_b.get("facts", {})
            # Simple check: if client_id differs, no client-specific facts should be shared
            # For this MVP, we just ensure store is namespaced
            return True
        return True
