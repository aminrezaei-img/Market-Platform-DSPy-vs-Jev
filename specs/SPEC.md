# SPEC.md - Financial Agent Reliability Lab Phase 1

**Status:** FROZEN v1.0
**Date:** 2026-09-15

## 1. Objective
Build one banker-facing workflow (Corporate Pre-Meeting Brief) surrounded by evaluation, tracing, lifecycle gate system.

Platform is product. Workflow exercises platform.

## 2. Primary Workflow
Input: "Prepare pre-meeting brief for Nordic Industrial A/S"
Output sections:
- relationship overview
- current credit exposure
- recent trading activity
- relevant external financial developments
- material risks or inconsistencies
- information that could not be verified
- items requiring human review

Must combine synthetic internal data + external public filings + deterministic tools + LLM synthesis + independent verification.

## 3. Architecture
```
USER REQUEST
  -> REQUEST NORMALISER
  -> SUPERVISOR/ROUTER (task_type, answerability, risk, specialists, tools, parallelisable)
  -> [INTERNAL DATA AGENT] [RESEARCH RAG AGENT] [ANALYSIS AGENT] (parallel where possible)
  -> VERIFIER (mandatory)
  -> SYNTHESISER (cited brief, warnings, abstentions)
  -> FINAL OUTPUT

EVERY COMPONENT EMITS EVENTS -> TRACE/EVAL STORE -> REGRESSION ENGINE -> PASS/BLOCK (Lifecycle Gate)
```

## 4. Agents
1. Supervisor - strict JSON schema, fail-closed
2. Internal Data Agent - typed internal tools only, no guessing
3. Research RAG Agent - external corpus only, preserve provenance
4. Analysis Agent - deterministic calculations via tools
5. Verifier - claim support, citation validity, conflicts, permissions
6. Synthesiser - consumes only verified facts

Why multi-agent:
- Permission isolation (internal vs external)
- Parallelism (internal + external)
- Independent verification
- Evaluatability

Simple tasks may bypass specialists.

## 5. Technology
Python 3.11+, Pydantic, LangGraph, FastAPI optional, Streamlit, SQLite/DuckDB for synthetic, Qdrant or local vector store, BM25, sentence-transformers, pytest, structured JSON logging.

No AWS live dependencies for Phase 1. Interfaces must map to AgentCore:
- local orchestration -> AgentCore Runtime
- tool gateway -> AgentCore Gateway
- memory layer -> AgentCore Memory
- trace system -> AgentCore Observability
- eval harness -> AgentCore Evaluations

InternalDataProvider abstraction:
- Current: SyntheticInternalDataProvider
- Future: DatabricksInternalDataProvider

ExternalResearchProvider abstraction:
- Current: SEC/FinAgent corpus
- Future: LSEG/Bloomberg

## 6. Model Abstraction
All LLM calls via ModelProvider interface:
- generate
- generate_structured
- stream (optional)
- metadata (provider, model, prompt_version, input_tokens, output_tokens, latency, estimated_cost)

Supervisor replaceable via SupervisorProvider for Phase 2 LFM.

## 7. Memory
Short-term: conversation context, current client, engagement, workflow state. Cleared/namespaced by engagement.
Long-term: format preferences, workflow preferences, previous analyst decisions, non-authoritative notes. Must NOT contain authoritative current business state (credit exposure, positions, market prices, GL, limits). Must include tenant_id, user_id, client_id, engagement_id. Cross-client leak = P0 BLOCK.

## 8. Retrieval
Three configs: BM25, dense (sentence-transformers), hybrid (BM25+dense+RRF). Optional cross-encoder rerank after baseline works. Output must preserve provenance with governance metadata: source, authoritative, freshness_timestamp, permitted, provenance, retrieved_at.

## 9. Evaluation Philosophy
Hierarchy:
DATA (correct, current, authoritative, permitted)
 -> RETRIEVAL (right evidence)
 -> TOOL (correct tool)
 -> AGENT (routing)
 -> MULTI-AGENT (coordination)
 -> WORKFLOW (banker task success)
 -> OUTPUT (accurate, faithful, useful)
 -> REGRESSION (degradation)
 -> LIFECYCLE GATE (should progress)

Across all: QUALITY, LATENCY, COST, SECURITY, AUDITABILITY, HUMAN REVIEW

## 10. Non-Goals Phase 1
No LFM fine-tuning, no Tau training, no real Databricks/LSEG/Bloomberg, no production AWS deployment, no C#, no React, no large synthetic customer gen, no autonomous state-mutating financial actions.

## 11. Final Principle
Optimize so every important behaviour can be measured, explained, challenged. Interviewer must be able to inspect any output and answer: where from, what tools, what evidence, what could go wrong, how evaluated, would it ship?
