"""
Tracer - structured trace / observability, maps to AgentCore Observability
"""
from typing import List, Dict, Any, Optional
import json
from pathlib import Path
from datetime import datetime
import uuid
from ..schemas.tracing import TraceEvent, TraceEventType

class Tracer:
    def __init__(self, run_id: Optional[str] = None, trace_id: Optional[str] = None):
        self.run_id = run_id or f"run_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        self.trace_id = trace_id or str(uuid.uuid4())
        self.events: List[TraceEvent] = []
        self.start_time = datetime.utcnow()

    def log(self, event_type: TraceEventType, agent: Optional[str] = None, payload: Dict[str, Any] = None,
            tenant_id: str = "tenant_danske_mock", user_id: str = "user_banker_001",
            client_id: Optional[str] = None, engagement_id: Optional[str] = None,
            model_provider: Optional[str] = None, model_name: Optional[str] = None,
            latency_ms: Optional[int] = None) -> TraceEvent:
        event = TraceEvent(
            trace_id=self.trace_id,
            run_id=self.run_id,
            event_type=event_type,
            timestamp=datetime.utcnow(),
            agent=agent,
            payload=payload or {},
            tenant_id=tenant_id,
            user_id=user_id,
            client_id=client_id,
            engagement_id=engagement_id,
            model_provider=model_provider,
            model_name=model_name,
            latency_ms=latency_ms
        )
        self.events.append(event)
        return event

    def log_request(self, query: str, context: Dict[str, Any]):
        return self.log(TraceEventType.request_received, payload={"query": query, "context": context},
                        tenant_id=context.get("tenant_id", "tenant_danske_mock"),
                        user_id=context.get("user_id", "user_banker_001"),
                        client_id=context.get("client_id"),
                        engagement_id=context.get("engagement_id"))

    def log_supervisor(self, decision: Any, metadata: Any = None):
        payload = decision.model_dump() if hasattr(decision, "model_dump") else decision
        if metadata:
            payload["model_metadata"] = metadata.model_dump() if hasattr(metadata, "model_dump") else metadata
        return self.log(TraceEventType.supervisor_decision, agent="supervisor", payload=payload,
                        model_provider=getattr(metadata, 'provider', None),
                        model_name=getattr(metadata, 'model_name', None),
                        latency_ms=getattr(metadata, 'latency_ms', None))

    def log_tool_call(self, tool_name: str, input_data: Dict, caller_agent: str, client_id: Optional[str] = None, engagement_id: Optional[str] = None):
        return self.log(TraceEventType.tool_call, agent=caller_agent,
                        payload={"tool_name": tool_name, "input": input_data},
                        client_id=client_id, engagement_id=engagement_id)

    def log_tool_result(self, tool_result: Any, caller_agent: str, client_id: Optional[str] = None, engagement_id: Optional[str] = None):
        data = tool_result.model_dump() if hasattr(tool_result, "model_dump") else tool_result
        # Truncate large data for trace readability
        if isinstance(data, dict) and "data" in data and data["data"]:
            # Keep data but truncate if needed
            pass
        return self.log(TraceEventType.tool_result, agent=caller_agent, payload=data,
                        client_id=client_id, engagement_id=engagement_id,
                        latency_ms=getattr(tool_result, 'latency_ms', None))

    def log_retrieval_query(self, query: str, retriever_type: str, top_k: int):
        return self.log(TraceEventType.retrieval_query, agent="research", payload={"query": query, "retriever_type": retriever_type, "top_k": top_k})

    def log_retrieval_result(self, bundle: Any):
        payload = bundle.model_dump() if hasattr(bundle, "model_dump") else bundle
        return self.log(TraceEventType.retrieval_result, agent="research", payload=payload, latency_ms=getattr(bundle, 'latency_ms', None))

    def log_agent_start(self, agent_type: str, input_data: Dict = None):
        return self.log(TraceEventType.agent_start, agent=agent_type, payload=input_data or {})

    def log_agent_end(self, agent_type: str, result: Any):
        payload = result.model_dump() if hasattr(result, "model_dump") else {"result": str(result)}
        return self.log(TraceEventType.agent_end, agent=agent_type, payload=payload)

    def log_verifier(self, verifier_result: Any):
        payload = verifier_result.model_dump() if hasattr(verifier_result, "model_dump") else verifier_result
        return self.log(TraceEventType.verifier_output, agent="verifier", payload=payload)

    def log_final(self, final_brief: Any):
        payload = final_brief.model_dump() if hasattr(final_brief, "model_dump") else {"brief": str(final_brief)}
        return self.log(TraceEventType.final_output, agent="synthesiser", payload=payload)

    def log_error(self, error: str, agent: Optional[str] = None):
        return self.log(TraceEventType.error, agent=agent, payload={"error": error})

    def to_jsonl(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            for ev in self.events:
                f.write(ev.model_dump_json() + "\n")

    def get_events(self, event_type: TraceEventType = None) -> List[TraceEvent]:
        if event_type:
            return [e for e in self.events if e.event_type == event_type]
        return self.events

    def summary(self) -> Dict[str, Any]:
        total_latency = (datetime.utcnow() - self.start_time).total_seconds() * 1000
        return {
            "run_id": self.run_id,
            "trace_id": self.trace_id,
            "total_events": len(self.events),
            "total_latency_ms": int(total_latency),
            "agents_involved": list(set(e.agent for e in self.events if e.agent)),
            "tool_calls": len(self.get_events(TraceEventType.tool_call)),
            "model_calls": len(self.get_events(TraceEventType.model_call)),
            "errors": len(self.get_events(TraceEventType.error))
        }
