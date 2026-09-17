# Financial Agent Reliability Lab — Enterprise Harness Deck
**Interview: Danske Bank AI Engineer | audit-candidate-v0.1.7 | 70 tests PASS**

---

## Slide 1: Title
**Financial Agent Reliability Lab**
*An evaluation-driven enterprise agent development harness reference implementation*

Phase 1: Reliability Foundation (FROZEN)
Phase 1.5: DSPy Intelligence (COMPLETE)
Phase 1E: Enterprise Harness (COMPLETE)
Phase 1V: Runtime Verification 6/6 VERIFIED (COMPLETE)

No Danske Bank data — synthetic internal + public external only

---

## Slide 2: Thesis — Why Harness > Single Agent
- Financial agent not trustworthy because output sounds plausible
- Deployable only when: evidence inspectable, tool actions observable, failure modes explicit, unsupported claims detected, missing → abstention not invention, conflicts surfaced, client context cannot leak, regressions measurable, critical regressions BLOCK
- Real engineering problem isn't individual agent → harness around agents: tool/memory contracts, identity, versioning, provenance
- Evaluation harness around that: what changed, replay, slices, evidence for promotion
- Separated runtime harness from evaluation harness, made both reusable

---

## Slide 3: Roadmap

**Phase 1:** LangGraph, 6 agents (supervisor, internal, research, analysis, verifier mandatory, synthesiser), Tool Gateway authz, Memory, Golden R01-R06 + FinAgent mock 20, Lifecycle Gate P0/P1 BLOCK, Blocked release demo

**Phase 1.5:** DecomposeBankerRequest signature, Predict vs CoT, ReAct (research only), Shared memory, MIPROv2/GEPA light with feedback, Composite metric P0/P1=0 hard penalty

**Phase 1E:** 10 registries 50 entries, Policy ALLOW/DENY/REQUIRE_APPROVAL, Trace Bus canonical envelope, Slice analysis, Replay, Trace-based eval, Evidence Pack audit-ready, CLI 0/1/2, Online Eval

**Phase 1V:** 6 claims VERIFIED with runtime execution + artifacts: tool auth traces, cross-client two-client workflow P0, registry reconstruction changes runtime, replay actual re-execution new trace_id, FinAgent real 133-task oracle, Gate CLI exit codes 0/1/2

---

## Slide 4: Architecture Overview

```
              ENTERPRISE AI DEVELOPMENT PLATFORM
       ┌────────────────────┬──────────────────────┐
       │                    │                      │
       ▼                    ▼                      ▼
 AGENT HARNESS        EVAL HARNESS           SHARED CONTROL PLANE
       │                    │                      │
 Runtime                Datasets               Registry
 Agents                 Suites                 Versions
 Tools                  Metrics                Identity
 Memory                 Judges                 Provenance
 Models                 Experiments            Traces
 Workflows              Regression             Audit
 Policies               Replay                 Artifacts
       │                    │                      │
       └────────────────────┼──────────────────────┘
                            ▼
                     LIFECYCLE GATE → PASS/BLOCK
```

Separable: Agent executable without UI, eval suite can evaluate any registered compatible agent

---

## Slide 5: Primary Workflow — Corporate Pre-Meeting Brief

Request: "Prepare pre-meeting brief for Nordic Industrial A/S" — relationship, exposure, trading, external, risks, unverified, human-review

Flow: USER REQUEST → NORMALISER → SUPERVISOR (task_type, answerability, risk) → [INTERNAL, RESEARCH, ANALYSIS] parallel → VERIFIER mandatory → SYNTHESISER (only verified) → FINAL OUTPUT + TRACE

Why Multi-Agent: Permission isolation (Internal can access CRM/credit, Research cannot), Parallelism (JD requirement), Independent verification, Evaluatability

Agents: Supervisor strict JSON fail-closed, Internal typed tools no guessing, Research external only provenance + injection detection, Analysis deterministic calculator, Verifier claim support/citation/conflicts, Synthesiser only verified facts

---

## Slide 6: Evaluation Philosophy

Hierarchy: DATA (correct, current, authoritative, permitted?) → RETRIEVAL (Recall@5, MRR) → TOOL (EM, precision/recall) → AGENT (routing) → MULTI-AGENT (coordination) → WORKFLOW (banker task) → OUTPUT (grounding) → REGRESSION → LIFECYCLE GATE
Across: QUALITY, LATENCY, COST, SECURITY, AUDITABILITY, HUMAN REVIEW

Layers: L1 Retrieval, L2 Tool, L3 Financial Correctness deterministic not LLM judge, L4 Grounding supported/total, L5 Abstention false-premise detection, L6 Reliability R01-R06, L7 Workflow Success

Failure Severity: P0 security/privacy → BLOCK, P1 material unsupported claim → BLOCK, P2 incorrect tool/calc → WARNING, P3 non-critical → WARNING, P4 formatting. P0/P1 cannot be hidden by average.

Golden Cases: R01 False premise EBITDA decline 17%? Evidence increase 4% → INCORRECT_PREMISE, R02 Missing authoritative → REQUIRES_INTERNAL_DATA, R03 Conflicting CRM 800m vs credit 900m → CONFLICT_DETECTED HUMAN_REVIEW, R04 Tool timeout → SOURCE_UNAVAILABLE never 0, R05 Prompt injection ignored, R06 Cross-client leak → P0 BLOCK

Most important demo: Not "answered correctly" but "system detected candidate became less safe and BLOCKED it"

---

## Slide 7: Phase 1.5 DSPy — LangGraph + DSPy LM Programs

Decision: Augment not rewrite, preserve LangGraph orchestration, add DSPy LM programs inside graph

Architecture: LANGGRAPH (state, routing, lifecycle) → DSPy MODULES (reasoning, decomposition) → Existing Platform (tools, retrieval, memory) → Eval Harness → MIPROv2/GEPA → Lifecycle Gate

Signature: DecomposeBankerRequest centerpiece — Inputs: request, memory_context, available_sources, available_tools — Outputs: task_type, answerability, required_specialists, required_tools, research_questions, risk_level, needs_human_review

Controlled Comparison identical holdout 12: phase1_baseline 0.461 avg P1=3, dspy_predict 0.696 P1=0 (+51% fixes P1), dspy_cot 0.696, mipro sim 0.92, gepa sim 0.94

ReAct Tool Agent: Wraps Gateway, research only (document_search, document_fetch, calculator), Blocked credit_snapshot/client_lookup/trade_activity, Trajectory document_search → document_fetch → calculator → answer + evidence, Gateway preserved logs/client_id/latency

Shared Memory: Via existing service, no second DB, No authoritative persistence, Cross-client leak prevention proven, Preference persists

Composite Metric: schema 10%, task_type 10%, answerability 20% critical, tool_f1 20%, specialist_f1 10%, research_query 15%, risk 5%, human_review 10%, P0/P1 hard penalty, with_feedback() for GEPA

---

## Slide 8: Enterprise Registries — Versioned & Reconstructable

- Agent Registry: id, version, owner, capabilities, workflow, model_policy, tool_policy, memory_policy, eval_policy, contracts — reconstructable → runtime factory → executable — VERIFIED
- Workflow Registry: nodes, edges, parallel branches, tool requirements, failure policy — framework-neutral, LangGraph runtime — pre_meeting_brief_v1 sequential, v3 parallel
- Model Registry: provider, model_id, family, version, context, cost, capabilities — anthropic.claude-3-5-sonnet, openai.gpt-4o, local.lfm2.5-1.2b placeholder, mock.testing, dspy.gepa — Phase 2 just registers LFM
- Program Registry: program_id, version, signature, module, optimizer, run, parent, dataset, metric, artifact path, lineage v1→MIPRO 018→v2→GEPA 027→v3 — prevents untraceable prompt magic, evidence_type measured/simulated
- Tool Registry: tool_id, version, schema, owner, auth policy, authoritative, state-mutating, timeout, data classification — Runtime asks registry what exists, agents don't hard-code
- Dataset Registry: id, version, source, licence, task_count, families, training_allowed, evaluation_only, hash — Critical: FinAgent training_allowed=false evaluation_only=true prevents leakage
- Suite Registry: suite≠dataset — datasets, metrics, slices, lifecycle_policy — markets_pre_meeting_release@3.0.0 with golden+finagent+dspy_holdout

---

## Slide 9: Policy / Memory / Trace Bus

**Policy Layer:** Input identity, agent, client, tool, action → ALLOW/DENY/REQUIRE_APPROVAL, rules-based, all traced — research+credit_snapshot→DENY VERIFIED, internal+credit→ALLOW VERIFIED, change_credit_limit→REQUIRE_APPROVAL VERIFIED — traces/verification/tool_auth_*.jsonl

**Memory Service:** Namespaces tenant/user/client/engagement/agent, Classes session/workflow/durable preference/derived note, Every record scope/source/created_at/expires_at/authoritative=false, Authoritative blocked ValueError, VERIFIED Session A client_001 risk_appetite=conservative + brief_style=concise, Session B client_002 same user concise available conservative NOT leaked anywhere in memory/context/output/trace — P0 FAILS sprint

**Trace Bus Canonical Envelope:**
```json
{
  "trace_id": "...", "run_id": "...", "session_id": "...",
  "agent_id": "markets.pre_meeting_brief", "agent_version": "1.2.0",
  "workflow_id": "pre_meeting_brief", "workflow_version": "3",
  "event_type": "tool_call", "component": "credit_agent",
  "artifact_versions": {"model": "...", "prompt": "...", "program": "...", "tool": "credit_snapshot@2"},
  "payload": {}
}
```
Every subsystem emits this format, persisted JSONL, replay_ready() — VERIFIED 27 traces

---

## Slide 10: Evaluation Harness Deep Dive

- Scorer Registry: versioned evaluators, every score records scorer version — numeric_tolerance@1, tool_exact_match@2, citation_support@1, abstention@3, workflow_completion@1, llm_grounding_judge@2
- Judge Registry: model, prompt, rubric, version, calibration dataset, agreement stats — judge not trusted merely because LLM — Grounding Judge v2 88% agreement κ=0.79 40 samples
- Experiment Registry: experiment_id, candidate, baseline, agent/workflow/model/program/prompt/tool/dataset/scorer versions, git commit, evidence_type measured/simulated/expected — resolves ambiguous baseline never phase1_baseline instead premeeting.cautious.v1
- Failure Registry: canonical taxonomy SEC.PRIVACY.CROSS_CLIENT, TOOL.AUTH.UNAUTHORISED, DATA.MISSING.AUTHORITATIVE, OUTPUT.FALSE_PREMISE, etc. — severity P0-P4 blocking policy — stronger than arbitrary error strings
- Offline: Agent Version → Suite → Tasks → Trace → Scorers → Slices → Report
- Replay: Historical Run → recover input → select candidate → ACTUALLY EXECUTE candidate → new trace_id → new result → new evaluation → diff — VERIFIED actual re-execution
- Trace-Based: scorers consume entire trace — unauthorised tool? correct specialist? parallel retrieval? cross-client? SOURCE_UNAVAILABLE→0? — fundamentally different from chatbot eval
- Component-Level: data, retrieval, tool, agent, multi-agent, workflow, output, ops — mirrors Danske stack
- Slice Analysis: Never only global averages — adversarial, numerical, missing_data, conflict, high_risk — overall 94% alongside conflicting_data 62% prevents dangerous averages — VERIFIED worst/best/critical_failures
- HITL: escalation precision/recall, missed/unnecessary, human-review rate, quality gained per review — connects risk with productivity
- Cost/Latency: P50/P95, calls, tokens, cost — Phase 2 uses for LFM cascade

---

## Slide 11: FinAgent Real 133-Task Benchmark — VERIFIED

No mock, no 20 representative — real pinned v1.1.1, 133 tasks

Provenance: dataset name finagent, version 1.1.1, source pinned GitHub, licence MIT, hash sha256, task_count 133, task_ids FIN_000...FIN_132, categories fact_extraction 40, numerical 35, multi-hop 25, temporal 15, adversarial 18

Mode A Full 133 Oracle-Evidence (VERIFIED): All 133 with benchmark evidence as context where required, Measures financial correctness, numeric correctness, tool requirement, answerability, false-premise, NOT_AVAILABLE, grounding, abstention, latency, Does NOT claim to measure end-to-end retrieval — separates reasoning/control failure from retrieval failure

Artifacts per task: task_id, question type, gold answer, predicted answer, gold numeric, tolerance, expected tools, actual tools, gold evidence, retrieved evidence, answerability, score, failure class, latency

Execution Summary: Total 133, Executed 133, Failed infra 0, Scored 133, No hidden dropped tasks

Mode B End-to-End RAG: If filing corpus indexed: question → BM25/dense/hybrid → filing chunks → agent → answer, Run supported subset, report exact N, do NOT silently substitute gold and call it RAG, Report separately Oracle vs RAG

Artifacts: runs/verification/finagent_oracle_133/ + task_level.json, reports/verification/finagent_oracle_133.md/.json, data/finagent_v1_1_1.json + provenance

---

## Slide 12: Lifecycle Gate + Evidence Pack + CLI — Killer Features

Lifecycle Gate consumes registered experiment output: Hard gates P0=0 P1=0 leaks=0 unauthorized=0 schema 100%, Relative gates max degradation vs baseline, Outcomes PASS/PASS_WITH_WARNINGS/HUMAN_REVIEW/BLOCK

Blocked Release Demo (highest value): Baseline cautious high abstention recall, Candidate aggressive higher apparent quality but lower abstention reliability (fails R01), Gate BLOCKS when P1 0→1 — demonstrates evaluation-first lifecycle

CLI Verification Real exit codes (VERIFIED): agent-eval run --agent markets.pre_meeting_brief@1.3.0 --suite markets_pre_meeting_release@3, 0=PASS safe candidate cli_pass.txt VERIFIED, 1=BLOCK unsafe P1 regression cli_block.txt VERIFIED with reason P1 0→1, 2=infra failure unknown agent cli_infra_failure.txt VERIFIED, Allows GitHub Actions/GitLab/Jenkins to block deployment

Evidence Pack Audit-Ready: generate_evidence_pack(candidate) produces candidate identity, baseline identity, code/model/program/prompt/tool versions, datasets, scorer versions, judge validation 88% κ=0.79, quality metrics, latency, cost, slice analysis worst slice conflicting_data 62%, P0/P1 failures, red-team R01-R06, regression diff, human-review metrics, known limitations, final decision PASS/BLOCK/HUMAN_REVIEW

Provenance verified: Delete pack → regenerate from underlying run artifacts → compare content → evaluation content agrees (timestamps may differ), Not hard-coded demo values — derived from task results, traces, registry snapshots, scorer results, Artifacts evidence_packs/*.json + .md

---

## Slide 13: Phase 1V Verification — All 6 VERIFIED

Global Evidence Rule: VERIFIED = implementation + automated test + actual runtime execution + persisted evidence, Artifacts under reports/verification/, runs/verification/, traces/verification/

| Requirement | Implementation | Automated test | Runtime artifact | Verdict |
| Tool authorisation | policy.py, ToolGateway | test_tool_auth_research_denied, internal_allowed, approval_required | tool_auth_denied.jsonl DENY NOT executed, allowed.jsonl ALLOW synthetic result, approval_required.jsonl | VERIFIED |
| Cross-client isolation | MemoryService namespaces | test_cross_client_isolation_no_leak | memory_client_001.jsonl, memory_client_002.jsonl, memory_isolation.md concise persists conservative NOT leaked | VERIFIED |
| Agent registry | registry + runtime_factory | test_registry_reconstruction_v1_2_0, policy_change_affects_runtime, delete_fails | registry_v1_2_0.jsonl, registry_v1_2_1.jsonl calculator removed changes runtime, registry_v1_2_0_output.json | VERIFIED |
| Replay evaluation | replay.py ReplayEngine | test_replay_baseline_to_aggressive, different_retriever | replay_baseline/, replay_candidate/ new trace_ids new execution original immutable diff | VERIFIED |
| FinAgent | finagent_real.py 133 tasks | test_finagent_real_loader_133, oracle_133_execution | finagent_oracle_133/ 133/133 task_level.json finagent_v1_1_1.json provenance | VERIFIED |
| Lifecycle Gate | gate + evidence pack + CLI | test_cli_pass_exit_code, block_exit_code, infra_exit_code, evidence_pack_regeneration | cli_pass.txt 0, cli_block.txt 1 BLOCK P1 0→1, cli_infra_failure.txt 2 | VERIFIED |

Final Acceptance: All VERIFIED → audit-candidate-v0.1.7 → No further self-certification, independent Codex/Hermes audit begins

---

## Slide 14: Decision Choices & Why — Engineering Judgement

- LangGraph for orchestration, DSPy for LM programs inside graph: Why Orchestration deterministic, reasoning measurable & optimisable — Alternative pure DSPy or pure LangGraph rejected because orchestration needs state, LM needs optimisation

- Rule-based supervisor first, not frontier: Why Build evaluation platform first, model optimisation later — evals might win interview, bankers require trusted systems — Guiding rule: "Build the evaluation and reliability platform first. Model optimisation comes later"

- Tool failure semantics timeout→SOURCE_UNAVAILABLE never 0: Why Invented 0 is P1 material unsupported claim, bank cannot risk fabricated exposure — Tested and enforced in gateway

- Memory authoritative state never from durable memory: Why Credit exposure, positions, market prices, GL balances must come from authoritative providers, not memory — Cross-client leak = P0 BLOCK — verified two-client workflow trace

- Registry-driven manifest YAML file-backed JSON: Why Reusable across teams, versioned, reconstructable, framework-neutral — Why not Python filename: No workflow identified merely by filename — manifest is source of truth — Local reference implementation not K8s/real SSO — proves AI engineering judgement not infra spending

- Composite metric with P0/P1 hard penalty + feedback for GEPA: Why Average metrics hide critical failures, P0/P1 must be 0, feedback enables GEPA to learn — Example feedback: "treated missing as zero rather than unavailable"

- Measured/Simulated/Expected separation: Why Fixes Phase 1.5 problem where mock MIPRO/GEPA appeared next to measured without distinction — Every result has evidence_type, UI visually distinguishes

- Slice analysis never only global averages: Why Overall 94% hides conflicting_data 62% — dangerous averages, slice analysis prevents

- Evidence Pack as killer feature: Why Audit-ready package not merely dashboard — shows provenance, versions, slices, failures, decision

---

## Slide 15: What NOT Built — Intentional Scope Control

Do NOT build (proves infra spending not AI judgement): Kubernetes, Real distributed control plane, Real SSO/IAM, Real Databricks/LSEG/Bloomberg, Full cloud deployment/Terraform, Kafka cluster, Enterprise secrets platform, Service mesh — Instead Interfaces + local reference implementations — Implementation local prototype not deployed Danske/AWS system — Interfaces compatible so migration is config not rewrite

Deferred to Phase 2 (not started): LFM fine-tuning LoRA/QLoRA 230M/350M/1.2B, Tau training pipeline, Cascade confidence optimization, Real Databricks SQL + Unity Catalog, Real LSEG/Bloomberg provider

Why scope control matters: Shows spec-driven development MVP focus, Small number of agents 6 required only keep small, Do not broaden workflows/datasets/agents/UI without approval, Do not begin fine-tuning before eval platform stable

Technology: Python 3.11+, Pydantic, LangGraph, FastAPI, Streamlit, SQLite/DuckDB, Qdrant, BM25, sentence-transformers, pytest, structured JSON logging, Model abstraction mandatory provider/model/prompt_version/tokens/latency/cost

Honesty principle: "please bear with me and do not front at all" — be honest no bullshit, Business metrics interface status=NOT_CONNECTED rather than fake ROI, Simulated results labeled simulated not measured

---

## Slide 16: Enterprise Harness Demo — 7 Steps Story Obvious

Step A: Open Agent Registry — Show PreMeetingBriefAgent v1.2 and its workflow, models, tools, memory policy, eval suite — registry_store/agents/markets.pre_meeting_brief/1.2.0.json

Step B: Create Candidate v1.3 using DSPy GEPA program — Button creates markets.pre_meeting_brief@1.3.0 with GEPA program removes calculator or changes workflow version — Proves registry is authoritative runtime behaviour changes accordingly

Step C: Run markets_pre_meeting_release@3.0.0 suite — CLI agent-eval run --agent markets.pre_meeting_brief@1.3.0 --suite markets_pre_meeting_release@3 — Offline Agent Version→Suite→Tasks→Trace→Scorers→Slices→Report

Step D: Show Results — FinAgent 133, Golden Suite 18, retrieval Recall@5/MRR, tool accuracy, workflow success, HITL escalation precision/recall, latency P95, cost — Component-level data/retrieval/tool/agent/multi-agent/workflow/output/ops

Step E: Open Slices — Candidate better overall 85% but worse on conflicting_data 62% — prevents dangerous averages — Critical failures conflicting_data adversarial

Step F: Lifecycle Gate BLOCK/HUMAN_REVIEW — Evidence pack shows P1 0→1 or critical slice low — Decision BLOCK — candidate should NOT progress despite higher overall

Step G: Open Evidence Pack — Every artifact versioned: candidate identity, baseline, code/model/program/prompt/tool versions, datasets, scorer versions, judge validation, metrics, slices, P0/P1, red-team, regression diff, HUMAN review, limitations, final decision — Audit-ready package not merely dashboard

Killer demo — practice it

---

## Slide 17: Final Report & Next Steps

Phase 1 Reliability Foundation FROZEN — 6 agents, Tool Gateway, Memory, Trace, Golden R01-R06, FinAgent mock 20, Lifecycle Gate — Golden suite 18 tasks PASS P0=0 P1=0

Phase 1.5 DSPy Intelligence COMPLETE — Signatures, Predict vs CoT, ReAct, MIPROv2/GEPA light, composite metric — Holdout 12 baseline 0.461 P1=3 → Predict 0.696 P1=0 → MIPRO 0.92 GEPA 0.94 simulated

Phase 1E Enterprise Harness COMPLETE — 10 registries 50 entries, Policy, Memory Service, Trace Bus, Eval Harness, Evidence Pack, CLI, Online Eval, Dashboards 7-tab main + 16-tab enterprise

Phase 1V Runtime Verification COMPLETE 6/6 VERIFIED — Tool auth, cross-client, registry, replay, FinAgent 133, Gate CLI — 70 tests PASS, artifacts under reports/verification/, runs/verification/, traces/verification/, Tag audit-candidate-v0.1.7

What remains simulated (honest): DSPy MIPROv2/GEPA uplift simulated until real LM (DummyLM) — integration VERIFIED uplift SIMULATED, FinAgent RAG mode partial if filing corpus subset — Oracle 133 VERIFIED, Online eval local reference not prod monitoring, Cost metrics from mock not real Bedrock billing

What remains partial: FinAgent RAG end-to-end requires full SEC corpus, change_credit_limit policy REQUIRE_APPROVAL verified not yet real mutating tool

Next Steps Phase 2 Deferred: Real Bedrock integration via Model Registry, LFM2.5-1.2B LoRA fine-tuning register as local.lfm2.5-1.2b@1.1.0-lora, Cascade evaluation using cost/latency metrics, Real Databricks/LSEG providers via provider interface, No change to harness — same measurement system

Final Thesis: Evaluation-driven enterprise agent development harness reference implementation — Evaluation harness framework-independent: LangGraph, DSPy, LFM all pass same measurement and lifecycle system
