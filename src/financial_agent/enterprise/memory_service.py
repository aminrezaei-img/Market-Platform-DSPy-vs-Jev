"""
Shared Memory Service - enterprise-shaped contract
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid

class MemoryScope(str, Enum):
    session = "session"
    workflow = "workflow"
    durable_preference = "durable_preference"
    derived_note = "derived_note"

class MemoryNamespace(BaseModel):
    tenant: str = "tenant_danske_mock"
    user: str = "user_banker_001"
    client: Optional[str] = None
    engagement: Optional[str] = None
    agent: Optional[str] = None

class EnterpriseMemoryRecord(BaseModel):
    memory_id: str = Field(default_factory=lambda: f"mem_{uuid.uuid4().hex[:8]}")
    scope: MemoryScope = MemoryScope.session
    namespace: MemoryNamespace = Field(default_factory=MemoryNamespace)
    source: str = "user"
    content: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: Optional[str] = None
    authoritative: bool = False  # must always be False for business state
    is_authoritative: bool = False  # alias for backward compat
    tags: List[str] = Field(default_factory=list)

    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        try:
            exp = datetime.fromisoformat(self.expires_at)
            return datetime.now(timezone.utc) > exp
        except:
            return False

class EnterpriseMemoryService:
    """
    Enterprise-shaped memory service per spec section 10
    Namespaces: tenant, user, client, engagement, agent
    Memory classes: session, workflow, durable preference, derived note
    Every record carries scope, source, created_at, expires_at, authoritative=false
    Authoritative business state still never comes from memory.
    """
    def __init__(self):
        self._store: Dict[str, EnterpriseMemoryRecord] = {}
        self._authoritative_blocklist = [
            "credit_exposure", "position", "market_price", "gl_balance",
            "limit", "exposure", "balance", "price"
        ]

    def _check_authoritative(self, content: Dict[str, Any]) -> bool:
        """Check if content tries to store authoritative business state"""
        authoritative_keys = ["credit_exposure", "positions", "market_prices", "gl_balances", "limits", "market_price", "gl_balance", "position"]
        for key in content.keys():
            if key.lower() in [k.lower() for k in authoritative_keys]:
                return True
            # Also check if key contains authoritative pattern
            lower_key = key.lower()
            if "credit_exposure" in lower_key or "market_price" in lower_key or "gl_balance" in lower_key:
                return True
        return False

    def store(self, record: EnterpriseMemoryRecord) -> EnterpriseMemoryRecord:
        if record.authoritative or record.is_authoritative:
            raise ValueError("Authoritative business state must never be stored in memory")

        if self._check_authoritative(record.content):
            raise ValueError(f"Authoritative field in {list(record.content.keys())} cannot be stored in memory")

        self._store[record.memory_id] = record
        return record

    def store_simple(
        self,
        tenant: str,
        user: str,
        client: Optional[str],
        engagement: Optional[str],
        agent: Optional[str],
        content: Dict[str, Any],
        scope: MemoryScope = MemoryScope.durable_preference,
        source: str = "user",
        expires_in_days: Optional[int] = None
    ) -> EnterpriseMemoryRecord:
        namespace = MemoryNamespace(
            tenant=tenant,
            user=user,
            client=client,
            engagement=engagement,
            agent=agent
        )

        expires_at = None
        if expires_in_days:
            expires_at = (datetime.now(timezone.utc) + timedelta(days=expires_in_days)).isoformat()

        record = EnterpriseMemoryRecord(
            scope=scope,
            namespace=namespace,
            source=source,
            content=content,
            expires_at=expires_at,
            authoritative=False,
            is_authoritative=False
        )

        return self.store(record)

    def retrieve(
        self,
        tenant: str,
        user: str,
        client: Optional[str] = None,
        engagement: Optional[str] = None,
        agent: Optional[str] = None,
        scope: Optional[MemoryScope] = None
    ) -> List[EnterpriseMemoryRecord]:
        results = []

        for record in self._store.values():
            if record.is_expired():
                continue

            ns = record.namespace
            if ns.tenant != tenant:
                continue
            if ns.user != user:
                continue

            # Client isolation: if requesting for specific client, don't leak other clients
            if client:
                if ns.client and ns.client != client:
                    # This record is for different client, skip if it's client-specific
                    # But allow global preferences (client=None)
                    continue

            if engagement and ns.engagement and ns.engagement != engagement:
                continue

            if scope and record.scope != scope:
                continue

            results.append(record)

        return results

    def get_safe_context(
        self,
        tenant: str,
        user: str,
        client: Optional[str],
        engagement: Optional[str]
    ) -> str:
        """Get safe context string for prompt, with isolation"""
        records = self.retrieve(tenant, user, client, engagement)

        if not records:
            return "No prior preferences"

        # Build context, ensuring no cross-client leak
        context_parts = []
        for r in records:
            # Skip if this is client-specific for different client
            if r.namespace.client and client and r.namespace.client != client:
                continue
            context_parts.append(f"{r.scope.value}: {r.content}")

        return "\n".join(context_parts) if context_parts else "No prior preferences"

    def count(self) -> int:
        return len(self._store)

    def clear(self):
        self._store.clear()
