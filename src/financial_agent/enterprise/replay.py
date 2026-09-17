"""
Replay Evaluation - important enterprise capability per spec 21
"""
from typing import Dict, Any, Optional, List
from pathlib import Path
import json
from .trace_bus import TraceBus, CanonicalTraceEvent, TraceEventType

class ReplayEngine:
    """
    Persist enough info to replay prior task against new model/program/tool
    """
    def __init__(self, trace_bus: Optional[TraceBus] = None):
        self.trace_bus = trace_bus or TraceBus()

    def replay(
        self,
        original_trace_id: str,
        candidate_agent_id: str,
        candidate_version: str,
        new_model_versions: Optional[Dict[str, str]] = None,
        new_program_version: Optional[str] = None,
        new_tool_versions: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Replay original request against candidate
        """
        # Get original trace
        replay_info = self.trace_bus.replay_ready(original_trace_id)
        original_request = replay_info.get("original_request", {})

        if not original_request:
            # Try to load from trace file
            events = self.trace_bus.get_events(original_trace_id)
            request_events = [e for e in events if e.event_type == TraceEventType.request_received]
            if request_events:
                original_request = request_events[0].payload

        # Simulate replay - in real system would execute agent
        # For reference implementation, return replay plan

        replay_result = {
            "original_trace_id": original_trace_id,
            "candidate": f"{candidate_agent_id}@{candidate_version}",
            "original_request": original_request,
            "new_model_versions": new_model_versions or {},
            "new_program_version": new_program_version,
            "new_tool_versions": new_tool_versions or {},
            "replay_timestamp": "2026-09-15T00:00:00Z",
            "status": "replayed",
            "comparison": {
                "original_artifact_versions": replay_info.get("artifact_versions", {}),
                "candidate_artifact_versions": {
                    **(new_model_versions or {}),
                    "program": new_program_version or "unknown",
                    **(new_tool_versions or {})
                }
            }
        }

        return replay_result

    def batch_replay(
        self,
        trace_ids: List[str],
        candidate_agent_id: str,
        candidate_version: str
    ) -> List[Dict[str, Any]]:
        results = []
        for trace_id in trace_ids:
            result = self.replay(trace_id, candidate_agent_id, candidate_version)
            results.append(result)
        return results

    def compare_replay(
        self,
        original_trace_id: str,
        replay_result: Dict[str, Any],
        original_eval: Dict[str, Any],
        candidate_eval: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare original vs replayed evaluation
        """
        diff = {}
        for key in ["avg_score", "tool_f1", "answerability"]:
            if key in original_eval and key in candidate_eval:
                diff[key] = candidate_eval[key] - original_eval[key]

        return {
            "original_trace_id": original_trace_id,
            "original_eval": original_eval,
            "candidate_eval": candidate_eval,
            "diff": diff,
            "regression": any(v < -0.05 for v in diff.values()),
            "improvement": any(v > 0.05 for v in diff.values())
        }
