# TRACE_SPEC.md - Structured Trace / Observability

**Status:** FROZEN v1.0

## 1. Purpose
Every execution must expose full operational trace for auditability. No hidden chain-of-thought. Structured operational traces only.

Maps to AgentCore Observability.

## 2. Trace Event Schema
Each execution produces a trace file JSONL with events.

Event types:
- request_received
- request_normalised
- supervisor_decision
- agent_start
- agent_end
- retrieval_query
- retrieval_result
- tool_call
- tool_result
- model_call
- verifier_input
- verifier_output
- synthesiser_input
- final_output
- evaluation_result
- error
- memory_read
- memory_write

Base fields for all events:
{
  trace_id: str (UUID),
  run_id: str,
  event_id: str,
  event_type: str,
  timestamp: ISO8601,
  agent: str | null,
  model_provider: str | null,
  model_name: str | null,
  latency_ms: int | null,
  tenant_id: str,
  user_id: str,
  client_id: str | null,
  engagement_id: str | null
}

Specific payloads:

### supervisor_decision
{
  task_type, answerability, required_specialists, required_tools, parallelisable, risk_level, needs_human_review, confidence, reasoning_summary (not chain-of-thought)
}

### tool_call
{
  tool_name, input, caller_agent, timeout, is_authoritative, is_state_mutating
}

### tool_result
{
  tool_name, status, data (truncated if large), error_code, error_message, provenance {source, authoritative, freshness_timestamp, permitted, retrieved_at}, latency_ms
}

### retrieval_query
{
  query, retriever_type (bm25|dense|hybrid), top_k, filters
}

### retrieval_result
{
  query, results: [{document_id, source, section, text (truncated), score, retriever, metadata, governance}], latency_ms
}

### model_call
{
  prompt_version, input_tokens, output_tokens, latency_ms, estimated_cost, provider, model, structured_output (if any)
}

### verifier_output
{
  supported_claims, total_claims, citation_precision, unsupported_claims, conflicts, critical_failure, recommendation
}

### final_output
{
  brief (truncated for trace), sections_present, warnings, human_review_items, abstentions, conflicts_surfaced
}

## 3. Persistence
- Trace file: runs/{run_id}/trace.jsonl
- Final output: runs/{run_id}/final_output.json
- Evaluation result: runs/{run_id}/eval_result.jsonl (one per task)

No manual editing.

## 4. Operational Metrics Captured
Per run: P50 latency, P95 latency (if multiple model calls), tokens in/out, estimated cost, tool-call count, model-call count, error count

Per model_call: latency, tokens, cost

## 5. No Hidden Reasoning
Do not store full LLM chain-of-thought. Store reasoning_summary max 2 sentences for supervisor. Verifier reasoning must be structured (list of unsupported claims).

## 6. Mapping to AgentCore Observability
Our trace.jsonl fields compatible with OpenTelemetry-like attributes. Document in README.

## 7. Testing
Contract test: every workflow execution must produce trace with at least: request_received, supervisor_decision, at least one agent_start/end, verifier_output, final_output
