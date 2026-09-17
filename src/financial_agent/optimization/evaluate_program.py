"""
Evaluate DSPy programs on held-out tasks
Uses existing eval harness metrics + DSPy metric
"""
from typing import List, Dict, Any, Optional
import time
from pathlib import Path
import json
import dspy
from .datasets import DSPyOptimizationDataset
from .metrics import DSPyControlMetric
from ..dspy_programs.query_planner import dspy_to_supervisor_decision

def evaluate_dspy_program(program: dspy.Module, dataset: List[dspy.Example], metric: Optional[DSPyControlMetric] = None) -> Dict[str, Any]:
    metric = metric or DSPyControlMetric()

    # Ensure mock LM configured if no LM set
    try:
        _ = dspy.settings.lm
        if _ is None:
            from ..dspy_programs.query_planner import create_mock_dspy_lm
            dspy.settings.configure(lm=create_mock_dspy_lm())
    except:
        from ..dspy_programs.query_planner import create_mock_dspy_lm
        dspy.settings.configure(lm=create_mock_dspy_lm())

    results = []
    total_score = 0.0
    latencies = []
    failures = {"P0": 0, "P1": 0}

    for example in dataset:
        start = time.time()
        try:
            pred = program(
                request=example.request,
                memory_context=example.memory_context,
                available_sources=example.available_sources,
                available_tools=example.available_tools
            )
            latency = (time.time() - start) * 1000
            latencies.append(latency)

            score = metric(example, pred)
            total_score += score

            # Check for P0/P1
            if score == 0.0:
                # Determine if P0 or P1 based on expected answerability
                if example.answerability in ["incorrect_premise", "conflict_detected"]:
                    failures["P1"] += 1
                else:
                    failures["P1"] += 1  # Simplified

            results.append({
                "task_id": getattr(example, 'task_id', 'unknown'),
                "request": example.request,
                "expected_answerability": example.answerability,
                "predicted_answerability": getattr(pred, 'answerability', 'unknown'),
                "expected_tools": example.required_tools,
                "predicted_tools": getattr(pred, 'required_tools', []),
                "score": score,
                "latency_ms": latency,
                "passed": score > 0.5
            })

        except Exception as e:
            latency = (time.time() - start) * 1000
            latencies.append(latency)
            results.append({
                "task_id": getattr(example, 'task_id', 'unknown'),
                "request": example.request,
                "error": str(e),
                "score": 0.0,
                "latency_ms": latency,
                "passed": False
            })
            failures["P1"] += 1

    avg_score = total_score / len(dataset) if dataset else 0
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    p95_latency = sorted(latencies)[int(len(latencies)*0.95)] if latencies else 0

    # Calculate component metrics
    tool_f1_scores = []
    answerability_acc = []
    specialist_f1_scores = []
    human_review_acc = []

    for r in results:
        if "expected_tools" in r and "predicted_tools" in r:
            # Simple F1
            exp = set(r["expected_tools"])
            pred = set(r["predicted_tools"])
            if exp or pred:
                tp = len(exp.intersection(pred))
                prec = tp / len(pred) if pred else 0
                rec = tp / len(exp) if exp else 0
                f1 = 2*prec*rec/(prec+rec) if prec+rec>0 else 0
                tool_f1_scores.append(f1)

        if "expected_answerability" in r and "predicted_answerability" in r:
            answerability_acc.append(1.0 if r["expected_answerability"] == r["predicted_answerability"] else 0.0)

    summary = {
        "total_tasks": len(dataset),
        "avg_score": avg_score,
        "tool_f1": sum(tool_f1_scores)/len(tool_f1_scores) if tool_f1_scores else 0,
        "answerability_accuracy": sum(answerability_acc)/len(answerability_acc) if answerability_acc else 0,
        "avg_latency_ms": avg_latency,
        "p95_latency_ms": p95_latency,
        "p0_failures": failures["P0"],
        "p1_failures": failures["P1"],
        "pass_rate": len([r for r in results if r.get("passed")]) / len(results) if results else 0
    }

    return {
        "summary": summary,
        "results": results
    }

def evaluate_and_save(program: dspy.Module, program_name: str, dataset_split: str, output_dir: Path, metric: Optional[DSPyControlMetric] = None):
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load dataset
    ds = DSPyOptimizationDataset(size=60)
    if dataset_split == "train":
        examples = ds.to_dspy_examples("train")
    elif dataset_split == "dev":
        examples = ds.to_dspy_examples("dev")
    elif dataset_split == "holdout":
        examples = ds.to_dspy_examples("holdout")
    else:
        examples = ds.to_dspy_examples("holdout")

    evaluation = evaluate_dspy_program(program, examples, metric)

    # Save
    with open(output_dir / f"{program_name}_{dataset_split}_eval.json", "w") as f:
        json.dump(evaluation, f, indent=2, default=str)

    print(f"Evaluated {program_name} on {dataset_split}: avg_score={evaluation['summary']['avg_score']:.3f}, tool_f1={evaluation['summary']['tool_f1']:.3f}, answerability={evaluation['summary']['answerability_accuracy']:.3f}, p95={evaluation['summary']['p95_latency_ms']:.0f}ms, P1={evaluation['summary']['p1_failures']}")

    return evaluation
