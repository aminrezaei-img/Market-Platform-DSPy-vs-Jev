#!/usr/bin/env python3
"""
Run DSPy optimization - MIPROv2 and GEPA - Phase 1.5
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import argparse
from financial_agent.optimization.run_mipro import run_mipro_optimization
from financial_agent.optimization.run_gepa import run_gepa_optimization
from financial_agent.optimization.compare_programs import compare_all_programs

def main():
    parser = argparse.ArgumentParser(description="Run DSPy Optimization")
    parser.add_argument("--optimizer", choices=["mipro", "gepa", "both", "compare"], default="both")
    parser.add_argument("--program-type", choices=["predict", "cot"], default="predict")
    parser.add_argument("--auto", default="light")
    args = parser.parse_args()

    if args.optimizer in ["mipro", "both"]:
        print("=== Running MIPROv2 ===")
        run_mipro_optimization(program_type=args.program_type, auto=args.auto)

    if args.optimizer in ["gepa", "both"]:
        print("\n=== Running GEPA ===")
        run_gepa_optimization(program_type=args.program_type, auto=args.auto)

    if args.optimizer in ["compare", "both"]:
        print("\n=== Comparing All Programs ===")
        compare_all_programs()

if __name__ == "__main__":
    main()
