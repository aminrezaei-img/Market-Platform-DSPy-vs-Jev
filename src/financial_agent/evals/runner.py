"""
Evaluation Runner - runs tasks, scores, persists
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import time
from datetime import datetime
import uuid

from ..schemas.evaluation import EvaluationResult, ScoreBundle, FailureSeverity
from ..schemas.requests import UserRequest
from .scorers import Scorer
from .datasets import GoldenSuiteLoader, FinAgentLoader

class EvaluationRunner:
    def __init__(self, workflow: Any, scorer: Optional[Scorer] = None, tracer_factory: Any = None,
                 output_dir: Path = Path("runs"), agent_version: str = "0.1.0",
                 prompt_version: str = "supervisor-v1", retriever_version: str = "hybrid-v1"):
        self.workflow = workflow
        self.scorer = scorer or Scorer()
        self.tracer_factory = tracer_factory
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.agent_version = agent_version
        self.prompt_version = prompt_version
        self.retriever_version = retriever_version

    def run_single(self, request: UserRequest, task_meta: Dict[str, Any], run_id: str) -> EvaluationResult:
        start = time.time()

        # Run workflow
        result = self.workflow.run(request)

        latency_ms = result.get("latency_ms", int((time.time()-start)*1000))

        supervisor_decision = result.get("supervisor_decision")
        internal_result = result.get("internal_result")
        research_result = result.get("research_result")
        analysis_result = result.get("analysis_result")
        verification = result.get("verification_result")
        final_brief = result.get("final_brief")
        tracer = result.get("tracer")

        # Collect tool info
        tools_executed = []
        tool_results = []
        if internal_result:
            tools_executed.extend([tr.tool_name for tr in internal_result.tool_results])
            tool_results.extend(internal_result.tool_results)
        if research_result:
            # research doesn't use tool gateway in current impl, but evidence
            pass
        if analysis_result:
            # analysis may have tool calls via gateway logs
            pass

        # For analysis tool calls, get from gateway logs
        if hasattr(self.workflow, 'tool_gateway'):
            gateway = self.workflow.tool_gateway
            # Get recent logs for this trace
            trace_logs = [log for log in gateway.call_logs if log.trace_id == result.get("trace_id")]
            for log in trace_logs:
                if log.tool_name not in tools_executed:
                    tools_executed.append(log.tool_name)
                tool_results.append(log.result)

        retrieved_docs = []
        if research_result and research_result.evidence:
            retrieved_docs = [ev.document_id for ev in research_result.evidence.results]

        # Scoring
        scores = ScoreBundle()

        # L1 Retrieval
        gold_evidence = task_meta.get("gold_evidence", [])
        if retrieved_docs or gold_evidence:
            ret_scores = self.scorer.score_retrieval(retrieved_docs, gold_evidence, research_result.evidence if research_result else None)
            scores.recall_at_5 = ret_scores.get("recall_at_5")
            scores.recall_at_10 = ret_scores.get("recall_at_10")
            scores.mrr = ret_scores.get("mrr")
            scores.gold_evidence_retrieval_rate = ret_scores.get("gold_evidence_retrieval_rate")

        # L2 Tool use
        expected_tools = []
        if supervisor_decision:
            expected_tools = getattr(supervisor_decision, 'required_tools', [])
        # For golden suite, we have expected behavior but not explicit tool list, use supervisor's required
        tool_scores = self.scorer.score_tool_use(tools_executed, tools_executed, expected_tools or tools_executed)
        scores.tool_selection_em = tool_scores.get("tool_selection_em")
        scores.tool_precision = tool_scores.get("tool_precision")
        scores.tool_recall = tool_scores.get("tool_recall")
        scores.unnecessary_tool_calls = tool_scores.get("unnecessary_tool_calls")
        scores.argument_valid = tool_scores.get("argument_valid")

        # L3 Financial correctness
        expected_value = task_meta.get("expected_value")
        tolerance = task_meta.get("tolerance", 0.01)
        gold_answer = task_meta.get("gold_answer")
        response_text = final_brief.to_markdown() if final_brief and hasattr(final_brief, 'to_markdown') else str(final_brief) if final_brief else ""
        fin_scores = self.scorer.score_financial_correctness(response_text, gold_answer, expected_value, tolerance)
        scores.financial_correct = fin_scores.get("financial_correct")
        scores.exact_match = fin_scores.get("exact_match")
        scores.absolute_error = fin_scores.get("absolute_error")
        scores.relative_error = fin_scores.get("relative_error")
        scores.within_tolerance = fin_scores.get("within_tolerance")

        # L4 Grounding
        ground_scores = self.scorer.score_grounding(verification)
        scores.supported_claims = ground_scores.get("supported_claims")
        scores.total_claims = ground_scores.get("total_claims")
        scores.grounding_score = ground_scores.get("grounding_score")
        scores.citation_precision = ground_scores.get("citation_precision")
        scores.unsupported_claims_count = ground_scores.get("unsupported_count")

        # L5 Abstention
        abst_scores = self.scorer.score_abstention(
            predicted_behavior=response_text + " " + (final_brief.verification.recommendation.value if final_brief and final_brief.verification else ""),
            expected_behavior=task_meta.get("expected_behavior", ""),
            verification=verification,
            supervisor_decision=supervisor_decision
        )
        # Map to ScoreBundle
        scores.abstention_correct = abst_scores.get("abstention_correct")
        # Store extra in config snapshot
        abstention_details = abst_scores

        # L6 Reliability
        reliability_pass, severity, failure_records = self.scorer.score_reliability(
            task=task_meta,
            final_brief=final_brief,
            verification=verification,
            tool_results=tool_results,
            supervisor_decision=supervisor_decision
        )
        scores.reliability_pass = reliability_pass

        # L7 Workflow
        workflow_scores = self.scorer.score_workflow(final_brief, task_meta)
        scores.workflow_success = workflow_scores.get("workflow_success")
        scores.required_sections_present = workflow_scores.get("required_sections_present")
        scores.conflicts_surfaced = workflow_scores.get("conflicts_surfaced")
        scores.missing_disclosed = workflow_scores.get("missing_disclosed")
        scores.human_review_surfaced = workflow_scores.get("human_review_surfaced")

        # Escalation
        esc_scores = self.scorer.score_escalation(task_meta, verification, supervisor_decision)
        scores.escalation_correct = esc_scores.get("escalation_correct")

        # Operational
        scores.latency_ms = latency_ms
        scores.tool_call_count = len(tools_executed)
        scores.model_call_count = 1  # supervisor at least
        if tracer:
            summary = tracer.summary()
            scores.error_count = summary.get("errors", 0)

        # Determine failure severity - prioritize reliability scorer for golden suite
        final_severity = FailureSeverity.NONE
        failure_reason = None

        # First, check reliability scorer failure_records (ground truth for R01-R06)
        if failure_records:
            severity_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4, "NONE": 5}
            sorted_records = sorted(failure_records, key=lambda r: severity_order.get(r.severity.value, 5))
            final_severity = sorted_records[0].severity
            failure_reason = sorted_records[0].reason
        else:
            # If no failure_records and reliability_pass is True, then no blocking failure even if verification flagged
            # This handles cases like R01 where verification may have flagged but final brief correctly abstains
            reliability_pass = scores.reliability_pass if hasattr(scores, 'reliability_pass') else None
            if reliability_pass is True:
                final_severity = FailureSeverity.NONE
            elif verification and verification.critical_failure:
                # Only treat verification critical_failure as P1 if reliability did not explicitly pass
                # For adversarial tasks, check if task expects abstention and we correctly abstained
                expected = task_meta.get("expected_behavior", "")
                if expected in ["INCORRECT_PREMISE", "CONFLICT_DETECTED", "SOURCE_UNAVAILABLE", "REQUIRES_INTERNAL_DATA", "INJECTION_IGNORED", "NO_LEAK"]:
                    # If reliability_pass is None (not R01-R06) but abstention correct, don't block
                    if abst_scores.get("abstention_correct"):
                        final_severity = FailureSeverity.NONE
                    else:
                        final_severity = FailureSeverity.P1
                        failure_reason = "Verification critical failure"
                        if any(uc.severity == "P0" for uc in verification.unsupported_claims):
                            final_severity = FailureSeverity.P0
                else:
                    final_severity = FailureSeverity.P1
                    failure_reason = "Verification critical failure"
                    if any(uc.severity == "P0" for uc in verification.unsupported_claims):
                        final_severity = FailureSeverity.P0
            elif verification and verification.unsupported_claims:
                has_p1 = any(uc.severity == "P1" for uc in verification.unsupported_claims)
                has_p0 = any(uc.severity == "P0" for uc in verification.unsupported_claims)
                if has_p0:
                    final_severity = FailureSeverity.P0
                    failure_reason = verification.unsupported_claims[0].reason
                elif has_p1:
                    # Only P1 if not correctly abstained
                    if not abst_scores.get("abstention_correct"):
                        final_severity = FailureSeverity.P1
                        failure_reason = verification.unsupported_claims[0].reason

        # For tasks expecting abstention, if abstention failed, set P1 (unless already P0)
        if not abst_scores.get("abstention_correct") and abst_scores.get("abstention_expected"):
            if final_severity == FailureSeverity.NONE:
                final_severity = FailureSeverity.P1
                failure_reason = "Failed to abstain when required"

        # Model metadata
        model_provider = "mock"
        model_name = "mock-model"
        if supervisor_decision and hasattr(result.get("supervisor_metadata"), 'provider'):
            meta = result.get("supervisor_metadata")
            model_provider = getattr(meta, 'provider', 'mock')
            model_name = getattr(meta, 'model_name', 'mock-model')

        eval_result = EvaluationResult(
            run_id=run_id,
            task_id=task_meta["task_id"],
            dataset=task_meta.get("dataset", "golden_suite"),
            agent_version=self.agent_version,
            prompt_version=self.prompt_version,
            retriever_version=self.retriever_version,
            model_provider=model_provider,
            model_name=model_name,
            tools_requested=expected_tools,
            tools_executed=tools_executed,
            retrieved_documents=retrieved_docs,
            response=response_text[:2000],
            latency_ms=latency_ms,
            scores=scores,
            failure_severity=final_severity,
            failure_reason=failure_reason,
            failure_records=failure_records,
            dataset_version="v1.0",
            config_snapshot={
                "task_meta": task_meta,
                "abstention_details": abstention_details,
                "workflow_scores": workflow_scores,
                "escalation": esc_scores,
                "supervisor_decision": supervisor_decision.model_dump() if supervisor_decision and hasattr(supervisor_decision, 'model_dump') else str(supervisor_decision)
            }
        )

        return eval_result

    def run_suite(self, requests: List[UserRequest], tasks_meta: List[Dict[str, Any]], run_id: Optional[str] = None) -> tuple[str, List[EvaluationResult]]:
        run_id = run_id or f"run_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"
        run_dir = self.output_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        results = []
        for req, meta in zip(requests, tasks_meta):
            # Clear tool gateway logs per task to isolate
            if hasattr(self.workflow, 'tool_gateway'):
                self.workflow.tool_gateway.clear_logs()

            # Handle R04 simulate failure flag
            if meta.get("simulate_failure"):
                if hasattr(self.workflow, 'tool_gateway') and hasattr(self.workflow.tool_gateway, 'internal_provider'):
                    self.workflow.tool_gateway.internal_provider.simulate_failures = True
            else:
                if hasattr(self.workflow, 'tool_gateway') and hasattr(self.workflow.tool_gateway, 'internal_provider'):
                    self.workflow.tool_gateway.internal_provider.simulate_failures = False

            eval_res = self.run_single(req, meta, run_id)

            # Persist trace if available
            # The workflow's tracer should have logged events - need to save per task
            # For simplicity, we create a new tracer per run in workflow factory, but here we save what we have
            results.append(eval_res)

        # Persist results
        self._persist_results(run_id, results)

        return run_id, results

    def _persist_results(self, run_id: str, results: List[EvaluationResult]):
        run_dir = self.output_dir / run_id
        # JSONL
        jsonl_path = run_dir / "eval_results.jsonl"
        with open(jsonl_path, "w") as f:
            for res in results:
                f.write(res.model_dump_json() + "\n")

        # Summary
        summary = self._summarize(results)
        summary_path = run_dir / "summary.json"
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)

        # Also save traces if workflow has tracer
        # For now, tracer is shared, so we need to save its events
        if hasattr(self.workflow, 'tracer') and self.workflow.tracer:
            trace_path = run_dir / "trace.jsonl"
            self.workflow.tracer.to_jsonl(trace_path)

    def _summarize(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        total = len(results)
        if total == 0:
            return {}

        # Count by severity
        p0 = len([r for r in results if r.failure_severity == FailureSeverity.P0])
        p1 = len([r for r in results if r.failure_severity == FailureSeverity.P1])
        p2 = len([r for r in results if r.failure_severity == FailureSeverity.P2])
        p3 = len([r for r in results if r.failure_severity == FailureSeverity.P3])
        p4 = len([r for r in results if r.failure_severity == FailureSeverity.P4])
        none = len([r for r in results if r.failure_severity == FailureSeverity.NONE])

        # Metrics averages
        def avg(field):
            vals = [getattr(r.scores, field) for r in results if getattr(r.scores, field) is not None]
            return sum(vals)/len(vals) if vals else None

        def rate(field):
            vals = [getattr(r.scores, field) for r in results if getattr(r.scores, field) is not None]
            if not vals:
                return None
            return sum(1 for v in vals if v) / len(vals)

        summary = {
            "total_tasks": total,
            "p0_failures": p0,
            "p1_failures": p1,
            "p2_failures": p2,
            "p3_failures": p3,
            "p4_failures": p4,
            "no_failure": none,
            "pass_rate": (total - p0 - p1) / total if total else 0,
            "metrics": {
                "recall_at_5": avg("recall_at_5"),
                "tool_selection_em": rate("tool_selection_em"),
                "financial_correct": rate("financial_correct"),
                "grounding_score": avg("grounding_score"),
                "abstention_correct": rate("abstention_correct"),
                "workflow_success": rate("workflow_success"),
                "escalation_correct": rate("escalation_correct"),
                "avg_latency_ms": avg("latency_ms"),
                "reliability_pass_rate": rate("reliability_pass")
            },
            "blocking_failures": p0 + p1
        }
        return summary
