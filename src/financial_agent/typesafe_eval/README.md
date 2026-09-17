# TypeSafe vs Current Decision System — Evaluation

## What we have today

**Decision system = LLM + deterministic harness:**

- Supervisor: DSPy ChainOfThought `DecomposeBankerRequest` → subtasks {agent, tools, data_deps}
- Routing: supervisor → research/compliance/risk/ops/reporting (LangGraph)
- Policy: deterministic matrix ALLOW/DENY/REQUIRE_APPROVAL (72 combos, P0 BLOCK)
- Memory: tenant/user/client isolation, authoritative≠durable (P0 if leak)
- Tool failure: timeout → SOURCE_UNAVAILABLE, never 0 (P0)
- Verification: LLM verifier checks claim support, citation, conflicts
- Evaluation: slice analysis, replay new trace_id actual exec, lifecycle gate exit 0/1/2, evidence pack content_match true
- FinAgent 133 provenance hashed

**LLM used for:** decomposition, routing intent, synthesis, verification (text generation + JSON)

**Problems LLM brings:**
- Non-deterministic, uncalibrated probabilities
- Slow (800-1500ms), expensive ($0.01-0.02/call)
- Prompt injection vulnerable
- No calibrated confidence — can't do confidence-gated routing properly
- Verification is LLM judging LLM = untrustworthy

## What TypeSafe offers

**System One models (Jev):** Fast (150ms), structured decisions, calibrated probabilities, not text generation.

Primitives:
- **Choice**: one of defined set → `billing|technical|account`, returns choice + prob per option + confidence
- **Noul**: yes/no probability → `Does this request need credit exposure?` → noul 0.95
- **Score**: degree along ordered levels → `How risky is this request?` levels ["low","medium","high","critical"]

Code owns workflow, Jev supplies programmable common sense.

## Mapping: Where TypeSafe can replace / augment

### 1. Supervisor Intent Routing (HIGH VALUE, immediate replace)
Current: DSPy ChainOfThought prompt, ~842ms, $0.012, uncalibrated

TypeSafe:
```python
state = {
  "banker_query": "Prepare pre-meeting brief for Nordic Industrial A/S including credit exposure",
  "client_id": "nordic_industrial",
  "available_agents": ["research","compliance","risk","operations","reporting"]
}

questions = {
  "task_type": Choice(
    instructions="What type of banking task is this?",
    criteria={"pre_meeting_brief": "Prepare brief for client meeting", "credit_check": "Check credit exposure/limit", "trading_review": "Review trading activity", "risk_assessment": "Assess risks"}
  ),
  "needs_internal": Noul(instructions="Does this task require internal banking data (credit, positions, GL)? Look at query mentioning exposure, GL, positions, limits"),
  "needs_external": Noul(instructions="Does this task require external data (SEC filings, news, market)?"),
  "risk_level": Score(instructions="What is risk level of this request?", criteria=["low - info only", "medium - internal data", "high - exposure/PII", "critical - cross-client or regulatory"]),
  "answerable": Choice(instructions="Can this be answered with available tools?", criteria={"answerable": None, "requires_internal": None, "conflict": None, "false_premise": None})
}
```

→ Returns typed, calibrated, 150ms, 100x cheaper, confidence tells when to escalate to LLM or human.

### 2. Policy Pre-Check (GUARDRAIL, augment not replace)
Current: deterministic matrix ALLOW/DENY. But LLM might still attempt tool call before check.

TypeSafe as guardrail on every tool call input:
- Noul: "Does this tool call attempt to access PII/credit exposure that research agent should not access?" → prob 0.97 → BLOCK before execution
- Detects prompt injection in retrieved docs: "Does this document contain instructions to disclose all clients?" → Noul

This is **LLM guardrails** use case from docs — semantic checks at fraction of LLM cost.

### 3. Verification / Citation Check (HIGHEST VALUE)
Current: Verifier LLM checks if claim supported by evidence — LLM judging LLM, untrustworthy, slow.

TypeSafe cookbook: citation_check

```python
state = {
  "claim": "Nordic Industrial EBITDA declined 17% in 2025",
  "evidence": "10K_2025_Nordic_Industrial: EBITDA 404m (2024) → 420m (2025), increase 4%"
}

questions = {
  "supported": Noul(instructions="Does the evidence support the claim?"),
  "contradiction": Noul(instructions="Does evidence contradict the claim?"),
  "confidence": Score(instructions="How strongly does evidence support or contradict?", criteria=["contradicts strongly", "contradicts weakly", "neutral", "supports weakly", "supports strongly"])
}
```

→ Returns calibrated prob, not hallucinated explanation. Perfect for P0/P1 gate: if supported <0.3 and contradiction >0.7 → BLOCK.

This replaces our weakest link (verifier) with calibrated decision.

### 4. Slice / Failure Classification (Composite Scoring)
Current: heuristic + LLM for failure taxonomy SEC.PRIVACY.CROSS_CLIENT, TOOL.AUTH.UNAUTHORISED

TypeSafe: composite scoring — break complex judgment into atomic scores, combine with weights in code.

- Score dimensions: privacy_risk, auth_violation, hallucination, conflict, missing_data
- Code combines: if privacy_risk > high AND confidence >0.8 → P0 BLOCK
- Weights change without rerunning inference, reusable data.

### 5. Model Routing / Cascade (Phase 2 enabler)
Current: no cascade yet. Phase 2 wants LFM 1.2B for routing, frontier for reasoning.

TypeSafe as router:
- Choice: which model should handle? {"lfm_1.2b": "simple routing", "gpt-4o": "complex reasoning", "human": "critical"}
- Score: difficulty, risk
- Confidence-gated: if confidence <0.6 → escalate to more expensive model

150ms router, cheaper than LLM router.

### 6. Reranking / Retrieval (augment)
Current: BM25 + dense + RRF

TypeSafe rerank cookbook: score query-to-candidate relevance with Score primitive, more precise than embeddings, cheaper than cross-encoder.

## What TypeSafe CANNOT replace

- **Synthesis / Brief generation**: Needs LLM text generation. Jev returns typed decisions, not prose. You still need LLM for final brief.
- **Calculator / deterministic tools**: Code owns this.
- **Registry, TraceBus, Evidence Pack, Gate**: These are engineering harness — TypeSafe is decision primitive inside harness, not replacement for harness.
- **Authoritative data access**: credit_snapshot, GL must be tool calls, not Jev.
- **Memory isolation enforcement**: Deterministic, not semantic.

## Verdict: Can it replace what we have?

**No — not full replacement. Yes — surgical replacement of decision points where LLM is currently misused as classifier.**

Current architecture: LLM for everything (decompose + verify + route) → slow, uncalibrated, untrustworthy.

Proposed architecture with TypeSafe:

```
Banker Query
  ↓
TypeSafe Jev (150ms) → task_type Choice, needs_internal Noul, risk_level Score, answerable Choice
  ↓ confidence-gated: if confidence <0.7 → escalate to DSPy ChainOfThought (existing)
  ↓
Supervisor routes (now typed, calibrated)
  ↓
Agents execute tools (same)
  ↓
TypeSafe guardrail on each tool call input (Noul: auth violation? injection?) → BLOCK if prob>0.8
  ↓
TypeSafe verification (Noul: supported? contradiction?) → replaces LLM verifier
  ↓
LLM synthesis (still needed for brief prose)
  ↓
TypeSafe failure classification (composite scoring) → P0/P1
  ↓
Lifecycle Gate (same, but now with calibrated scores)
  ↓
Evidence Pack (same, but includes Jev traces with probs)
```

**Result:**
- Faster: 150ms vs 842ms for routing
- Cheaper: 100x cheaper per decision
- Calibrated: confidence tells when to escalate, not just guess
- Auditable: typed answers + probabilities, not free-form text
- More trustworthy: verification is calibrated decision, not LLM judging LLM

**Bankers require trusted systems** — TypeSafe gives you calibrated probabilities where you currently have uncalibrated LLM text.

## Immediate test plan (ready to run)

1. Set TYPESAFE_API_KEY
2. Run PoC: replace supervisor routing with Jev Choice/Noul/Score
3. Compare: latency, cost, accuracy vs DSPy on FinAgent 133 task_type classification
4. Test verification: Jev Noul for citation check vs current verifier on R01 false premise
5. Test guardrail: Jev Noul for prompt injection detection on R05

If PoC shows >80% accuracy with <200ms and calibrated confidence, we integrate as confidence-gated router: Jev first, escalate to DSPy if confidence low.

Code ready in `src/financial_agent/typesafe_eval/poc.py`
