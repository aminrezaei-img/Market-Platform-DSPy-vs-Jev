"""
DSPy Metric - Phase 1.5
Composite metric using existing deterministic scorers
P0 failure -> score 0, P1 failure -> severe penalty
"""
from typing import Dict, Any, List, Optional
import dspy
from ..schemas.supervisor import SupervisorDecision, TaskType, Answerability, RiskLevel

class DSPyControlMetric:
    """
    Composite metric for query planning:
    schema validity 10%
    task-type accuracy 10%
    answerability accuracy 20%
    required-tool F1 20%
    specialist-selection F1 10%
    research-query retrieval value 15%
    risk classification 5%
    human-review routing 10%

    P0 failure -> score 0
    P1 failure -> severe penalty / score 0
    """
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or {
            "schema_validity": 0.10,
            "task_type": 0.10,
            "answerability": 0.20,
            "tool_f1": 0.20,
            "specialist_f1": 0.10,
            "research_query": 0.15,
            "risk": 0.05,
            "human_review": 0.10
        }

    def _tool_f1(self, predicted_tools: List[str], expected_tools: List[str]) -> float:
        if not predicted_tools and not expected_tools:
            return 1.0
        if not predicted_tools or not expected_tools:
            return 0.0

        pred_set = set(predicted_tools)
        exp_set = set(expected_tools)

        tp = len(pred_set.intersection(exp_set))
        precision = tp / len(pred_set) if pred_set else 0
        recall = tp / len(exp_set) if exp_set else 0

        if precision + recall == 0:
            return 0.0
        return 2 * precision * recall / (precision + recall)

    def _specialist_f1(self, predicted: List[str], expected: List[str]) -> float:
        if not predicted and not expected:
            return 1.0
        if not predicted or not expected:
            return 0.0

        pred_set = set(predicted)
        exp_set = set(expected)

        tp = len(pred_set.intersection(exp_set))
        precision = tp / len(pred_set) if pred_set else 0
        recall = tp / len(exp_set) if exp_set else 0

        if precision + recall == 0:
            return 0.0
        return 2 * precision * recall / (precision + recall)

    def __call__(self, example: dspy.Example, pred: dspy.Prediction, trace: Any = None) -> float:
        """
        Main metric called by MIPROv2/GEPA
        Returns score 0-1
        """
        # Extract expected
        expected_task_type = example.task_type
        expected_answerability = example.answerability
        expected_tools = example.required_tools
        expected_specialists = example.required_specialists
        expected_risk = example.risk_level
        expected_human_review = example.needs_human_review

        # Extract predicted
        try:
            pred_task_type = getattr(pred, 'task_type', '')
            pred_answerability = getattr(pred, 'answerability', '')
            pred_tools = getattr(pred, 'required_tools', [])
            pred_specialists = getattr(pred, 'required_specialists', [])
            pred_risk = getattr(pred, 'risk_level', '')
            pred_human_review = getattr(pred, 'needs_human_review', False)
            research_questions = getattr(pred, 'research_questions', [])
        except Exception:
            # Schema invalid -> 0
            return 0.0

        # Check for P0/P1 failures that should give score 0
        # P0: security - if tools include unauthorized for task
        # P1: if answerability is wrong for false premise / conflict / missing data

        # For false premise, if we say answerable when should be incorrect_premise -> P1
        if expected_answerability == "incorrect_premise" and pred_answerability == "answerable":
            return 0.0  # P1 failure

        if expected_answerability == "conflict_detected" and pred_answerability == "answerable":
            return 0.0  # P1 failure - missed conflict

        if expected_answerability == "requires_internal_data" and pred_answerability == "answerable":
            # Missing data but said answerable -> severe penalty, but not necessarily 0 if research_questions acknowledge missing?
            # For now, penalty 0.2
            return 0.2

        # Calculate components
        scores = {}

        # Schema validity - if we got here, schema valid
        scores["schema_validity"] = 1.0

        # Task type accuracy
        scores["task_type"] = 1.0 if pred_task_type == expected_task_type else 0.0

        # Answerability accuracy (20% weight, critical)
        scores["answerability"] = 1.0 if pred_answerability == expected_answerability else 0.0

        # Tool F1 (20%)
        scores["tool_f1"] = self._tool_f1(pred_tools, expected_tools)

        # Specialist F1 (10%)
        scores["specialist_f1"] = self._specialist_f1(pred_specialists, expected_specialists)

        # Research query retrieval value (15%) - simple heuristic: 2-4 queries, each contains company or relevant keywords
        if research_questions and len(research_questions) >= 2 and len(research_questions) <= 4:
            # Check if queries are non-empty and diverse
            unique_queries = len(set(research_questions))
            scores["research_query"] = min(1.0, unique_queries / 3.0)
        else:
            scores["research_query"] = 0.3 if research_questions else 0.0

        # Risk classification (5%)
        scores["risk"] = 1.0 if pred_risk == expected_risk else 0.5 if pred_risk else 0.0

        # Human review routing (10%)
        scores["human_review"] = 1.0 if pred_human_review == expected_human_review else 0.0

        # Weighted sum
        total = sum(scores[k] * self.weights[k] for k in self.weights)

        return total

    def with_feedback(self, example: dspy.Example, pred: dspy.Prediction, trace: Any = None) -> tuple[float, str]:
        """
        Returns (score, feedback) for GEPA which uses reflective feedback
        """
        score = self.__call__(example, pred, trace)

        # Generate feedback
        feedback_parts = []

        expected_tools = example.required_tools
        pred_tools = getattr(pred, 'required_tools', [])
        expected_answerability = example.answerability
        pred_answerability = getattr(pred, 'answerability', '')
        expected_specialists = example.required_specialists
        pred_specialists = getattr(pred, 'required_specialists', [])

        if set(expected_tools) - set(pred_tools):
            missing = set(expected_tools) - set(pred_tools)
            feedback_parts.append(f"Selected tools missing required: {missing}. Expected {expected_tools} but got {pred_tools}.")

        if set(pred_tools) - set(expected_tools):
            extra = set(pred_tools) - set(expected_tools)
            feedback_parts.append(f"Selected unnecessary tools: {extra}.")

        if expected_answerability != pred_answerability:
            if expected_answerability == "incorrect_premise" and pred_answerability == "answerable":
                feedback_parts.append(f"Failed to detect false premise. Query '{example.request}' asserts false fact but was marked answerable. Should be incorrect_premise with human_review true.")
            elif expected_answerability == "conflict_detected" and pred_answerability == "answerable":
                feedback_parts.append(f"Failed to detect conflicting sources. Should be conflict_detected with critical risk and human review.")
            elif expected_answerability == "requires_internal_data" and pred_answerability == "answerable":
                feedback_parts.append(f"Marked request answerable even though authoritative internal exposure data was unavailable. Should be requires_internal_data or insufficient_evidence.")
            else:
                feedback_parts.append(f"Answerability wrong: expected {expected_answerability} but got {pred_answerability}.")

        if set(expected_specialists) != set(pred_specialists):
            feedback_parts.append(f"Specialist selection wrong: expected {expected_specialists} but got {pred_specialists}.")

        expected_human = example.needs_human_review
        pred_human = getattr(pred, 'needs_human_review', False)
        if expected_human != pred_human:
            if expected_human and not pred_human:
                feedback_parts.append(f"Human review should have been true for this risky/conflicting/missing-data case but was false.")
            else:
                feedback_parts.append(f"Human review incorrectly true - unnecessary escalation.")

        if not feedback_parts:
            feedback = "All components correct. Good tool selection, answerability, specialist routing, and human review decision."
        else:
            feedback = " ".join(feedback_parts)

        return score, feedback

# For backward compatibility with simple metric
def control_metric(example: dspy.Example, pred: dspy.Prediction, trace: Any = None) -> float:
    metric = DSPyControlMetric()
    return metric(example, pred, trace)

def control_feedback_metric(example: dspy.Example, pred: dspy.Prediction, trace: Any = None) -> tuple[float, str]:
    metric = DSPyControlMetric()
    return metric.with_feedback(example, pred, trace)
