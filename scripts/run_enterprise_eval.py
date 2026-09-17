"""
Run enterprise evaluation harness - Phase 1E
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import argparse
from financial_agent.enterprise.eval_harness import EnterpriseEvalHarness
from financial_agent.enterprise.evidence_pack import EvidencePackGenerator
from financial_agent.registry.bootstrap import bootstrap_all

def main():
    parser = argparse.ArgumentParser(description="Enterprise Eval Harness")
    parser.add_argument("--agent", default="markets.pre_meeting_brief@1.3.0", help="Agent id@version")
    parser.add_argument("--suite", default="markets_pre_meeting_release@3.0.0", help="Suite id@version")
    parser.add_argument("--baseline", help="Baseline experiment id")
    parser.add_argument("--evidence-type", default="measured", choices=["measured", "simulated", "expected"])
    parser.add_argument("--bootstrap", action="store_true", help="Bootstrap registries first")

    args = parser.parse_args()

    if args.bootstrap:
        bootstrap_all()

    if "@" in args.agent:
        agent_id, agent_version = args.agent.split("@", 1)
    else:
        agent_id = args.agent
        agent_version = "1.3.0"

    if "@" in args.suite:
        suite_id, suite_version = args.suite.split("@", 1)
    else:
        suite_id = args.suite
        suite_version = "3.0.0"

    print(f"=== Enterprise Evaluation Harness ===")
    print(f"Agent: {agent_id}@{agent_version}")
    print(f"Suite: {suite_id}@{suite_version}")
    print(f"Evidence Type: {args.evidence_type}")

    harness = EnterpriseEvalHarness()
    result = harness.evaluate(
        agent_id=agent_id,
        agent_version=agent_version,
        suite_id=suite_id,
        suite_version=suite_version,
        evidence_type=args.evidence_type
    )

    print(f"\nExperiment: {result.experiment_id}")
    print(f"Overall Accuracy: {result.overall.get('accuracy', 0):.3f}")
    print(f"Tool F1: {result.overall.get('tool_f1', 0):.3f}")
    print(f"Evidence Type: {result.evidence_type}")

    print(f"\n--- Slice Analysis ---")
    analysis = harness.slice_analysis(result)
    print(f"Overall: {analysis['overall']}")
    print(f"Worst slice: {analysis['worst_slice']}")
    print(f"Best slice: {analysis['best_slice']}")
    if analysis['critical_failures']:
        print(f"CRITICAL FAILURES: {analysis['critical_failures']}")

    print(f"\n--- Component-Level ---")
    for comp in result.components:
        print(f"{comp.component}: {comp.score:.3f}")

    print(f"\n--- Trace-Based Checks ---")
    for check, passed in result.trace_based.items():
        status = "✅" if not check.startswith("unauthorised") and passed or check.startswith("unauthorised") and not passed else "❌"
        # Simplified
        print(f"{check}: {passed}")

    print(f"\n--- HITL ---")
    print(result.hitl)

    print(f"\n--- Cost/Latency ---")
    print(result.cost_latency)

    # Generate evidence pack
    generator = EvidencePackGenerator()
    pack = generator.generate(
        candidate_identity=f"{agent_id}@{agent_version}",
        baseline_identity="markets.pre_meeting_brief@1.2.0",
        experiment_results=result.model_dump(),
        slice_analysis={s.slice_name: {"accuracy": s.accuracy} for s in result.slices},
        evidence_type=result.evidence_type
    )

    print(f"\n--- Evidence Pack ---")
    print(f"ID: {pack.evidence_pack_id}")
    print(f"Decision: {pack.lifecycle_decision} - {pack.decision_reason}")
    print(f"Saved to: evidence_packs/{pack.evidence_pack_id}.json")

    # CLI return code logic
    if pack.lifecycle_decision == "BLOCK":
        print("\n❌ BLOCK - Candidate should NOT progress")
        return 1
    else:
        print(f"\n✅ {pack.lifecycle_decision} - Candidate can progress")
        return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
