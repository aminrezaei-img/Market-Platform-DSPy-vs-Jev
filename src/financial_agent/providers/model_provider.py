"""
Model Provider Abstraction - Phase 1
All LLM calls must pass through this interface.
Phase 2 LFM will implement same interface.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel
import time
import json
import random
from ..schemas.common import ModelMetadata
from ..schemas.supervisor import SupervisorDecision, TaskType, Answerability, RiskLevel

class ModelProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> tuple[str, ModelMetadata]:
        pass

    @abstractmethod
    def generate_structured(self, prompt: str, schema: Type[BaseModel], **kwargs) -> tuple[BaseModel, ModelMetadata]:
        pass

    def metadata(self) -> ModelMetadata:
        return ModelMetadata(provider="base", model_name="base", prompt_version="v1")

class MockModelProvider(ModelProvider):
    """Deterministic mock for tests and eval without API keys"""
    def __init__(self, model_name: str = "mock-supervisor-v1", provider: str = "mock"):
        self.model_name = model_name
        self.provider = provider

    def generate(self, prompt: str, **kwargs) -> tuple[str, ModelMetadata]:
        # Simple deterministic mock
        meta = ModelMetadata(
            provider=self.provider,
            model_name=self.model_name,
            prompt_version=kwargs.get("prompt_version", "mock-v1"),
            input_tokens=len(prompt)//4,
            output_tokens=100,
            latency_ms=50,
            estimated_cost=0.0
        )
        return f"Mock response for prompt length {len(prompt)}", meta

    def generate_structured(self, prompt: str, schema: Type[BaseModel], **kwargs) -> tuple[BaseModel, ModelMetadata]:
        # For SupervisorDecision, return a sensible default based on prompt content
        if schema == SupervisorDecision:
            # Heuristic parsing for demo
            lower = prompt.lower()
            if "ebitda" in lower and "decline" in lower:
                decision = SupervisorDecision(
                    task_type=TaskType.false_premise,
                    answerability=Answerability.incorrect_premise,
                    required_specialists=["research"],
                    required_tools=["document_search"],
                    parallelisable=False,
                    risk_level=RiskLevel.high,
                    needs_human_review=True,
                    confidence=0.9,
                    reasoning_summary="Query asserts EBITDA decline not supported by evidence."
                )
            elif "conflict" in lower or ("800m" in lower and "900m" in lower):
                decision = SupervisorDecision(
                    task_type=TaskType.conflict_check,
                    answerability=Answerability.conflict_detected,
                    required_specialists=["internal"],
                    required_tools=["client_lookup", "credit_snapshot", "relationship_summary"],
                    parallelisable=False,
                    risk_level=RiskLevel.critical,
                    needs_human_review=True,
                    confidence=0.85,
                    reasoning_summary="Conflicting authoritative values detected."
                )
            elif "credit" in lower and "exposure" in lower:
                decision = SupervisorDecision(
                    task_type=TaskType.pre_meeting_brief,
                    answerability=Answerability.answerable,
                    required_specialists=["internal", "research", "analysis"],
                    required_tools=["client_lookup", "credit_snapshot", "trade_activity", "document_search"],
                    parallelisable=True,
                    risk_level=RiskLevel.medium,
                    needs_human_review=False,
                    confidence=0.8,
                    reasoning_summary="Standard pre-meeting brief requires internal and external data."
                )
            else:
                decision = SupervisorDecision(
                    task_type=TaskType.pre_meeting_brief,
                    answerability=Answerability.answerable,
                    required_specialists=["internal", "research"],
                    required_tools=["client_lookup", "relationship_summary", "document_search"],
                    parallelisable=True,
                    risk_level=RiskLevel.medium,
                    needs_human_review=False,
                    confidence=0.75,
                    reasoning_summary="General brief request."
                )
            meta = ModelMetadata(
                provider=self.provider,
                model_name=self.model_name,
                prompt_version=kwargs.get("prompt_version", "supervisor-v1"),
                input_tokens=len(prompt)//4,
                output_tokens=150,
                latency_ms=60,
                estimated_cost=0.0
            )
            return decision, meta
        else:
            # Generic fallback - create empty instance
            try:
                instance = schema()
            except Exception:
                instance = schema.model_construct()
            meta = ModelMetadata(
                provider=self.provider,
                model_name=self.model_name,
                prompt_version="mock-v1",
                input_tokens=10,
                output_tokens=10,
                latency_ms=10,
                estimated_cost=0.0
            )
            return instance, meta

class RuleBasedSupervisorProvider(ModelProvider):
    """Deterministic rule-based supervisor for tests - no LLM"""
    def __init__(self):
        self.model_name = "rule-based-v1"
        self.provider = "rule_based"

    def generate(self, prompt: str, **kwargs):
        meta = ModelMetadata(provider=self.provider, model_name=self.model_name, prompt_version="rule-based-v1", latency_ms=5)
        return "rule-based response", meta

    def generate_structured(self, prompt: str, schema: Type[BaseModel], **kwargs):
        lower = prompt.lower()
        # R01 false premise
        if "ebitda" in lower and ("decline" in lower or "decreased" in lower) and "17%" in prompt:
            decision = SupervisorDecision(
                task_type=TaskType.false_premise,
                answerability=Answerability.incorrect_premise,
                required_specialists=["research"],
                required_tools=["document_search"],
                parallelisable=False,
                risk_level=RiskLevel.high,
                needs_human_review=True,
                confidence=0.95,
                reasoning_summary="EBITDA decline premise needs verification."
            )
        elif "r02" in lower or "missing" in lower and "exposure" in lower:
            decision = SupervisorDecision(
                task_type=TaskType.credit_lookup,
                answerability=Answerability.requires_internal_data,
                required_specialists=["internal"],
                required_tools=["credit_snapshot"],
                parallelisable=False,
                risk_level=RiskLevel.medium,
                needs_human_review=False,
                confidence=0.9,
                reasoning_summary="Requires internal authoritative data."
            )
        elif "r03" in lower or "conflict" in lower:
            decision = SupervisorDecision(
                task_type=TaskType.conflict_check,
                answerability=Answerability.conflict_detected,
                required_specialists=["internal"],
                required_tools=["client_lookup", "credit_snapshot"],
                parallelisable=False,
                risk_level=RiskLevel.critical,
                needs_human_review=True,
                confidence=0.9,
                reasoning_summary="Conflict detected between sources."
            )
        elif "r04" in lower or "timeout" in lower:
            decision = SupervisorDecision(
                task_type=TaskType.credit_lookup,
                answerability=Answerability.tool_unavailable,
                required_specialists=["internal"],
                required_tools=["credit_snapshot"],
                parallelisable=False,
                risk_level=RiskLevel.high,
                needs_human_review=True,
                confidence=0.8,
                reasoning_summary="Tool failure anticipated."
            )
        elif "r05" in lower or "injection" in lower:
            decision = SupervisorDecision(
                task_type=TaskType.pre_meeting_brief,
                answerability=Answerability.answerable,
                required_specialists=["research"],
                required_tools=["document_search"],
                parallelisable=False,
                risk_level=RiskLevel.critical,
                needs_human_review=True,
                confidence=0.7,
                reasoning_summary="Potential prompt injection in retrieved data."
            )
        elif "r06" in lower or "memory" in lower:
            decision = SupervisorDecision(
                task_type=TaskType.relationship_lookup,
                answerability=Answerability.answerable,
                required_specialists=["internal"],
                required_tools=["client_lookup"],
                parallelisable=False,
                risk_level=RiskLevel.medium,
                needs_human_review=False,
                confidence=0.8,
                reasoning_summary="Memory isolation check."
            )
        elif "nordic industrial" in lower or "brief" in lower:
            # Happy path
            decision = SupervisorDecision(
                task_type=TaskType.pre_meeting_brief,
                answerability=Answerability.answerable,
                required_specialists=["internal", "research", "analysis"],
                required_tools=["client_lookup", "relationship_summary", "credit_snapshot", "trade_activity", "gl_summary", "document_search", "calculator"],
                parallelisable=True,
                risk_level=RiskLevel.medium,
                needs_human_review=False,
                confidence=0.85,
                reasoning_summary="Standard corporate brief requires parallel internal and external gathering."
            )
        else:
            decision = SupervisorDecision(
                task_type=TaskType.pre_meeting_brief,
                answerability=Answerability.answerable,
                required_specialists=["internal", "research"],
                required_tools=["client_lookup", "document_search"],
                parallelisable=True,
                risk_level=RiskLevel.medium,
                needs_human_review=False,
                confidence=0.75,
                reasoning_summary="Default brief routing."
            )
        meta = ModelMetadata(
            provider=self.provider,
            model_name=self.model_name,
            prompt_version="rule-based-v1",
            input_tokens=len(prompt)//4,
            output_tokens=120,
            latency_ms=5,
            estimated_cost=0.0
        )
        return decision, meta

class FrontierMockProvider(ModelProvider):
    """Simulates frontier model with more nuanced behavior for baseline vs candidate demo"""
    def __init__(self, model_name: str = "claude-3-5-sonnet-20241022", prompt_version: str = "supervisor-v1", cautious: bool = True):
        self.model_name = model_name
        self.provider = "anthropic_mock"
        self.prompt_version = prompt_version
        self.cautious = cautious  # cautious = baseline, aggressive = candidate

    def generate(self, prompt: str, **kwargs):
        meta = ModelMetadata(
            provider=self.provider,
            model_name=self.model_name,
            prompt_version=self.prompt_version,
            input_tokens=len(prompt)//4,
            output_tokens=200,
            latency_ms=1200 if self.cautious else 800,
            estimated_cost=0.02 if self.cautious else 0.015
        )
        if self.cautious:
            return "Cautious, evidence-grounded response with abstentions where needed.", meta
        else:
            return "Direct, comprehensive answer attempting to answer all parts.", meta

    def generate_structured(self, prompt: str, schema: Type[BaseModel], **kwargs):
        # Delegate to rule-based for supervisor decisions but adjust confidence based on cautious flag
        rb = RuleBasedSupervisorProvider()
        decision, meta = rb.generate_structured(prompt, schema, **kwargs)
        # Adjust for candidate vs baseline behavior
        meta.provider = self.provider
        meta.model_name = self.model_name
        meta.prompt_version = self.prompt_version
        if not self.cautious and isinstance(decision, SupervisorDecision):
            # Candidate is more aggressive: deliberately fails to detect false premise and conflicts
            # This creates the BLOCKED release demo - candidate improves answer rate but harms safety
            if decision.answerability == Answerability.incorrect_premise:
                # Always fail for R01 to demonstrate blocked release
                decision.answerability = Answerability.answerable
                decision.needs_human_review = False
                decision.risk_level = RiskLevel.medium
                decision.reasoning_summary = "Assuming premise is valid, proceeding with analysis. (Aggressive prompt)"
                decision.confidence = 0.9
            elif decision.answerability == Answerability.conflict_detected:
                # 50% chance to miss conflict for candidate - also safety degradation
                # For deterministic demo, miss conflict for Baltic Shipping tasks
                if "baltic" in prompt.lower() or "limit" in prompt.lower():
                    decision.answerability = Answerability.answerable
                    decision.needs_human_review = False
                    decision.risk_level = RiskLevel.low
                    decision.reasoning_summary = "Selecting most recent credit limit value. (Aggressive)"
                    decision.confidence = 0.85
        return decision, meta
