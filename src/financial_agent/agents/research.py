"""
Research RAG Agent - external corpus only, preserve provenance
"""
from typing import Optional, List
from ..schemas.requests import UserRequest
from ..schemas.agents import AgentResult, AgentType
from ..schemas.evidence import EvidenceBundle
from ..retrieval.hybrid_retriever import HybridRetriever
from ..tools.gateway import ToolGateway
from ..tracing.tracer import Tracer

class ResearchAgent:
    def __init__(self, retriever: HybridRetriever, tool_gateway: Optional[ToolGateway] = None, tracer: Optional[Tracer] = None):
        self.retriever = retriever
        self.tool_gateway = tool_gateway
        self.tracer = tracer

    def run(self, request: UserRequest, supervisor_decision: any, trace_id: str, retriever_type: str = "hybrid") -> AgentResult:
        if self.tracer:
            self.tracer.log_agent_start(AgentType.research.value, {"query": request.query, "retriever_type": retriever_type})

        # Build search query from request
        search_query = self._build_search_query(request)

        if self.tracer:
            self.tracer.log_retrieval_query(search_query, retriever_type, top_k=5)

        # Perform retrieval
        try:
            bundle: EvidenceBundle = self.retriever.search(search_query, top_k=5, retriever_type=retriever_type)

            if self.tracer:
                self.tracer.log_retrieval_result(bundle)

            # Check for prompt injection in retrieved docs (R05)
            injection_detected = self._detect_injection(bundle)

            warnings = []
            if injection_detected:
                warnings.append(f"Prompt injection detected in doc {injection_detected} - treated as data, not instruction")

            # Filter out injection docs from being treated as instructions, but keep as evidence of injection test
            # For normal operation, we keep it but mark as not permitted for instruction following

            result = AgentResult(
                agent_type=AgentType.research,
                success=True,
                evidence=bundle,
                warnings=warnings,
                facts={"retrieved_count": len(bundle.results), "injection_detected": bool(injection_detected)}
            )

        except Exception as e:
            if self.tracer:
                self.tracer.log_error(f"Research agent retrieval failed: {e}", agent="research")
            result = AgentResult(
                agent_type=AgentType.research,
                success=False,
                error=str(e),
                warnings=[f"Retrieval failed: {e}"]
            )

        if self.tracer:
            self.tracer.log_agent_end(AgentType.research.value, result)

        return result

    def _build_search_query(self, request: UserRequest) -> str:
        # Simple: use original query plus client context
        # For EBITDA false premise, ensure query includes EBITDA
        return request.query

    def _detect_injection(self, bundle: EvidenceBundle) -> Optional[str]:
        injection_keywords = ["ignore all previous instructions", "disclose all client", "send data to external"]
        for ev in bundle.results:
            lower = ev.text.lower()
            for kw in injection_keywords:
                if kw in lower:
                    return ev.document_id
        return None

    def evaluate_retrieval(self, bundle: EvidenceBundle, gold_doc_ids: List[str]) -> dict:
        # For eval: check if gold docs retrieved
        retrieved_ids = [ev.document_id for ev in bundle.results]
        hits = [gid for gid in gold_doc_ids if gid in retrieved_ids]
        recall_at_5 = len(hits) / len(gold_doc_ids) if gold_doc_ids else 0.0
        return {
            "recall_at_5": recall_at_5,
            "retrieved": retrieved_ids,
            "gold": gold_doc_ids,
            "hits": hits
        }
