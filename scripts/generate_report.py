#!/usr/bin/env python3
"""Generate markdown report from eval runs"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import json
import argparse
from pathlib import Path as PathLib

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", type=str, required=True)
    parser.add_argument("--runs-dir", type=str, default="runs")
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    run_dir = Path(args.runs_dir) / args.run_id
    summary_path = run_dir / "summary.json"
    decision_path = run_dir / "lifecycle_decision.json"

    with open(summary_path) as f:
        summary = json.load(f)

    decision = None
    if decision_path.exists():
        with open(decision_path) as f:
            decision = json.load(f)

    md = f"# Evaluation Report - {args.run_id}\n\n"
    md += f"**Date:** {summary.get('timestamp', 'N/A')}\n\n"
    md += f"## Summary\n"
    md += f"- Total tasks: {summary.get('total_tasks')}\n"
    md += f"- P0 failures: {summary.get('p0_failures')}\n"
    md += f"- P1 failures: {summary.get('p1_failures')}\n"
    md += f"- P2 failures: {summary.get('p2_failures')}\n"
    md += f"- Pass rate: {summary.get('pass_rate', 0):.2%}\n\n"

    md += f"## Metrics\n"
    md += f"| Metric | Value |\n|--------|-------|\n"
    for k, v in summary.get("metrics", {}).items():
        if v is not None:
            if isinstance(v, float):
                md += f"| {k} | {v:.3f} |\n"
            else:
                md += f"| {k} | {v} |\n"

    if decision:
        md += f"\n## Lifecycle Gate\n"
        md += f"- Outcome: **{decision.get('outcome')}**\n"
        md += f"- Reason: {decision.get('reason')}\n"
        if decision.get("blocking_gates_violated"):
            md += f"- Blocking: {decision.get('blocking_gates_violated')}\n"

    # Load eval results for failure details
    jsonl_path = run_dir / "eval_results.jsonl"
    if jsonl_path.exists():
        md += f"\n## Failures\n"
        with open(jsonl_path) as f:
            for line in f:
                data = json.loads(line)
                if data.get("failure_severity") in ["P0", "P1"]:
                    md += f"- **{data['task_id']}** ({data['failure_severity']}): {data.get('failure_reason')}\n"

    output_path = Path(args.output) if args.output else run_dir / "report.md"
    with open(output_path, "w") as f:
        f.write(md)

    print(f"Report saved to {output_path}")
    print(md)

if __name__ == "__main__":
    main()
