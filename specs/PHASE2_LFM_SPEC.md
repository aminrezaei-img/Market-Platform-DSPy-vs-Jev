# PHASE2_LFM_SPEC.md - Future Small Model Specialisation

**Status:** FROZEN INTERFACE ONLY - NO IMPLEMENTATION IN PHASE 1
**Date:** 2026-09-15

## 1. Purpose
Define interfaces so Phase 2 can replace supervisor/router with fine-tuned LFM model without changing surrounding architecture.

Phase 1 must not implement training. Only scaffolding for replacement.

## 2. Supervisor Provider Interface

```python
class SupervisorProvider(Protocol):
    def decide(self, request: UserRequest, context: MemoryContext) -> SupervisorDecision: ...
    def metadata(self) -> ModelMetadata: ...
```

Current implementations:
- FrontierSupervisor (Bedrock Claude / OpenAI / local mock)
- RuleBasedSupervisor (deterministic for tests)

Future implementations (Phase 2):
- LFM12BSupervisor (LFM2.5-1.2B-Instruct fine-tuned)
- LFM26BSupervisor (LFM2.5-2.6B baseline)
- HybridSupervisor (cascade: LFM for control, frontier for reasoning)

No other agent should need modification when supervisor provider swapped.

## 3. Model Provider Abstraction (Already in Phase 1)
```python
class ModelProvider:
    def generate(prompt, ...): ...
    def generate_structured(prompt, schema, ...): ...
    def metadata(...): ModelMetadata
```

Future:
```python
class LFMRouterProvider(ModelProvider):
    model_name = "LFM2.5-1.2B-FinAgent-LoRA"
```

## 4. Training Data Interface (Phase 2)
Training data will come from:
- TauIndianBankBench 40 families -> supervisor JSON labels (task_type, answerability, required_tools, risk_level)
- Generated control examples (optional)

Must be split by scenario family to avoid leakage:
- 40 families train/dev
- 10 families held-out Test A
- FinAgent adversarial 43 Test B (never trained)
- Golden R01-R06 Test C

FinAgent must NEVER be used for training. Only external evaluation.

## 5. Hypothesis (Phase 2)
H1: Domain-specialized 1.2B can match frontier on constrained control tasks (routing, tool selection, answerability) while reducing latency/cost >60%
H2: Specialization helps control tasks more than open-ended financial reasoning

Metrics for Phase 2:
- Task classification macro F1
- Tool selection EM, precision, recall
- Answerability accuracy, false-premise detection
- Abstention precision/recall
- Latency p50/p95, VRAM, tokens/sec, estimated cost
- Escalation rate for hybrid cascade

Decision rule example:
IF confidence >0.85 AND task in {routing, tool_selection, answerability} -> use LFM 1.2B fine-tuned ELSE escalate to frontier

## 6. Evaluation Reuse
Phase 1 evaluation platform must be usable unchanged for Phase 2:
- Same tasks, traces, metrics, failure taxonomy, release gates
- Evaluation runner must accept any SupervisorProvider

## 7. Licensing Note
LFM models use LFM Open License v1.0, not MIT/Apache. Free research/academic use, certain commercial conditions. Flag legal review for production. No issue for interview prototype.

## 8. Stretch Experiments (Phase 2 only)
- 230M fine-tune for same task to show operating envelope
- Graph: 230M -> 1.2B -> 2.6B -> frontier for routing accuracy

## 9. What Phase 1 Must Provide
- SupervisorProvider protocol
- ModelProvider protocol
- Config to swap supervisor via models.yaml
- Trace captures model_provider, model_name, prompt_version so Phase 2 runs comparable
- No training code, no LoRA, no Unsloth import in Phase 1

## 10. Success Criteria for Phase 2 (Not Implemented Now)
Platform can answer: Does LFM specialist deserve responsibility for control plane? Where does it fail? What is competence boundary? What is cascade tradeoff (risk reduction vs cost vs latency)?
