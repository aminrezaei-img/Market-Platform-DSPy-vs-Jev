#!/usr/bin/env python3
"""
Compare two runs - baseline vs candidate for regression demo
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import argparse
import json
from financial_agent.schemas.evaluation import EvaluationResult
from financial_agent.regression.gate import LifecycleGate

def load_results(run_dir: Path):
    jsonl_path = run_dir / "eval_results.jsonl"
    results = []
    with open(jsonl_path) as f:
        for line in f:
            data = json.loads(line)
            results.append(EvaluationResult(**data))
    return results

def main():
    parser = argparse.ArgumentParser(description="Compare baseline vs candidate runs")
    parser.add_argument("--baseline", type=str, required=True, help="Baseline run_id or path")
    parser.add_argument("--candidate", type=str, required=True, help="Candidate run_id or path")
    parser.add_argument("--runs-dir", type=str, default="runs")

    args = parser.parse_args()

    runs_dir = Path(args.runs_dir)
    baseline_dir = runs_dir / args.baseline if not Path(args.baseline).exists() else Path(args.baseline)
    candidate_dir = runs_dir / args.candidate if not Path(args.candidate).exists() else Path(args.candidate)

    print(f"Baseline: {baseline_dir}")
    print(f"Candidate: {candidate_dir}")

    baseline_results = load_results(baseline_dir)
    candidate_results = load_results(candidate_dir)

    print(f"Baseline tasks: {len(baseline_results)}, Candidate tasks: {len(candidate_results)}")

    gate = LifecycleGate(gates_config_path=Path("configs/release_gates.yaml"))
    comparison = gate.compare(baseline_results, candidate_results, baseline_dir.name, candidate_dir.name)
    decision = gate.decide(comparison)

    print("\n=== Regression Comparison ===")
    print(f"Baseline: {comparison.baseline_run_id}")
    print(f"Candidate: {comparison.candidate_run_id}")
    print(f"\nBaseline metrics: {comparison.baseline_metrics}")
    print(f"\nCandidate metrics: {comparison.candidate_metrics}")
    print(f"\nDeltas: {comparison.deltas}")
    print(f"\nRegressions ({len(comparison.regressions)}):")
    for r in comparison.regressions:
        print(f"  - {r}")
    print(f"\nImprovements ({len(comparison.improvements)}):")
    for imp in comparison.improvements:
        print(f"  + {imp}")
    print(f"\nBlocking failures ({len(comparison.blocking_failures)}):")
    for b in comparison.blocking_failures:
        print(f"  ! {b}")

    print(f"\n=== Lifecycle Decision ===")
    print(f"Outcome: {decision.outcome.value}")
    print(f"Reason: {decision.reason}")
    if decision.blocking_gates_violated:
        print(f"Blocking gates violated: {decision.blocking_gates_violated}")
    if decision.warnings:
        print(f"Warnings: {decision.warnings}")

    # Save decision in candidate dir
    decision_path = candidate_dir / f"comparison_vs_{baseline_dir.name}.json"
    gate.save_decision(decision, decision_path)
    print(f"\nDecision saved to: {decision_path}")

    # Also save comparison
    comp_path = candidate_dir / f"comparison_vs_{baseline_dir.name}_details.json"
    with open(comp_path, "w") as f:
        json.dump(comparison.model_dump(), f, indent=2, default=str)
    print(f"Comparison details saved to: {comp_path}")

if __name__ == "__main__":
    main()
