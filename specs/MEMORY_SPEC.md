# MEMORY_SPEC.md - Memory Architecture

**Status:** FROZEN v1.0

## 1. Two Classes

### Short-term (Session/Engagement Memory)
Contains:
- conversation context
- current client
- current engagement
- current workflow state

Implementation: LangGraph checkpoint / in-memory dict keyed by engagement_id
Cleared or namespaced by engagement. TTL per engagement.

Must include: tenant_id, user_id, client_id, engagement_id, timestamp

### Long-term (Durable Workflow Memory)
May contain:
- format preferences (brief format, citation style)
- workflow preferences
- previous analyst decisions (non-authoritative)
- non-authoritative engagement notes

Must NOT contain authoritative current business state:
- credit exposure
- positions
- market prices
- GL balances
- limits

Those must be re-fetched via tools.

Storage: SQLite/DuckDB table with embedding for retrieval (optional). Keyed by tenant_id, user_id, client_id, engagement_id.

## 2. Namespacing (Mandatory)
Every stored memory item:
{
  tenant_id: str,
  user_id: str,
  client_id: str | null,
  engagement_id: str | null,
  memory_type: "short_term" | "long_term_preference" | "long_term_decision",
  content: ...,
  created_at: ISO,
  is_authoritative: bool (must be false for long-term),
  source: str
}

## 3. Isolation Rules
- Query for Client B must never return Client A specific facts (risk appetite, exposure, etc.)
- Long-term preferences may be user-scoped but client-specific facts must be client-scoped.
- Cross-client contamination = P0 failure, BLOCK.

Test R06:
- Store memory for Client A: risk appetite conservative, exposure 800m
- Start session for Client B with same user_id but different client_id
- Assert no Client A facts returned
- Assert preference (e.g., brief format = bullet) may be returned if user-scoped

## 4. Authoritative State Policy
- Never serve authoritative fields from long-term memory.
- If long-term contains "credit exposure 800m from 2025-01-01", it must be ignored and re-fetched.
- Verifier should check if synthesiser used stale memory for authoritative field.

## 5. Implementation Notes
- Short-term: dict in LangGraph state
- Long-term: simple SQLite table `durable_memory` with columns above + embedding blob optional
- Retrieval: filter by tenant_id, user_id, then client_id if provided
- No vector search needed for MVP but structure allows.

## 6. Phase 2 Extensibility
Memory interfaces must allow future AgentCore Memory mapping:
- short-term -> AgentCore short-term interaction memory
- long-term -> AgentCore extracted long-term memory

No change to agent logic needed when provider swapped.
