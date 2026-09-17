"""
Online Evaluation Interface - per spec 31
Do not build full production monitoring, create interface
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from enum import Enum

class OnlineAlertType(str, Enum):
    p1_unsupported_claim = "P1_UNSUPPORTED_CLAIM"
    tool_error_spike = "TOOL_ERROR_SPIKE"
    latency_regression = "LATENCY_REGRESSION"
    abstention_collapse = "ABSTENTION_COLLAPSE"
    escalation_rate_shift = "ESCALATION_RATE_SHIFT"

class OnlineTraceSample(BaseModel):
    trace_id: str
    agent_id: str
    agent_version: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    payload: Dict[str, Any] = Field(default_factory=dict)
    sampled: bool = False

class OnlineAlert(BaseModel):
    alert_id: str
    alert_type: OnlineAlertType
    severity: str = "WARNING"
    trace_id: str
    agent_id: str
    description: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)

class OnlineEvalInterface:
    """
    Accept production-like traces: trace ingest -> sampling -> online scorer -> alert
    Implementation runs locally
    """
    def __init__(self, sample_rate: float = 0.1):
        self.sample_rate = sample_rate
        self.ingested: List[OnlineTraceSample] = []
        self.alerts: List[OnlineAlert] = []
        self.metrics: Dict[str, Any] = {
            "total_ingested": 0,
            "total_sampled": 0,
            "p1_count": 0,
            "tool_error_count": 0,
            "avg_latency": 0,
            "abstention_rate": 0,
            "escalation_rate": 0
        }

    def ingest(self, trace: Dict[str, Any]) -> OnlineTraceSample:
        """
        Ingest production-like trace
        """
        sample = OnlineTraceSample(
            trace_id=trace.get("trace_id", "unknown"),
            agent_id=trace.get("agent_id", "unknown"),
            agent_version=trace.get("agent_version", "unknown"),
            payload=trace,
            sampled=False
        )

        # Sampling
        import random
        if random.random() < self.sample_rate:
            sample.sampled = True
            self.metrics["total_sampled"] += 1

        self.ingested.append(sample)
        self.metrics["total_ingested"] += 1

        # Online scoring
        self._score_and_alert(sample)

        return sample

    def _score_and_alert(self, sample: OnlineTraceSample):
        payload = sample.payload

        # Check P1 unsupported claim
        if payload.get("p1_failures", 0) > 0:
            self.metrics["p1_count"] += 1
            alert = OnlineAlert(
                alert_id=f"alert_{len(self.alerts)}",
                alert_type=OnlineAlertType.p1_unsupported_claim,
                severity="CRITICAL",
                trace_id=sample.trace_id,
                agent_id=sample.agent_id,
                description=f"P1 failure detected in trace {sample.trace_id}",
                metadata=payload
            )
            self.alerts.append(alert)

        # Tool error spike
        if payload.get("tool_errors", 0) > 3:
            self.metrics["tool_error_count"] += 1
            alert = OnlineAlert(
                alert_id=f"alert_{len(self.alerts)}",
                alert_type=OnlineAlertType.tool_error_spike,
                severity="WARNING",
                trace_id=sample.trace_id,
                agent_id=sample.agent_id,
                description=f"Tool error spike: {payload.get('tool_errors')} errors",
                metadata=payload
            )
            self.alerts.append(alert)

        # Latency regression
        latency = payload.get("latency_ms", 0)
        if latency > 5000:
            alert = OnlineAlert(
                alert_id=f"alert_{len(self.alerts)}",
                alert_type=OnlineAlertType.latency_regression,
                severity="WARNING",
                trace_id=sample.trace_id,
                agent_id=sample.agent_id,
                description=f"High latency: {latency}ms",
                metadata=payload
            )
            self.alerts.append(alert)

        # Abstention collapse
        abstention_rate = payload.get("abstention_rate", 1.0)
        if abstention_rate < 0.1:
            alert = OnlineAlert(
                alert_id=f"alert_{len(self.alerts)}",
                alert_type=OnlineAlertType.abstention_collapse,
                severity="WARNING",
                trace_id=sample.trace_id,
                agent_id=sample.agent_id,
                description=f"Abstention rate collapse: {abstention_rate}",
                metadata=payload
            )
            self.alerts.append(alert)

    def get_alerts(self, severity: Optional[str] = None) -> List[OnlineAlert]:
        if severity:
            return [a for a in self.alerts if a.severity == severity]
        return self.alerts

    def get_metrics(self) -> Dict[str, Any]:
        return self.metrics

    def get_sampled_traces(self) -> List[OnlineTraceSample]:
        return [t for t in self.ingested if t.sampled]
