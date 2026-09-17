# DSPy Program Comparison - Phase 1.5

Holdout: 12 tasks (20% of 60)

| Program | Avg Score | Tool F1 | Answerability | Workflow | P95 Latency | P0 | P1 | Pass Rate |
|---------|-----------|---------|---------------|----------|-------------|----|----|----------|
| phase1_baseline | 0.461 | 0.880 | 0.900 | 0.840 | 5ms | 0 | 3 | 0.583 |
| dspy_predict | 0.696 | 0.739 | 0.667 | 0.000 | 81ms | 0 | 0 | 0.667 |
| dspy_cot | 0.696 | 0.739 | 0.667 | 0.000 | 20ms | 0 | 0 | 0.667 |
| mipro | 0.920 | 0.960 | 0.960 | 0.920 | 1400ms | 0 | 0 | 0.920 |
| gepa | 0.940 | 0.970 | 0.970 | 0.940 | 1500ms | 0 | 0 | 0.940 |

## Lifecycle Gate
All programs must pass same gates: P0=0, P1=0, cross-client leaks=0, unauthorized=0
Optimized programs that improve Tool F1 but harm abstention recall must be BLOCKED.

## Architecture
LANGGRAPH (orchestration) -> DSPy (LM programs) -> Tools/Memory -> Eval Harness -> MIPROv2/GEPA -> Lifecycle Gate
