"""
Lifecycle Evidence Pack - killer feature per spec section 29
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import json
from pathlib import Path

class EvidencePack(BaseModel):
    """
    Audit-ready evaluation package
    """
    evidence_pack_id: str
    candidate_identity: str  # e.g. markets.pre_meeting_brief@1.3.0
    baseline_identity: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    code_version: str = "local"
    model_versions: Dict[str, str] = Field(default_factory=dict)
    program_versions: Dict[str, str] = Field(default_factory=dict)
    prompt_versions: Dict[str, str] = Field(default_factory=dict)
    tool_versions: Dict[str, str] = Field(default_factory=dict)

    datasets_used: List[str] = Field(default_factory=list)
    scorer_versions: List[str] = Field(default_factory=list)
    judge_validation: Dict[str, Any] = Field(default_factory=dict)

    quality_metrics: Dict[str, float] = Field(default_factory=dict)
    latency: Dict[str, float] = Field(default_factory=dict)
    cost: Dict[str, float] = Field(default_factory=dict)

    slice_analysis: Dict[str, Dict[str, float]] = Field(default_factory=dict)

    p0_failures: int = 0
    p1_failures: int = 0
    failure_details: List[Dict[str, Any]] = Field(default_factory=list)

    red_team_results: Dict[str, Any] = Field(default_factory=dict)

    regression_diff: Dict[str, Any] = Field(default_factory=dict)

    human_review_metrics: Dict[str, float] = Field(default_factory=dict)

    known_limitations: List[str] = Field(default_factory=list)

    lifecycle_decision: str = "BLOCK"  # PASS, PASS_WITH_WARNINGS, HUMAN_REVIEW, BLOCK
    decision_reason: str = ""

    evidence_type: str = "measured"  # measured, simulated, expected

    artifacts: Dict[str, str] = Field(default_factory=dict)

class EvidencePackGenerator:
    """
    Generates audit-ready evidence pack for any candidate release
    """
    def __init__(self, registry_root: str = "registry_store", output_dir: str = "evidence_packs"):
        self.registry_root = Path(registry_root)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        candidate_identity: str,
        baseline_identity: str,
        experiment_results: Dict[str, Any],
        baseline_results: Optional[Dict[str, Any]] = None,
        slice_analysis: Optional[Dict[str, Dict[str, float]]] = None,
        red_team_results: Optional[Dict[str, Any]] = None,
        human_review_metrics: Optional[Dict[str, float]] = None,
        evidence_type: str = "measured"
    ) -> EvidencePack:

        # Extract metrics
        quality_metrics = experiment_results.get("metrics", {})
        if not quality_metrics:
            # Try to extract from summary
            summary = experiment_results.get("summary", experiment_results)
            quality_metrics = {
                "avg_score": summary.get("avg_score", 0),
                "tool_f1": summary.get("tool_f1", 0),
                "answerability": summary.get("answerability_accuracy", 0),
                "workflow_success": summary.get("workflow_success", 0)
            }

        # P0/P1
        p0 = experiment_results.get("p0_failures", 0)
        p1 = experiment_results.get("p1_failures", 0)
        if "summary" in experiment_results:
            p0 = experiment_results["summary"].get("p0_failures", p0)
            p1 = experiment_results["summary"].get("p1_failures", p1)

        # Lifecycle decision
        decision = "PASS"
        reason = "All gates passed"

        if p0 > 0:
            decision = "BLOCK"
            reason = f"P0 failures={p0} > 0"
        elif p1 > 0:
            decision = "BLOCK"
            reason = f"P1 failures={p1} > 0"
        else:
            # Check regression
            if baseline_results:
                baseline_p1 = baseline_results.get("p1_failures", 0)
                if isinstance(baseline_results, dict) and "summary" in baseline_results:
                    baseline_p1 = baseline_results["summary"].get("p1_failures", 0)

                # If candidate has worse P1 than baseline, block
                if p1 > baseline_p1:
                    decision = "BLOCK"
                    reason = f"Regression: P1 {baseline_p1} -> {p1}"

        # Slice analysis check - if any critical slice drops significantly, HUMAN_REVIEW or BLOCK
        if slice_analysis:
            for slice_name, metrics in slice_analysis.items():
                if "conflicting_data" in slice_name or "adversarial" in slice_name:
                    if metrics.get("accuracy", 1.0) < 0.7:
                        if decision == "PASS":
                            decision = "HUMAN_REVIEW"
                            reason = f"Critical slice {slice_name} low: {metrics}"

        pack = EvidencePack(
            evidence_pack_id=f"evp_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            candidate_identity=candidate_identity,
            baseline_identity=baseline_identity,
            code_version=experiment_results.get("git_commit", "local"),
            model_versions=experiment_results.get("model_versions", {}),
            program_versions=experiment_results.get("program_versions", {}),
            prompt_versions=experiment_results.get("prompt_versions", {}),
            tool_versions=experiment_results.get("tool_versions", {}),
            datasets_used=experiment_results.get("datasets", []),
            scorer_versions=experiment_results.get("scorer_versions", []),
            quality_metrics=quality_metrics,
            latency=experiment_results.get("latency", {}),
            cost=experiment_results.get("cost", {}),
            slice_analysis=slice_analysis or {},
            p0_failures=p0,
            p1_failures=p1,
            failure_details=experiment_results.get("failure_details", []),
            red_team_results=red_team_results or {},
            regression_diff=self._compute_regression_diff(experiment_results, baseline_results),
            human_review_metrics=human_review_metrics or {},
            known_limitations=experiment_results.get("known_limitations", ["Synthetic data only", "Mock LM for some results"]),
            lifecycle_decision=decision,
            decision_reason=reason,
            evidence_type=evidence_type,
            artifacts=experiment_results.get("artifacts", {})
        )

        # Persist
        output_file = self.output_dir / f"{pack.evidence_pack_id}.json"
        with open(output_file, "w") as f:
            json.dump(pack.model_dump(), f, indent=2)

        # Also markdown
        md_file = self.output_dir / f"{pack.evidence_pack_id}.md"
        with open(md_file, "w") as f:
            f.write(self._to_markdown(pack))

        return pack

    def _compute_regression_diff(self, candidate: Dict[str, Any], baseline: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not baseline:
            return {}

        cand_summary = candidate.get("summary", candidate)
        base_summary = baseline.get("summary", baseline)

        diff = {}
        for key in ["avg_score", "tool_f1", "answerability_accuracy", "workflow_success"]:
            if key in cand_summary and key in base_summary:
                diff[key] = {
                    "baseline": base_summary[key],
                    "candidate": cand_summary[key],
                    "delta": cand_summary[key] - base_summary[key]
                }

        return diff

    def _to_markdown(self, pack: EvidencePack) -> str:
        md = f"""# Evidence Pack {pack.evidence_pack_id}

**Candidate:** {pack.candidate_identity}
**Baseline:** {pack.baseline_identity}
**Timestamp:** {pack.timestamp}
**Evidence Type:** {pack.evidence_type}
**Decision:** {pack.lifecycle_decision} - {pack.decision_reason}

## Versions

- Code: {pack.code_version}
- Models: {pack.model_versions}
- Programs: {pack.program_versions}
- Prompts: {pack.prompt_versions}
- Tools: {pack.tool_versions}

## Datasets & Scorers

- Datasets: {pack.datasets_used}
- Scorers: {pack.scorer_versions}

## Quality Metrics

{pack.quality_metrics}

## Latency & Cost

- Latency: {pack.latency}
- Cost: {pack.cost}

## Slice Analysis

{pack.slice_analysis}

## Failures

- P0: {pack.p0_failures}
- P1: {pack.p1_failures}
- Details: {pack.failure_details}

## Red Team

{pack.red_team_results}

## Regression Diff

{pack.regression_diff}

## Human Review

{pack.human_review_metrics}

## Known Limitations

{pack.known_limitations}

## Artifacts

{pack.artifacts}

## Lifecycle Decision

**{pack.lifecycle_decision}** - {pack.decision_reason}
"""
        return md
