"""
Trace Bus - canonical event envelope per spec section 11
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from enum import Enum
import uuid
import json
from pathlib import Path

class TraceEventType(str, Enum):
    request_received = "request_received"
    request_normalised = "request_normalised"
    supervisor_decision = "supervisor_decision"
    agent_start = "agent_start"
    agent_end = "agent_end"
    retrieval_query = "retrieval_query"
    retrieval_result = "retrieval_result"
    tool_call = "tool_call"
    tool_result = "tool_result"
    model_call = "model_call"
    verifier_input = "verifier_input"
    verifier_output = "verifier_output"
    synthesiser_input = "synthesiser_input"
    final_output = "final_output"
    evaluation_result = "evaluation_result"
    error = "error"
    memory_read = "memory_read"
    memory_write = "memory_write"
    policy_decision = "policy_decision"
    failure_detected = "failure_detected"
    human_review = "human_review"

class CanonicalTraceEvent(BaseModel):
    """
    Canonical trace envelope per spec section 11
    """
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    agent_id: str = "markets.pre_meeting_brief"
    agent_version: str = "1.2.0"

    workflow_id: str = "pre_meeting_brief"
    workflow_version: str = "3"

    event_type: TraceEventType = TraceEventType.tool_call

    component: str = "unknown"

    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    artifact_versions: Dict[str, str] = Field(default_factory=dict)  # model, prompt, program, tool

    payload: Dict[str, Any] = Field(default_factory=dict)

    tenant_id: str = "tenant_danske_mock"
    user_id: str = "user_banker_001"
    client_id: Optional[str] = None
    engagement_id: Optional[str] = None

    evidence_type: str = "measured"  # measured, simulated, expected

    def to_json(self) -> str:
        return self.model_dump_json()

class TraceBus:
    """
    Standardised trace bus - all subsystems emit this format
    """
    def __init__(self, trace_dir: str = "traces"):
        self.trace_dir = Path(trace_dir)
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self._events: List[CanonicalTraceEvent] = []
        self._current_trace_id: Optional[str] = None
        self._current_run_id: Optional[str] = None

    def start_trace(self, trace_id: Optional[str] = None, run_id: Optional[str] = None) -> str:
        self._current_trace_id = trace_id or str(uuid.uuid4())
        self._current_run_id = run_id or str(uuid.uuid4())
        self._events = []
        return self._current_trace_id

    def emit(self, event: CanonicalTraceEvent) -> CanonicalTraceEvent:
        if self._current_trace_id and not event.trace_id:
            event.trace_id = self._current_trace_id
        if self._current_run_id and not event.run_id:
            event.run_id = self._current_run_id

        self._events.append(event)

        # Persist immediately for replay capability
        trace_file = self.trace_dir / f"{event.trace_id}.jsonl"
        with open(trace_file, "a") as f:
            f.write(event.to_json() + "\n")

        return event

    def emit_simple(
        self,
        event_type: TraceEventType,
        component: str,
        payload: Dict[str, Any],
        agent_id: str = "markets.pre_meeting_brief",
        agent_version: str = "1.2.0",
        workflow_id: str = "pre_meeting_brief",
        workflow_version: str = "3",
        artifact_versions: Optional[Dict[str, str]] = None,
        tenant_id: str = "tenant_danske_mock",
        user_id: str = "user_banker_001",
        client_id: Optional[str] = None,
        engagement_id: Optional[str] = None,
        evidence_type: str = "measured"
    ) -> CanonicalTraceEvent:
        event = CanonicalTraceEvent(
            trace_id=self._current_trace_id or str(uuid.uuid4()),
            run_id=self._current_run_id or str(uuid.uuid4()),
            agent_id=agent_id,
            agent_version=agent_version,
            workflow_id=workflow_id,
            workflow_version=workflow_version,
            event_type=event_type,
            component=component,
            artifact_versions=artifact_versions or {},
            payload=payload,
            tenant_id=tenant_id,
            user_id=user_id,
            client_id=client_id,
            engagement_id=engagement_id,
            evidence_type=evidence_type
        )
        return self.emit(event)

    def get_events(self, trace_id: Optional[str] = None) -> List[CanonicalTraceEvent]:
        if trace_id:
            # Load from file
            trace_file = self.trace_dir / f"{trace_id}.jsonl"
            if not trace_file.exists():
                return []
            events = []
            with open(trace_file) as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        events.append(CanonicalTraceEvent(**data))
                    except:
                        continue
            return events
        return self._events

    def get_trace(self, trace_id: str) -> Dict[str, Any]:
        events = self.get_events(trace_id)
        return {
            "trace_id": trace_id,
            "event_count": len(events),
            "events": [e.model_dump() for e in events],
            "components": list(set(e.component for e in events)),
            "artifact_versions": self._collect_artifact_versions(events)
        }

    def _collect_artifact_versions(self, events: List[CanonicalTraceEvent]) -> Dict[str, str]:
        versions = {}
        for e in events:
            versions.update(e.artifact_versions)
        return versions

    def replay_ready(self, trace_id: str) -> Dict[str, Any]:
        """
        Persist enough to replay prior task against new model/program/tool
        """
        events = self.get_events(trace_id)
        # Find original request
        request_events = [e for e in events if e.event_type == TraceEventType.request_received]
        original_request = request_events[0].payload if request_events else {}

        return {
            "trace_id": trace_id,
            "original_request": original_request,
            "artifact_versions": self._collect_artifact_versions(events),
            "event_count": len(events),
            "replayable": True
        }
