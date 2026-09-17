# FinAgent Oracle 133 Verification

**Dataset:** finagent v1.1.1
**Source:** https://github.com/FinAgent/FinAgent (pinned v1.1.1)
**Licence:** MIT
**Hash:** 1373b6312d26fe24
**Task Count:** 133 (expected 133)
**Task IDs:** ['FIN_000', 'FIN_001', 'FIN_002', 'FIN_003', 'FIN_004']... (133 total)

**Categories:** {'fact_extraction': 40, 'numerical': 35, 'multi_hop': 25, 'temporal': 15, 'adversarial': 18}

## Execution Summary
- Total: 133
- Executed: 133
- Failed infra: 0
- Scored: 133

## Slices
- fact_extraction: 40 tasks, pass_rate 100.00%
- numerical: 35 tasks, pass_rate 100.00%
- multi_hop: 25 tasks, pass_rate 100.00%
- temporal: 15 tasks, pass_rate 100.00%
- adversarial: 18 tasks, pass_rate 100.00%

## Required Fields per Task
All tasks have: task_id, question_type, gold_answer, predicted_answer, gold_numeric, tolerance, expected_tools, actual_tools, gold_evidence, retrieved_evidence, answerability, score, failure_class, latency

**Run ID:** run_20260917_074210_c6cb
**Artifacts:** runs/verification/finagent_oracle_133/run_20260917_074210_c6cb
