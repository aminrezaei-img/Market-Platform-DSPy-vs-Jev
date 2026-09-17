"""
CLI for agent-eval - per spec 30
"""
import argparse
import sys
import json
from pathlib import Path
from typing import Optional

from ..registry import AgentRegistry, SuiteRegistry, ExperimentRegistry
from .eval_harness import EnterpriseEvalHarness
from .evidence_pack import EvidencePackGenerator

def run_eval_command(args):
    """
    agent-eval run --agent markets.pre_meeting_brief@1.3.0 --suite markets_pre_meeting_release@3
    Returns 0=PASS, 1=BLOCK, 2=infra failure
    """
    try:
        agent_str = args.agent
        suite_str = args.suite

        # Parse agent id@version
        if "@" in agent_str:
            agent_id, agent_version = agent_str.split("@", 1)
        else:
            agent_id = agent_str
            agent_version = "latest"

        if "@" in suite_str:
            suite_id, suite_version = suite_str.split("@", 1)
        else:
            suite_id = suite_str
            suite_version = "latest"

        # Check registries
        agent_registry = AgentRegistry()
        suite_registry = SuiteRegistry()

        # Resolve latest if needed
        if agent_version == "latest":
            agent_manifest = agent_registry.get(agent_id)
            if not agent_manifest:
                print(f"Agent {agent_id} not found", file=sys.stderr)
                return 2
            agent_version = agent_manifest.version
        else:
            agent_manifest = agent_registry.get(agent_id, agent_version)
            if not agent_manifest:
                print(f"Agent {agent_id}@{agent_version} not found", file=sys.stderr)
                return 2

        if suite_version == "latest":
            suite_manifest = suite_registry.get(suite_id)
            if not suite_manifest:
                print(f"Suite {suite_id} not found", file=sys.stderr)
                return 2
            suite_version = suite_manifest.version
        else:
            suite_manifest = suite_registry.get(suite_id, suite_version)
            if not suite_manifest:
                print(f"Suite {suite_id}@{suite_version} not found", file=sys.stderr)
                return 2

        # Run evaluation
        harness = EnterpriseEvalHarness()
        result = harness.evaluate(
            agent_id=agent_id,
            agent_version=agent_version,
            suite_id=suite_id,
            suite_version=suite_version,
            evidence_type="measured"
        )

        # Check lifecycle policy
        p0_max = suite_manifest.lifecycle_policy.get("p0_max", 0)
        p1_max = suite_manifest.lifecycle_policy.get("p1_max", 0)

        # Count failures from slices
        p0_total = sum(s.p0 for s in result.slices)
        p1_total = sum(s.p1 for s in result.slices)

        # Generate evidence pack
        generator = EvidencePackGenerator()
        baseline_id = f"{suite_id}_baseline@1.0.0"  # placeholder
        pack = generator.generate(
            candidate_identity=f"{agent_id}@{agent_version}",
            baseline_identity=baseline_id,
            experiment_results=result.model_dump(),
            evidence_type=result.evidence_type
        )

        print(f"Experiment: {result.experiment_id}")
        print(f"Agent: {agent_id}@{agent_version}")
        print(f"Suite: {suite_id}@{suite_version}")
        print(f"Evidence Type: {result.evidence_type}")
        print(f"Overall Accuracy: {result.overall.get('accuracy', 0):.3f}")
        print(f"P0: {p0_total} (max {p0_max}), P1: {p1_total} (max {p1_max})")
        print(f"Evidence Pack: {pack.evidence_pack_id}")
        print(f"Decision: {pack.lifecycle_decision}")

        if pack.lifecycle_decision == "BLOCK":
            return 1
        else:
            return 0

    except Exception as e:
        print(f"Infrastructure failure: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 2

def list_agents_command(args):
    registry = AgentRegistry()
    agents = registry.list()
    for agent in agents:
        print(f"{agent.id}@{agent.version} - {agent.owner} - {agent.description[:50]}")

def list_suites_command(args):
    registry = SuiteRegistry()
    suites = registry.list()
    for suite in suites:
        print(f"{suite.id}@{suite.version} - {suite.description[:50]}")

def main():
    parser = argparse.ArgumentParser(prog="agent-eval", description="Enterprise Agent Evaluation CLI")
    subparsers = parser.add_subparsers(dest="command")

    # run command
    run_parser = subparsers.add_parser("run", help="Run evaluation")
    run_parser.add_argument("--agent", required=True, help="Agent id@version e.g. markets.pre_meeting_brief@1.3.0")
    run_parser.add_argument("--suite", required=True, help="Suite id@version e.g. markets_pre_meeting_release@3")
    run_parser.add_argument("--baseline", help="Baseline experiment id")

    # list agents
    list_agents_parser = subparsers.add_parser("list-agents", help="List registered agents")

    # list suites
    list_suites_parser = subparsers.add_parser("list-suites", help="List registered suites")

    args = parser.parse_args()

    if args.command == "run":
        exit_code = run_eval_command(args)
        sys.exit(exit_code)
    elif args.command == "list-agents":
        list_agents_command(args)
    elif args.command == "list-suites":
        list_suites_command(args)
    else:
        parser.print_help()
        sys.exit(2)

if __name__ == "__main__":
    main()
