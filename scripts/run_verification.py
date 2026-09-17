"""
Run Phase 1V Verification - 6 claims
Produces artifacts under reports/verification/, runs/verification/, traces/verification/
Creates CLAIMS_LEDGER.md/json and VERIFICATION_REPORT.md
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import json
from datetime import datetime, timezone
from financial_agent.verification.runtime_verification import RuntimeVerificationHarness

def main():
    print("=== Phase 1V Runtime Verification ===")
    print("Target: 6 claims -> VERIFIED with runtime evidence")

    harness = RuntimeVerificationHarness()

    results = {}

    # 1. Tool authorisation
    results["tool_authorisation"] = harness.verify_tool_authorisation()

    # 2. Cross-client isolation
    results["cross_client_isolation"] = harness.verify_cross_client_isolation()

    # 3. Agent registry runtime
    results["agent_registry"] = harness.verify_agent_registry_runtime()

    # 4. Replay evaluation
    results["replay_evaluation"] = harness.verify_replay_evaluation()

    # 5. FinAgent 133
    results["finagent"] = harness.verify_finagent_133()

    # 6. Lifecycle Gate CLI
    results["lifecycle_gate"] = harness.verify_lifecycle_gate_cli()

    # Build CLAIMS_LEDGER
    ledger = []

    # Tool authorisation
    ledger.append({
        "requirement": "Tool authorisation",
        "implementation": "enterprise/policy.py, ToolGateway, Tool Registry",
        "automated_test": "tests/integration/test_verification_runtime.py::test_tool_auth_research_denied, test_tool_auth_internal_allowed, test_tool_auth_approval_required",
        "runtime_artifact": "traces/verification/tool_auth_denied.jsonl, traces/verification/tool_auth_allowed.jsonl, traces/verification/tool_auth_approval_required.jsonl, reports/verification/tool_authorisation.json",
        "verdict": results["tool_authorisation"]["verdict"]
    })

    # Cross-client isolation
    ledger.append({
        "requirement": "Cross-client isolation",
        "implementation": "enterprise/memory_service.py, MemoryService, namespaces tenant/user/client",
        "automated_test": "tests/integration/test_verification_runtime.py::test_cross_client_isolation_no_leak, test_cross_client_preference_persists",
        "runtime_artifact": "traces/verification/memory_client_001.jsonl, traces/verification/memory_client_002.jsonl, reports/verification/memory_isolation.md, reports/verification/memory_isolation.json",
        "verdict": results["cross_client_isolation"]["verdict"]
    })

    # Agent registry
    ledger.append({
        "requirement": "Agent registry",
        "implementation": "registry/agent_registry.py, enterprise/runtime_factory.py, RegistryRuntimeFactory",
        "automated_test": "tests/integration/test_verification_runtime.py::test_registry_reconstruction_v1_2_0, test_registry_policy_change_affects_runtime, test_registry_delete_fails_no_fallback",
        "runtime_artifact": "traces/verification/registry_v1_2_0.jsonl, traces/verification/registry_v1_2_1.jsonl, runs/verification/registry_v1_2_0_output.json, reports/verification/registry_runtime_reconstruction.md",
        "verdict": results["agent_registry"]["verdict"]
    })

    # Replay evaluation
    ledger.append({
        "requirement": "Replay evaluation",
        "implementation": "enterprise/replay.py, ReplayEngine, TraceBus replay_ready",
        "automated_test": "tests/integration/test_verification_runtime.py::test_replay_baseline_to_aggressive, test_replay_different_retriever",
        "runtime_artifact": "runs/verification/replay_baseline/, runs/verification/replay_candidate/, reports/verification/replay_comparison.md, reports/verification/replay_comparison.json",
        "verdict": results["replay_evaluation"]["verdict"]
    })

    # FinAgent
    ledger.append({
        "requirement": "FinAgent",
        "implementation": "evals/finagent_real.py, FinAgentRealLoader v1.1.1 133 tasks, EvaluationRunner",
        "automated_test": "tests/integration/test_verification_runtime.py::test_finagent_real_loader_133, test_finagent_oracle_133_execution",
        "runtime_artifact": "runs/verification/finagent_oracle_133/, reports/verification/finagent_oracle_133.md, reports/verification/finagent_oracle_133.json, data/finagent_v1_1_1.json, data/finagent_v1_1_1_provenance.json",
        "verdict": results["finagent"]["verdict"]
    })

    # Lifecycle Gate
    ledger.append({
        "requirement": "Lifecycle Gate",
        "implementation": "enterprise/evidence_pack.py, enterprise/cli.py, regression/gate.py, EvidencePackGenerator",
        "automated_test": "tests/integration/test_verification_runtime.py::test_cli_pass_exit_code, test_cli_block_exit_code, test_cli_infra_exit_code, test_evidence_pack_regeneration",
        "runtime_artifact": "reports/verification/cli_pass.txt, reports/verification/cli_block.txt, reports/verification/cli_infra_failure.txt, evidence_packs/, reports/verification/lifecycle_gate_cli.json",
        "verdict": results["lifecycle_gate"]["verdict"]
    })

    # Save ledger JSON
    ledger_path_json = Path("reports/verification/CLAIMS_LEDGER.json")
    with open(ledger_path_json, "w") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "target_verdict": "All VERIFIED",
            "claims": ledger,
            "detailed_results": results
        }, f, indent=2, default=str)

    # Save ledger MD
    ledger_path_md = Path("reports/verification/CLAIMS_LEDGER.md")
    with open(ledger_path_md, "w") as f:
        f.write("# Claims Ledger - Phase 1V Verification\n\n")
        f.write(f"**Generated:** {datetime.now(timezone.utc).isoformat()}\n\n")
        f.write("| Requirement | Implementation | Automated test | Runtime artifact | Verdict |\n")
        f.write("| --- | --- | --- | --- | --- |\n")
        for entry in ledger:
            f.write(f"| {entry['requirement']} | {entry['implementation']} | {entry['automated_test']} | {entry['runtime_artifact']} | {entry['verdict']} |\n")
        f.write("\n## Final Acceptance Condition\n\n")
        f.write("| Requirement | Verdict |\n")
        f.write("| --- | --- |\n")
        for entry in ledger:
            f.write(f"| {entry['requirement']} | **{entry['verdict']}** |\n")

        all_verified = all(e["verdict"] == "VERIFIED" for e in ledger)
        f.write(f"\n**All VERIFIED:** {all_verified}\n")

        if all_verified:
            f.write("\n> **No further self-certification by Arena. Independent Codex/Hermes audit begins.**\n")

    # Save VERIFICATION_REPORT.md
    report_path = Path("reports/verification/VERIFICATION_REPORT.md")
    with open(report_path, "w") as f:
        f.write("# Verification Report - Phase 1V\n\n")
        f.write(f"**Generated:** {datetime.now(timezone.utc).isoformat()}\n\n")
        f.write("## What was claimed?\n\n")
        f.write("6 capabilities claimed as enterprise-ready:\n")
        f.write("- Tool authorisation (policy + gateway)\n")
        f.write("- Cross-client isolation (memory namespaces)\n")
        f.write("- Agent registry runtime-authoritative\n")
        f.write("- Replay evaluation actual re-execution\n")
        f.write("- FinAgent real 133-task benchmark\n")
        f.write("- Lifecycle Gate PASS/BLOCK/infra CLI\n\n")

        f.write("## What was actually executed?\n\n")
        for claim, result in results.items():
            f.write(f"### {claim}\n")
            f.write(f"- Verdict: {result.get('verdict', 'UNKNOWN')}\n")
            f.write(f"- Details: {json.dumps(result, indent=2, default=str)[:2000]}\n\n")

        f.write("## What evidence proves it?\n\n")
        for entry in ledger:
            f.write(f"- **{entry['requirement']}**: {entry['runtime_artifact']} -> {entry['verdict']}\n")

        f.write("\n## What remains simulated?\n\n")
        f.write("- DSPy MIPROv2/GEPA uplift remains SIMULATED until real LM execution (DummyLM used for mock)\n")
        f.write("- Some FinAgent RAG mode remains partial if filing corpus not fully indexed - Oracle mode VERIFIED, RAG mode PARTIALLY_VERIFIED if subset\n")
        f.write("- Online eval interface is local reference implementation, not production monitoring\n")
        f.write("- Cost/latency metrics are measured from mock runs, not real Bedrock billing\n\n")

        f.write("## What remains partial?\n\n")
        f.write("- FinAgent RAG end-to-end requires full SEC filing corpus - currently Oracle-context 133 VERIFIED, RAG PARTIALLY_VERIFIED if corpus subset\n")
        f.write("- Tool change_credit_limit is policy-level REQUIRE_APPROVAL, not yet implemented as real state-mutating tool in gateway - policy decision VERIFIED, execution blocked VERIFIED\n\n")

        f.write("## Final Acceptance\n\n")
        f.write("| Requirement | Verdict |\n")
        f.write("| --- | --- |\n")
        for entry in ledger:
            f.write(f"| {entry['requirement']} | **{entry['verdict']}** |\n")

        all_verified = all(e["verdict"] == "VERIFIED" for e in ledger)
        if all_verified:
            f.write("\n**All 6 claims VERIFIED - audit-candidate-v0.1.7**\n")
            f.write("\n> No further self-certification by Arena. Independent Codex/Hermes audit begins.\n")
        else:
            f.write(f"\n**Not all verified - remaining:** {[e['requirement'] for e in ledger if e['verdict'] != 'VERIFIED']}\n")

    print(f"\n=== Verification Complete ===")
    for entry in ledger:
        print(f"{entry['requirement']}: {entry['verdict']}")

    all_verified = all(e["verdict"] == "VERIFIED" for e in ledger)
    if all_verified:
        print("\n✅ All 6 claims VERIFIED - Ready for audit-candidate-v0.1.7")
    else:
        print(f"\n❌ Not all verified: {[e['requirement'] for e in ledger if e['verdict'] != 'VERIFIED']}")

    return 0 if all_verified else 1

if __name__ == "__main__":
    sys.exit(main())
