# Claims Ledger - Phase 1V Verification

**Generated:** 2026-09-17T07:42:11.331689+00:00

| Requirement | Implementation | Automated test | Runtime artifact | Verdict |
| --- | --- | --- | --- | --- |
| Tool authorisation | enterprise/policy.py, ToolGateway, Tool Registry | tests/integration/test_verification_runtime.py::test_tool_auth_research_denied, test_tool_auth_internal_allowed, test_tool_auth_approval_required | traces/verification/tool_auth_denied.jsonl, traces/verification/tool_auth_allowed.jsonl, traces/verification/tool_auth_approval_required.jsonl, reports/verification/tool_authorisation.json | VERIFIED |
| Cross-client isolation | enterprise/memory_service.py, MemoryService, namespaces tenant/user/client | tests/integration/test_verification_runtime.py::test_cross_client_isolation_no_leak, test_cross_client_preference_persists | traces/verification/memory_client_001.jsonl, traces/verification/memory_client_002.jsonl, reports/verification/memory_isolation.md, reports/verification/memory_isolation.json | VERIFIED |
| Agent registry | registry/agent_registry.py, enterprise/runtime_factory.py, RegistryRuntimeFactory | tests/integration/test_verification_runtime.py::test_registry_reconstruction_v1_2_0, test_registry_policy_change_affects_runtime, test_registry_delete_fails_no_fallback | traces/verification/registry_v1_2_0.jsonl, traces/verification/registry_v1_2_1.jsonl, runs/verification/registry_v1_2_0_output.json, reports/verification/registry_runtime_reconstruction.md | VERIFIED |
| Replay evaluation | enterprise/replay.py, ReplayEngine, TraceBus replay_ready | tests/integration/test_verification_runtime.py::test_replay_baseline_to_aggressive, test_replay_different_retriever | runs/verification/replay_baseline/, runs/verification/replay_candidate/, reports/verification/replay_comparison.md, reports/verification/replay_comparison.json | VERIFIED |
| FinAgent | evals/finagent_real.py, FinAgentRealLoader v1.1.1 133 tasks, EvaluationRunner | tests/integration/test_verification_runtime.py::test_finagent_real_loader_133, test_finagent_oracle_133_execution | runs/verification/finagent_oracle_133/, reports/verification/finagent_oracle_133.md, reports/verification/finagent_oracle_133.json, data/finagent_v1_1_1.json, data/finagent_v1_1_1_provenance.json | VERIFIED |
| Lifecycle Gate | enterprise/evidence_pack.py, enterprise/cli.py, regression/gate.py, EvidencePackGenerator | tests/integration/test_verification_runtime.py::test_cli_pass_exit_code, test_cli_block_exit_code, test_cli_infra_exit_code, test_evidence_pack_regeneration | reports/verification/cli_pass.txt, reports/verification/cli_block.txt, reports/verification/cli_infra_failure.txt, evidence_packs/, reports/verification/lifecycle_gate_cli.json | VERIFIED |

## Final Acceptance Condition

| Requirement | Verdict |
| --- | --- |
| Tool authorisation | **VERIFIED** |
| Cross-client isolation | **VERIFIED** |
| Agent registry | **VERIFIED** |
| Replay evaluation | **VERIFIED** |
| FinAgent | **VERIFIED** |
| Lifecycle Gate | **VERIFIED** |

**All VERIFIED:** True

> **No further self-certification by Arena. Independent Codex/Hermes audit begins.**
