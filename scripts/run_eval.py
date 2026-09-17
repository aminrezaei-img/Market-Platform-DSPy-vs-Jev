#!/usr/bin/env python3
"""
Run evaluation suite - Phase 1
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import argparse
from financial_agent.factory import create_workflow
from financial_agent.evals.datasets import GoldenSuiteLoader, FinAgentLoader
from financial_agent.evals.runner import EvaluationRunner
from financial_agent.tracing.tracer import Tracer
from financial_agent.memory.short_term import ShortTermMemory
from financial_agent.memory.long_term import LongTermMemory
from financial_agent.regression.gate import LifecycleGate

def main():
    parser = argparse.ArgumentParser(description="Run Financial Agent Reliability Eval")
    parser.add_argument("--suite", choices=["golden", "finagent", "all"], default="golden")
    parser.add_argument("--supervisor", choices=["rule_based", "mock", "frontier_cautious", "frontier_aggressive"], default="rule_based")
    parser.add_argument("--retriever", choices=["bm25", "dense", "hybrid"], default="hybrid")
    parser.add_argument("--run-id", type=str, default=None)
    parser.add_argument("--output-dir", type=str, default="runs")
    parser.add_argument("--agent-version", type=str, default="0.1.0")
    parser.add_argument("--prompt-version", type=str, default="supervisor-v1")

    args = parser.parse_args()

    print(f"=== Financial Agent Reliability Lab - Eval Runner ===")
    print(f"Suite: {args.suite}, Supervisor: {args.supervisor}, Retriever: {args.retriever}")

    tracer = Tracer()
    stm = ShortTermMemory()
    ltm = LongTermMemory()

    workflow = create_workflow(
        supervisor_type=args.supervisor,
        prompt_version=args.prompt_version,
        retriever_type=args.retriever,
        tracer=tracer,
        short_term_memory=stm,
        long_term_memory=ltm
    )

    runner = EvaluationRunner(
        workflow=workflow,
        output_dir=Path(args.output_dir),
        agent_version=args.agent_version,
        prompt_version=args.prompt_version,
        retriever_version=f"{args.retriever}-v1"
    )

    # Load tasks
    tasks_meta = []
    requests = []

    if args.suite in ["golden", "all"]:
        golden_loader = GoldenSuiteLoader()
        golden_tasks = golden_loader.get_tasks()
        golden_requests = golden_loader.to_user_requests()
        tasks_meta.extend(golden_tasks)
        requests.extend(golden_requests)
        print(f"Loaded {len(golden_tasks)} golden tasks (including R01-R06)")

    if args.suite in ["finagent", "all"]:
        fin_loader = FinAgentLoader()
        fin_tasks = fin_loader.get_tasks()
        fin_requests = fin_loader.to_user_requests()
        tasks_meta.extend(fin_tasks)
        requests.extend(fin_requests)
        print(f"Loaded {len(fin_tasks)} FinAgent mock tasks")

    print(f"Total tasks: {len(tasks_meta)}")
    print(f"Running evaluation...")

    run_id, results = runner.run_suite(requests, tasks_meta, run_id=args.run_id)

    print(f"\n=== Run Complete: {run_id} ===")
    run_dir = Path(args.output_dir) / run_id
    print(f"Results saved to: {run_dir}")

    # Summary
    summary_path = run_dir / "summary.json"
    if summary_path.exists():
        import json
        with open(summary_path) as f:
            summary = json.load(f)
        print("\n--- Summary ---")
        print(f"Total: {summary.get('total_tasks')}")
        print(f"P0 failures: {summary.get('p0_failures')}")
        print(f"P1 failures: {summary.get('p1_failures')}")
        print(f"P2 failures: {summary.get('p2_failures')}")
        print(f"Pass rate: {summary.get('pass_rate', 0):.2%}")
        print("\nMetrics:")
        for k, v in summary.get("metrics", {}).items():
            if v is not None:
                print(f"  {k}: {v:.3f}" if isinstance(v, float) else f"  {k}: {v}")

    # Lifecycle gate check for single run
    gate = LifecycleGate(gates_config_path=Path("configs/release_gates.yaml"))
    decision = gate.evaluate_single_run(results, run_id)
    print(f"\n--- Lifecycle Gate ---")
    print(f"Outcome: {decision.outcome.value}")
    print(f"Reason: {decision.reason}")
    if decision.blocking_gates_violated:
        print(f"Blocking: {decision.blocking_gates_violated}")

    decision_path = run_dir / "lifecycle_decision.json"
    gate.save_decision(decision, decision_path)
    print(f"Decision saved to: {decision_path}")

    return run_id

if __name__ == "__main__":
    main()
