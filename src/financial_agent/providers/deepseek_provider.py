"""
DeepSeek Provider — OpenAI-compatible, implements ModelProvider interface
Supports deepseek-chat and deepseek-reasoner (v4)

Cost: deepseek-chat ~ $0.14/1M input, $0.28/1M output — 50 tasks ~ $0.03-0.08
"""

import os
import time
from typing import Type
from pydantic import BaseModel

from .model_provider import ModelProvider
from ..schemas.common import ModelMetadata
from ..schemas.supervisor import SupervisorDecision, TaskType, Answerability, RiskLevel


class DeepSeekProvider(ModelProvider):
    """DeepSeek Flash v4 provider via OpenAI-compatible API"""
    
    def __init__(
        self,
        model_name: str = "deepseek-chat",
        prompt_version: str = "supervisor-v1-deepseek",
        api_key: str = None,
        base_url: str = "https://api.deepseek.com",
        temperature: float = 0.0,
        max_tokens: int = 1024
    ):
        self.model_name = model_name
        self.prompt_version = prompt_version
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY not set")
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Lazy import
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        except ImportError:
            raise ImportError("openai package required: pip install openai")
    
    def generate(self, prompt: str, **kwargs) -> tuple[str, ModelMetadata]:
        start = time.time()
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a financial agent supervisor. Be precise, evidence-grounded, and abstain when information is missing or contradictory."},
                    {"role": "user", "content": prompt}
                ],
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens)
            )
            text = response.choices[0].message.content
            usage = response.usage
            
            latency_ms = int((time.time() - start) * 1000)
            
            # DeepSeek pricing: chat $0.14/1M input, $0.28/1M output
            input_tokens = usage.prompt_tokens if usage else len(prompt)//4
            output_tokens = usage.completion_tokens if usage else len(text)//4
            cost = (input_tokens * 0.14 / 1_000_000) + (output_tokens * 0.28 / 1_000_000)
            
            meta = ModelMetadata(
                provider="deepseek",
                model_name=self.model_name,
                prompt_version=self.prompt_version,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                estimated_cost=cost
            )
            return text, meta
            
        except Exception as e:
            # Fallback metadata on error
            latency_ms = int((time.time() - start) * 1000)
            meta = ModelMetadata(
                provider="deepseek",
                model_name=self.model_name,
                prompt_version=self.prompt_version,
                input_tokens=len(prompt)//4,
                output_tokens=0,
                latency_ms=latency_ms,
                estimated_cost=0.0
            )
            raise e
    
    def generate_structured(self, prompt: str, schema: Type[BaseModel], **kwargs) -> tuple[BaseModel, ModelMetadata]:
        """Generate structured output — for SupervisorDecision we use JSON mode"""
        if schema == SupervisorDecision:
            # Use DeepSeek with JSON instruction for SupervisorDecision
            system_prompt = """You are a financial agent supervisor. Output JSON only with fields:
{
  "task_type": "pre_meeting_brief|credit_lookup|relationship_lookup|trading_lookup|conflict_check|false_premise|other",
  "answerability": "answerable|requires_internal_data|conflict_detected|incorrect_premise|tool_unavailable|injection_detected",
  "required_specialists": ["internal","research","analysis"] etc,
  "required_tools": ["client_lookup","credit_snapshot",...],
  "parallelisable": true/false,
  "risk_level": "low|medium|high|critical",
  "needs_human_review": true/false,
  "confidence": 0.0-1.0,
  "reasoning_summary": "brief"
}
Be evidence-grounded. If false premise, set incorrect_premise. If conflict, conflict_detected. If injection, injection_detected.
"""
            
            start = time.time()
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt + "\n\nOutput JSON only, no markdown."}
                    ],
                    temperature=0.0,
                    max_tokens=800,
                    response_format={"type": "json_object"} if "deepseek" in self.model_name else None
                )
                text = response.choices[0].message.content
                usage = response.usage
                latency_ms = int((time.time() - start) * 1000)
                
                # Parse JSON
                import json
                # Clean markdown if present
                if "```" in text:
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                    text = text.strip()
                
                data = json.loads(text)
                
                # Map to SupervisorDecision
                # Handle enum conversions
                task_type_map = {
                    "pre_meeting_brief": TaskType.pre_meeting_brief,
                    "credit_lookup": TaskType.credit_lookup,
                    "relationship_lookup": TaskType.relationship_lookup,
                    "trading_lookup": TaskType.trading_lookup,
                    "conflict_check": TaskType.conflict_check,
                    "false_premise": TaskType.false_premise,
                    "other": TaskType.other
                }
                answerability_map = {
                    "answerable": Answerability.answerable,
                    "requires_internal_data": Answerability.requires_internal_data,
                    "conflict_detected": Answerability.conflict_detected,
                    "incorrect_premise": Answerability.incorrect_premise,
                    "tool_unavailable": Answerability.tool_unavailable,
                    "injection_detected": Answerability.injection_detected,
                    "injection": Answerability.injection_detected
                }
                risk_map = {
                    "low": RiskLevel.low,
                    "medium": RiskLevel.medium,
                    "high": RiskLevel.high,
                    "critical": RiskLevel.critical
                }
                
                decision = SupervisorDecision(
                    task_type=task_type_map.get(data.get("task_type", "pre_meeting_brief"), TaskType.pre_meeting_brief),
                    answerability=answerability_map.get(data.get("answerability", "answerable"), Answerability.answerable),
                    required_specialists=data.get("required_specialists", ["internal", "research"]),
                    required_tools=data.get("required_tools", ["client_lookup", "document_search"]),
                    parallelisable=data.get("parallelisable", True),
                    risk_level=risk_map.get(data.get("risk_level", "medium"), RiskLevel.medium),
                    needs_human_review=data.get("needs_human_review", False),
                    confidence=float(data.get("confidence", 0.8)),
                    reasoning_summary=data.get("reasoning_summary", "DeepSeek supervisor decision")
                )
                
                input_tokens = usage.prompt_tokens if usage else len(prompt)//4
                output_tokens = usage.completion_tokens if usage else len(text)//4
                cost = (input_tokens * 0.14 / 1_000_000) + (output_tokens * 0.28 / 1_000_000)
                
                meta = ModelMetadata(
                    provider="deepseek",
                    model_name=self.model_name,
                    prompt_version=self.prompt_version,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    latency_ms=latency_ms,
                    estimated_cost=cost
                )
                return decision, meta
                
            except Exception as e:
                # Fallback to rule-based on error
                from .model_provider import RuleBasedSupervisorProvider
                rb = RuleBasedSupervisorProvider()
                decision, meta = rb.generate_structured(prompt, schema, **kwargs)
                meta.provider = "deepseek_fallback"
                meta.model_name = self.model_name
                return decision, meta
        else:
            # Generic fallback
            text, meta = self.generate(prompt, **kwargs)
            try:
                instance = schema.model_validate_json(text)
            except Exception:
                instance = schema.model_construct()
            return instance, meta
