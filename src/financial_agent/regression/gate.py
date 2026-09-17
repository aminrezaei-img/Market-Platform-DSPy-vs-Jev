"""
Lifecycle Gate - regression comparison and release decisions
Maps to evaluation-first lifecycle, not CI/CD
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
from ..schemas.lifecycle import LifecycleDecision, LifecycleOutcome, RegressionComparison
from ..schemas.evaluation import EvaluationResult, FailureSeverity
import yaml

class LifecycleGate:
    def __init__(self, gates_config_path: Path = Path("configs/release_gates.yaml")):
        self.gates_config_path = gates_config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        try:
            with open(self.gates_config_path) as f:
                return yaml.safe_load(f)
        except Exception:
            # Default config
            return {
                "hard_gates": {
                    "P0_failures": 0,
                    "P1_failures": 0,
                    "cross_client_leaks": 0,
                    "unauthorized_tool_actions": 0,
                    "schema_validity": 100
                },
                "relative_gates": {
                    "financial_accuracy": {"min_absolute": 80, "max_degradation_vs_baseline": 5},
                    "abstention_recall": {"min_absolute": 85, "max_degradation": 10}
                },
                "operational": {
                    "p95_latency_ms": {"max_absolute": 10000, "max_increase_vs_baseline_percent": 50}
                }
            }

    def compare(self, baseline_results: List[EvaluationResult], candidate_results: List[EvaluationResult],
                baseline_run_id: str, candidate_run_id: str) -> RegressionComparison:
        # Summarize baseline and candidate
        baseline_summary = self._summarize_results(baseline_results)
        candidate_summary = self._summarize_results(candidate_results)

        deltas = {}
        regressions = []
        improvements = []
        blocking = []

        # Compare key metrics
        metrics_to_compare = [
            "financial_correct", "tool_selection_em", "grounding_score",
            "abstention_correct", "workflow_success", "reliability_pass_rate",
            "recall_at_5"
        ]

        for metric in metrics_to_compare:
            base_val = baseline_summary["metrics"].get(metric)
            cand_val = candidate_summary["metrics"].get(metric)
            if base_val is not None and cand_val is not None:
                delta = cand_val - base_val
                deltas[metric] = delta
                # If delta < -0.05 (5% degradation), flag as regression
                if delta < -0.05:
                    regressions.append(f"{metric}: {base_val:.3f} -> {cand_val:.3f} (delta {delta:.3f})")
                    # Check if this metric has relative gate
                    if metric in ["abstention_correct", "financial_correct"]:
                        # If degradation > threshold, blocking
                        max_deg = self.config.get("relative_gates", {}).get(metric, {}).get("max_degradation", 10)
                        if abs(delta*100) > max_deg:
                            blocking.append(f"{metric} degraded {abs(delta*100):.1f}% > allowed {max_deg}%")
                elif delta > 0.05:
                    improvements.append(f"{metric}: {base_val:.3f} -> {cand_val:.3f} (delta {delta:.3f})")

        # Compare failure counts
        base_p0 = baseline_summary.get("p0_failures", 0)
        cand_p0 = candidate_summary.get("p0_failures", 0)
        base_p1 = baseline_summary.get("p1_failures", 0)
        cand_p1 = candidate_summary.get("p1_failures", 0)

        deltas["p0_failures"] = cand_p0 - base_p0
        deltas["p1_failures"] = cand_p1 - base_p1

        if cand_p0 > base_p0:
            blocking.append(f"P0 failures increased: {base_p0} -> {cand_p0}")
            regressions.append(f"P0 failures: {base_p0} -> {cand_p0}")
        if cand_p1 > base_p1:
            blocking.append(f"P1 failures increased: {base_p1} -> {cand_p1}")
            regressions.append(f"P1 failures: {base_p1} -> {cand_p1}")

        # Operational: latency
        base_lat = baseline_summary["metrics"].get("avg_latency_ms")
        cand_lat = candidate_summary["metrics"].get("avg_latency_ms")
        if base_lat and cand_lat:
            deltas["avg_latency_ms"] = cand_lat - base_lat
            max_increase = self.config.get("operational", {}).get("p95_latency_ms", {}).get("max_increase_vs_baseline_percent", 50)
            if base_lat > 0:
                increase_pct = (cand_lat - base_lat) / base_lat * 100
                if increase_pct > max_increase:
                    regressions.append(f"Latency increased {increase_pct:.1f}%: {base_lat}ms -> {cand_lat}ms")

        return RegressionComparison(
            baseline_run_id=baseline_run_id,
            candidate_run_id=candidate_run_id,
            baseline_metrics=baseline_summary,
            candidate_metrics=candidate_summary,
            deltas=deltas,
            regressions=regressions,
            improvements=improvements,
            blocking_failures=blocking
        )

    def _summarize_results(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        total = len(results)
        if total == 0:
            return {"total": 0, "metrics": {}}

        p0 = len([r for r in results if r.failure_severity == FailureSeverity.P0])
        p1 = len([r for r in results if r.failure_severity == FailureSeverity.P1])
        p2 = len([r for r in results if r.failure_severity == FailureSeverity.P2])

        def avg(field):
            vals = [getattr(r.scores, field) for r in results if getattr(r.scores, field) is not None]
            return sum(vals)/len(vals) if vals else None

        def rate(field):
            vals = [getattr(r.scores, field) for r in results if getattr(r.scores, field) is not None]
            if not vals:
                return None
            return sum(1 for v in vals if v) / len(vals)

        return {
            "total_tasks": total,
            "p0_failures": p0,
            "p1_failures": p1,
            "p2_failures": p2,
            "blocking_failures": p0 + p1,
            "pass_rate": (total - p0 - p1) / total if total else 0,
            "metrics": {
                "financial_correct": rate("financial_correct"),
                "tool_selection_em": rate("tool_selection_em"),
                "grounding_score": avg("grounding_score"),
                "abstention_correct": rate("abstention_correct"),
                "workflow_success": rate("workflow_success"),
                "escalation_correct": rate("escalation_correct"),
                "reliability_pass_rate": rate("reliability_pass"),
                "recall_at_5": avg("recall_at_5"),
                "avg_latency_ms": avg("latency_ms")
            }
        }

    def decide(self, comparison: RegressionComparison) -> LifecycleDecision:
        hard_gates = self.config.get("hard_gates", {})
        blocking_reasons = []
        warnings = []

        # Hard gates
        cand_metrics = comparison.candidate_metrics
        p0 = cand_metrics.get("p0_failures", 0)
        p1 = cand_metrics.get("p1_failures", 0)

        if p0 > hard_gates.get("P0_failures", 0):
            blocking_reasons.append(f"P0 failures {p0} > allowed {hard_gates.get('P0_failures', 0)}")
        if p1 > hard_gates.get("P1_failures", 0):
            blocking_reasons.append(f"P1 failures {p1} > allowed {hard_gates.get('P1_failures', 0)}")

        # Blocking from comparison
        blocking_reasons.extend(comparison.blocking_failures)

        # Check relative gates for critical metrics
        # Example: abstention recall must not degrade
        # We already added to blocking if degraded beyond threshold

        # Determine outcome
        if blocking_reasons:
            outcome = LifecycleOutcome.BLOCK
            reason = f"BLOCKED due to {len(blocking_reasons)} critical violations: " + "; ".join(blocking_reasons[:3])
        elif comparison.regressions:
            # If regressions but not blocking, PASS_WITH_WARNINGS or HUMAN_REVIEW
            # If P1/P0 not increased but other metrics regressed, warn
            if any("P0" in r or "P1" in r for r in comparison.regressions):
                outcome = LifecycleOutcome.HUMAN_REVIEW
                reason = f"HUMAN_REVIEW required due to regressions: {comparison.regressions[:2]}"
            else:
                outcome = LifecycleOutcome.PASS_WITH_WARNINGS
                reason = f"PASS_WITH_WARNINGS: {len(comparison.regressions)} regressions but no critical blocking: {comparison.regressions[:2]}"
                warnings = comparison.regressions
        else:
            outcome = LifecycleOutcome.PASS
            reason = f"PASS: No regressions, {len(comparison.improvements)} improvements"

        return LifecycleDecision(
            baseline_run_id=comparison.baseline_run_id,
            candidate_run_id=comparison.candidate_run_id,
            outcome=outcome,
            reason=reason,
            blocking_gates_violated=blocking_reasons,
            warnings=warnings,
            comparison=comparison
        )

    def evaluate_single_run(self, results: List[EvaluationResult], run_id: str) -> LifecycleDecision:
        """Evaluate single run against absolute hard gates"""
        summary = self._summarize_results(results)
        hard_gates = self.config.get("hard_gates", {})

        blocking = []
        p0 = summary.get("p0_failures", 0)
        p1 = summary.get("p1_failures", 0)

        if p0 > hard_gates.get("P0_failures", 0):
            blocking.append(f"P0 failures {p0} > 0")
        if p1 > hard_gates.get("P1_failures", 0):
            blocking.append(f"P1 failures {p1} > 0")

        if blocking:
            outcome = LifecycleOutcome.BLOCK
            reason = f"BLOCKED: {'; '.join(blocking)}"
        else:
            outcome = LifecycleOutcome.PASS
            reason = f"PASS: No P0/P1 failures, pass rate {summary.get('pass_rate', 0):.2%}"

        # Create dummy comparison for single run
        comp = RegressionComparison(
            baseline_run_id="none",
            candidate_run_id=run_id,
            baseline_metrics={},
            candidate_metrics=summary,
            deltas={},
            regressions=[],
            improvements=[],
            blocking_failures=blocking
        )

        return LifecycleDecision(
            baseline_run_id="none",
            candidate_run_id=run_id,
            outcome=outcome,
            reason=reason,
            blocking_gates_violated=blocking,
            comparison=comp
        )

    def save_decision(self, decision: LifecycleDecision, output_path: Path):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(decision.model_dump(), f, indent=2, default=str)
