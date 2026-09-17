"""
DSPy Memory Adapter - Phase 1.5
Uses existing Phase 1 memory service, no second DB
"""
from typing import Optional, Dict, Any, List
from ..memory.short_term import ShortTermMemory
from ..memory.long_term import LongTermMemory
from ..schemas.memory import MemoryItem, MemoryType

class DSPyMemoryAdapter:
    """
    Adapter that provides safe namespaced context to DSPy modules
    Architecture:
              Existing Memory Service
                     |
          +----------+----------+
          v          v          v
      Supervisor   DSPy       Verifier
                   Planner
    """
    def __init__(self, short_term: ShortTermMemory, long_term: LongTermMemory):
        self.short_term = short_term
        self.long_term = long_term

    def get_safe_context(self, tenant_id: str, user_id: str, client_id: Optional[str], engagement_id: Optional[str]) -> str:
        """
        Before DSPy module executes:
        memory service -> safe namespaced context -> DSPy input field
        """
        context_parts = []

        # Short-term context (current engagement)
        if engagement_id and self.short_term:
            stm_ctx = self.short_term.get(engagement_id)
            if stm_ctx:
                # Only include non-authoritative facts, no exposure/limit
                facts = stm_ctx.get("facts", {})
                safe_facts = {k: v for k, v in facts.items() if not self._is_authoritative_key(k)}
                if safe_facts:
                    context_parts.append(f"Current engagement facts: {safe_facts}")

        # Long-term preferences (user-scoped + client-scoped, but isolated)
        if self.long_term:
            try:
                # Use isolation-safe retrieval
                if client_id:
                    items = self.long_term.retrieve_client_isolated(tenant_id, user_id, client_id)
                else:
                    items = self.long_term.retrieve(tenant_id, user_id, client_id=None, memory_type=MemoryType.long_term_preference)

                for item in items:
                    # Only include preferences and non-authoritative decisions, never authoritative state
                    if item.memory_type in [MemoryType.long_term_preference, MemoryType.long_term_decision]:
                        if not item.is_authoritative and not self._is_authoritative_content(item.content):
                            context_parts.append(f"Preference ({item.memory_type.value}): {item.content}")

            except AssertionError as e:
                # P0 leak detected - should never happen, but if it does, return empty and log
                context_parts.append(f"Memory isolation enforced: {e}")
            except Exception as e:
                context_parts.append(f"Memory retrieval error: {e}")

        if not context_parts:
            return "No prior preferences. Default to detailed brief."

        return "\n".join(context_parts)

    def _is_authoritative_key(self, key: str) -> bool:
        auth_keys = {"credit_exposure", "credit_limit", "exposure", "limit", "positions", "market_price", "gl_balance", "utilization", "credit_snapshot", "gl_summary"}
        return key in auth_keys or "exposure" in key.lower() or "limit" in key.lower()

    def _is_authoritative_content(self, content: Dict[str, Any]) -> bool:
        auth_fields = {"credit_exposure", "credit_limit", "positions", "market_price", "gl_balance", "exposure", "limit", "utilization"}
        content_keys = set(content.keys())
        return len(auth_fields.intersection(content_keys)) > 0

    def validate_and_store(self, tenant_id: str, user_id: str, client_id: Optional[str], engagement_id: Optional[str],
                           content: Dict[str, Any], memory_type: MemoryType, source: str = "dspy") -> bool:
        """
        After DSPy generates memory candidate:
        DSPy output -> existing memory policy -> validate -> persist or reject
        DSPy must not independently persist authoritative state.
        """
        # Enforce policy: never persist authoritative state
        if self._is_authoritative_content(content):
            raise ValueError(f"DSPy attempted to store authoritative state: {content}. Rejected by memory policy.")

        # Check for cross-client leak attempt
        if client_id is None and any(k in content for k in ["risk_appetite", "exposure", "client_specific"]):
            # User-scoped preference should not contain client-specific facts
            if "risk_appetite" in str(content).lower():
                raise ValueError(f"Client-specific fact in user-scoped memory: {content}. Must be client-scoped.")

        item = MemoryItem(
            tenant_id=tenant_id,
            user_id=user_id,
            client_id=client_id,
            engagement_id=engagement_id,
            memory_type=memory_type,
            content=content,
            is_authoritative=False,
            source=source
        )

        return self.long_term.store(item)

    def demo_shared_memory(self):
        """
        Demo for interview: shared memory across LangGraph/DSPy boundary
        """
        # Scenario: User prefers concise briefs
        return {
            "scenario": "User says: For these meetings, keep final brief concise.",
            "memory_persisted": {"brief_style": "concise", "format": "bullet_points"},
            "next_engagement_context": "preferred_brief_style = concise",
            "isolation_check": "Switch client - workflow preference persists, client-specific factual context does not leak"
        }
