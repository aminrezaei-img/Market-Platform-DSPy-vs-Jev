# TOOL_SPEC.md - Tool Gateway

**Status:** FROZEN v1.0

## 1. Principle
All internal/external access via typed tools. No direct DB access from agents. Tool Gateway enforces authz, logging, timeout, error semantics.

## 2. Minimum Tools

### Internal (authoritative)
- client_lookup: lookup client by name/id
- relationship_summary: relationship overview, coverage banker, tenure, products
- credit_snapshot: current credit exposure, limits, utilization
- trade_activity: recent trading activity
- gl_summary: GL summary / balances

### Utility / Deterministic
- calculator: deterministic calculation (add, subtract, multiply, divide, percent change)
- table_extractor: extract numeric table from text
- document_search: search external corpus (RAG)
- document_fetch: fetch document by id

Future: DatabricksInternalDataProvider, LSEG/Bloomberg provider - but do not name mock tools lseg/bloomberg unless real integration.

## 3. Tool Definition Contract
Every tool must define:
{
  name: str,
  description: str,
  input_schema: JSON schema / Pydantic,
  output_schema: JSON schema / Pydantic,
  authorisation_scope: ["internal_read", "external_read", "deterministic", ...],
  timeout_seconds: int,
  error_behaviour: "return_error_object" | "raise",
  is_authoritative: bool,
  is_state_mutating: bool
}

Example:
{
  name: "credit_snapshot",
  is_authoritative: true,
  is_state_mutating: false,
  authorisation_scope: ["internal_read", "credit_read"],
  timeout_seconds: 5
}

## 4. Tool Failure Semantics (Mandatory)
Tool failure must never be converted into substantive business conclusion.

Example:
credit_snapshot timeout -> must produce SOURCE_UNAVAILABLE, not credit exposure = 0

Error object schema:
{
  status: "success" | "not_found" | "timeout" | "auth_error" | "conflict" | "source_unavailable",
  data: ... | null,
  error_code: str | null,
  error_message: str | null,
  provenance: {source, retrieved_at, authoritative, freshness_timestamp, permitted}
}

Agents must surface error to verifier, not invent.

Tests required:
- timeout -> SOURCE_UNAVAILABLE
- not_found -> NOT_FOUND
- conflict detection preserved
- no invented values on failure

## 5. Authorisation
Tool Gateway checks: role (internal_data_agent can call internal_read, research_agent cannot). Research agent attempting internal tool -> auth_error -> logged -> P0 if bypassed.

All tool calls logged with: tool name, input, output status, latency, caller agent, tenant_id, client_id.

## 6. Governance Metadata
Every tool result must include provenance:
{
  source: "synthetic_crm" | "synthetic_credit" | "sec_filing" | "calculator",
  authoritative: bool,
  freshness_timestamp: ISO8601,
  permitted: bool,
  provenance: "CRM v1 fixture",
  retrieved_at: ISO8601
}

## 7. State Mutation
Phase 1: All tools read-only (is_state_mutating=false). No autonomous state-mutating financial actions. If future mutation needed, require human review flag.

## 8. Versioning
Tool configs versioned in configs/. Tool gateway version recorded in traces and eval runs.
