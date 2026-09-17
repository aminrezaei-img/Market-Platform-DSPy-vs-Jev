#!/usr/bin/env python3
"""
Run DSPy evaluation - Phase 1.5
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import argparse
import dspy
from financial_agent.optimization.datasets import DSPyOptimizationDataset
from financial_agent.optimization.metrics import DSPyControlMetric
from financial_agent.optimization.evaluate_program import evaluate_dspy_program, evaluate_and_save
from financial_agent.dspy_programs.query_planner import QueryPlannerPredict, QueryPlannerCoT, MockDSPyLM

def main():
    parser = argparse.ArgumentParser(description="Run DSPy Program Evaluation")
    parser.add_argument("--program", choices=["predict", "cot", "both"], default="both")
    parser.add_argument("--split", choices=["train", "dev", "holdout"], default="holdout")
    parser.add_argument("--size", type=int, default=60)
    args = parser.parse_args()

    print(f"=== DSPy Evaluation - {args.program} on {args.split} ===")

    # Mock LM for testing without API keys - use dict mode DummyLM
    from financial_agent.dspy_programs.query_planner import create_mock_dspy_lm
    mock_lm = create_mock_dspy_lm()
    dspy.settings.configure(lm=mock_lm)

    ds = DSPyOptimizationDataset(size=args.size)
    if args.split == "train":
        examples = ds.to_dspy_examples("train")
    elif args.split == "dev":
        examples = ds.to_dspy_examples("dev")
    else:
        examples = ds.to_dspy_examples("holdout")

    print(f"Dataset: {ds.summary()}")
    print(f"Evaluating on {args.split}: {len(examples)} examples")

    metric = DSPyControlMetric()

    if args.program in ["predict", "both"]:
        print("\n--- Predict ---")
        program = QueryPlannerPredict()
        eval_result = evaluate_dspy_program(program, examples, metric)
        print(f"Predict: avg_score={eval_result['summary']['avg_score']:.3f}, tool_f1={eval_result['summary']['tool_f1']:.3f}, answerability={eval_result['summary']['answerability_accuracy']:.3f}")

    if args.program in ["cot", "both"]:
        print("\n--- ChainOfThought ---")
        program = QueryPlannerCoT()
        eval_result = evaluate_dspy_program(program, examples, metric)
        print(f"CoT: avg_score={eval_result['summary']['avg_score']:.3f}, tool_f1={eval_result['summary']['tool_f1']:.3f}, answerability={eval_result['summary']['answerability_accuracy']:.3f}")

if __name__ == "__main__":
    main()
