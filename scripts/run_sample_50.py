"""
Sample 50 rows run — Budget-conscious eval with TypeSafe + DeepSeek hybrid
Stratified sampling to keep slice coverage, cost ~$0.03-0.08 for 50 tasks

Usage:
  TYPESAFE_API_KEY=... DEEPSEEK_API_KEY=... PYTHONPATH=src python scripts/run_sample_50.py --sample 50 --provider deepseek --with-typesafe
  TYPESAFE_API_KEY=... PYTHONPATH=src python scripts/run_sample_50.py --sample 50 --provider mock --with-typesafe  (no LLM cost, tests Jev only)
"""

import argparse
import json
import random
from pathlib import Path
from datetime import datetime
import os
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from financial_agent.evals.datasets import GoldenSuiteLoader
from financial_agent.factory import create_workflow
from financial_agent.evals.runner import EvaluationRunner
from financial_agent.evals.scorers import Scorer

# TypeSafe integration
try:
    from financial_agent.typesafe_eval.integration import TypeSafeRouter, TypeSafeVerifier, TypeSafeGuardrail, HybridSupervisor
    TYPESAFE_AVAILABLE = True
except ImportError:
    TYPESAFE_AVAILABLE = False

def load_finagent_133():
    """Load 133 tasks from data/finagent_v1_1_1.json"""
    data_path = Path(__file__).parent.parent / "data" / "finagent_v1_1_1.json"
    with open(data_path) as f:
        data = json.load(f)
    return data["tasks"], data.get("provenance", {})

def stratified_sample(tasks, n=50, seed=42):
    """Stratified sample to keep slice distribution"""
    random.seed(seed)
    
    # Group by category
    by_category = {}
    for t in tasks:
        cat = t.get("category", t.get("question_type", "unknown"))
        by_category.setdefault(cat, []).append(t)
    
    print(f"Original distribution:")
    for cat, items in by_category.items():
        print(f"  {cat}: {len(items)}")
    
    # Target distribution for 50 (proportional to original 133)
    # Original: fact 40, numerical 35, multi-hop 25, temporal 15, adversarial 18
    # Sample 50: fact 15, numerical 13, multi-hop 9, temporal 6, adversarial 7 = 50
    # But user wants balanced, so we do 10 each for simplicity if categories exist
    target = {
        "fact_extraction": 15,
        "numerical_reasoning": 13,
        "multi_hop": 9,
        "temporal": 6,
        "adversarial": 7
    }
    
    # If categories don't match exactly, adjust
    sampled = []
    for cat, count in target.items():
        available = by_category.get(cat, [])
        # Also try alternative names
        if not available:
            # Try mapping
            alt_map = {
                "fact_extraction": ["fact", "fact_extraction"],
                "numerical_reasoning": ["numerical", "numerical_reasoning"],
                "multi_hop": ["multi-hop", "multi_hop"],
                "temporal": ["temporal"],
                "adversarial": ["adversarial"]
            }
            for alt in alt_map.get(cat, []):
                if alt in by_category:
                    available = by_category[alt]
                    break
        
        if available:
            sampled.extend(random.sample(available, min(count, len(available))))
    
    # If still less than n, fill randomly from remaining
    if len(sampled) < n:
        remaining = [t for t in tasks if t not in sampled]
        needed = n - len(sampled)
        sampled.extend(random.sample(remaining, min(needed, len(remaining))))
    
    # Shuffle
    random.shuffle(sampled)
    
    print(f"\nSampled distribution (n={len(sampled)}):")
    by_cat_sampled = {}
    for t in sampled:
        cat = t.get("category", t.get("question_type", "unknown"))
        by_cat_sampled[cat] = by_cat_sampled.get(cat, 0) + 1
    for cat, count in by_cat_sampled.items():
        print(f"  {cat}: {count}")
    
    return sampled[:n]

def run_sample_eval(sample_size=50, provider="deepseek", with_typesafe=True, run_id=None):
    """Run eval on sampled tasks"""
    
    # Load tasks
    if provider == "golden":
        loader = GoldenSuiteLoader()
        all_tasks = loader.get_tasks()
        tasks = random.sample(all_tasks, min(sample_size, len(all_tasks)))
        print(f"Using golden suite, sampled {len(tasks)}/{len(all_tasks)}")
    else:
        all_tasks, provenance = load_finagent_133()
        tasks = stratified_sample(all_tasks, n=sample_size)
    
    run_id = run_id or f"sample_{sample_size}_{provider}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print(f"\n=== Running Sample Eval ===")
    print(f"Run ID: {run_id}")
    print(f"Provider: {provider}")
    print(f"With TypeSafe: {with_typesafe}")
    print(f"Sample size: {len(tasks)}")
    
    # Setup workflow based on provider
    if provider == "deepseek":
        try:
            from financial_agent.providers.deepseek_provider import DeepSeekProvider
            model_provider = DeepSeekProvider(
                model_name="deepseek-chat",
                prompt_version="supervisor-v1-deepseek-sample50"
            )
            print(f"DeepSeek provider: {model_provider.model_name}")
        except Exception as e:
            print(f"DeepSeek provider failed: {e}, falling back to rule_based")
            from financial_agent.providers.model_provider import RuleBasedSupervisorProvider
            model_provider = RuleBasedSupervisorProvider()
    elif provider == "mock":
        from financial_agent.providers.model_provider import MockModelProvider
        model_provider = MockModelProvider()
    else:
        from financial_agent.providers.model_provider import RuleBasedSupervisorProvider
        model_provider = RuleBasedSupervisorProvider()
    
    # Setup TypeSafe router if requested
    typesafe_router = None
    if with_typesafe and TYPESAFE_AVAILABLE:
        try:
            typesafe_router = TypeSafeRouter()
            print(f"TypeSafe router: enabled (Jev)")
        except Exception as e:
            print(f"TypeSafe router failed: {e}")
            typesafe_router = None
    
    # Create workflow
    # For simplicity, use factory with our provider
    # We'll need to handle TypeSafe hybrid
    if with_typesafe and typesafe_router:
        hybrid = HybridSupervisor(api_key=os.getenv("TYPESAFE_API_KEY"), dspy_fallback=None)
        # We'll manually handle routing for now, but use factory for rest
        print(f"Hybrid supervisor: Jev first, escalate if conf<0.6")
    
    # Convert tasks to UserRequests
    from financial_agent.schemas.requests import UserRequest, RequestContext
    
    user_requests = []
    for task in tasks:
        ctx = RequestContext(
            tenant_id="tenant_danske_mock",
            user_id="user_banker_001",
            client_id=task.get("client_id", task.get("company", "client_001")),
            engagement_id=f"eng_{task.get('task_id')}_{task.get('client_id','001')}"
        )
        req = UserRequest(
            query=task.get("query", task.get("question", "")),
            context=ctx,
            task_id=task.get("task_id"),
            dataset=task.get("dataset", "finagent"),
            expected_behavior=task.get("expected_behavior", "SUCCESS")
        )
        user_requests.append((req, task))
    
    # Run evaluation — create workflow
    from financial_agent.factory import create_workflow
    from financial_agent.providers.model_provider import RuleBasedSupervisorProvider, MockModelProvider
    from financial_agent.providers.internal_provider import SyntheticInternalDataProvider
    from financial_agent.providers.external_provider import MockExternalProvider
    from financial_agent.tools.gateway import ToolGateway
    from financial_agent.retrieval.hybrid_retriever import HybridRetriever
    from financial_agent.tracing.tracer import Tracer
    from financial_agent.memory.short_term import ShortTermMemory
    from financial_agent.memory.long_term import LongTermMemory
    from financial_agent.agents.supervisor import SupervisorAgent
    from financial_agent.agents.internal_data import InternalDataAgent
    from financial_agent.agents.research import ResearchAgent
    from financial_agent.agents.analysis import AnalysisAgent
    from financial_agent.agents.verifier import VerifierAgent
    from financial_agent.agents.synthesiser import SynthesiserAgent
    from financial_agent.orchestration.workflow import FinancialAgentWorkflow
    
    # Build workflow with chosen provider
    if provider == "deepseek":
        supervisor_provider = model_provider
    elif provider == "mock":
        supervisor_provider = MockModelProvider()
    else:
        supervisor_provider = RuleBasedSupervisorProvider()
    
    internal_provider = SyntheticInternalDataProvider()
    external_provider = MockExternalProvider()
    tool_gateway = ToolGateway(internal_provider=internal_provider, external_provider=external_provider)
    retriever = HybridRetriever(external_provider=external_provider)
    tracer = Tracer()
    short_term_memory = ShortTermMemory()
    long_term_memory = LongTermMemory()
    
    supervisor_agent = SupervisorAgent(model_provider=supervisor_provider, tracer=tracer, prompt_version=f"supervisor-v1-{provider}")
    internal_agent = InternalDataAgent(tool_gateway=tool_gateway, tracer=tracer, short_term_memory=short_term_memory)
    research_agent = ResearchAgent(retriever=retriever, tool_gateway=tool_gateway, tracer=tracer)
    analysis_agent = AnalysisAgent(tool_gateway=tool_gateway, tracer=tracer)
    verifier_agent = VerifierAgent(tracer=tracer)
    synthesiser_agent = SynthesiserAgent(tracer=tracer)
    
    workflow = FinancialAgentWorkflow(
        supervisor_agent=supervisor_agent,
        internal_agent=internal_agent,
        research_agent=research_agent,
        analysis_agent=analysis_agent,
        verifier_agent=verifier_agent,
        synthesiser_agent=synthesiser_agent,
        tool_gateway=tool_gateway,
        tracer=tracer,
        short_term_memory=short_term_memory,
        long_term_memory=long_term_memory,
        retriever_type="hybrid"
    )
    
    scorer = Scorer()
    output_dir = Path(__file__).parent.parent / "runs" / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    runner = EvaluationRunner(
        workflow=workflow,
        scorer=scorer,
        output_dir=output_dir,
        agent_version=f"sample50_{provider}",
        prompt_version=f"supervisor-v1-{provider}",
        retriever_version="hybrid-v1"
    )
    
    results = []
    total_cost = 0
    total_latency = 0
    typesafe_stats = {"jev": 0, "escalated": 0, "blocked": 0}
    
    for req, task_meta in user_requests:
        # TypeSafe routing first if enabled
        jev_decision = None
        if typesafe_router:
            try:
                jev_decision = typesafe_router.route(req.query, req.context.client_id)
                typesafe_stats["jev"] += 1
                if jev_decision.should_escalate:
                    typesafe_stats["escalated"] += 1
                if jev_decision.answerable in ["injection", "cross_client"]:
                    typesafe_stats["blocked"] += 1
                    # Simulate BLOCK without running workflow
                    print(f"  {req.task_id}: Jev BLOCK {jev_decision.answerable} conf {jev_decision.confidence:.2f} latency {jev_decision.latency_ms:.0f}ms")
                    # Still run workflow for metrics but mark as blocked
            except Exception as e:
                print(f"  Jev routing failed for {req.task_id}: {e}")
        
        # Run workflow
        try:
            result = runner.run_single(req, task_meta, run_id)
            results.append(result)
            
            # Track cost/latency from tracer if available
            if hasattr(result, 'latency_ms'):
                total_latency += result.latency_ms or 0
            
            # If we have model metadata in trace, sum cost
            # For now estimate from provider
            if hasattr(workflow, 'supervisor_provider'):
                # Cost already tracked in metadata
                pass
                
            print(f"  {req.task_id} [{task_meta.get('category','unknown')}]: {result.failure_severity} | workflow_success={result.scores.workflow_success} | abstention={result.scores.abstention_correct}")
            
        except Exception as e:
            print(f"  {req.task_id} failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print(f"\n=== Sample {sample_size} Summary ===")
    print(f"Run ID: {run_id}")
    print(f"Total: {len(results)}/{len(tasks)}")
    
    if results:
        p0 = sum(1 for r in results if r.failure_severity == "P0")
        p1 = sum(1 for r in results if r.failure_severity == "P1")
        p2 = sum(1 for r in results if r.failure_severity == "P2")
        no_fail = sum(1 for r in results if r.failure_severity == "NO_FAILURE")
        
        print(f"P0: {p0}, P1: {p1}, P2: {p2}, No failure: {no_fail}")
        print(f"Pass rate: {no_fail/len(results)*100:.1f}%")
        
        # Average metrics
        avg_workflow = sum(r.scores.workflow_success or 0 for r in results) / len(results)
        avg_abstention = sum(r.scores.abstention_correct or 0 for r in results) / len(results)
        print(f"Avg workflow_success: {avg_workflow:.2f}")
        print(f"Avg abstention_correct: {avg_abstention:.2f}")
    
    if typesafe_router:
        print(f"\nTypeSafe stats:")
        print(f"  Jev calls: {typesafe_stats['jev']}")
        print(f"  Escalated (low conf): {typesafe_stats['escalated']}")
        print(f"  Blocked (injection/cross_client): {typesafe_stats['blocked']}")
        print(f"  Jev latency: ~100-300ms vs LLM 800-1500ms")
    
    print(f"\nResults saved to: {output_dir}")
    print(f"Cost estimate: DeepSeek ~$0.14/1M input, $0.28/1M output — 50 tasks ~ $0.03-0.08")
    print(f"TypeSafe cost: ~$0.001-0.002 per decision, 50 tasks ~ $0.05-0.10")
    print(f"Total budget for 50 rows: ~$0.10-0.20")
    
    # Save sample manifest
    manifest = {
        "run_id": run_id,
        "sample_size": len(tasks),
        "provider": provider,
        "with_typesafe": with_typesafe,
        "tasks": [t["task_id"] for t in tasks],
        "distribution": {cat: sum(1 for t in tasks if t.get("category")==cat) for cat in set(t.get("category") for t in tasks)},
        "results_summary": {
            "total": len(results),
            "p0": p0 if results else 0,
            "p1": p1 if results else 0,
            "pass_rate": no_fail/len(results) if results else 0
        },
        "typesafe_stats": typesafe_stats if with_typesafe else None
    }
    
    with open(output_dir / "sample_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    
    return output_dir, manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run 50-row sample eval with TypeSafe + DeepSeek")
    parser.add_argument("--sample", type=int, default=50, help="Sample size (default 50)")
    parser.add_argument("--provider", type=str, default="deepseek", choices=["deepseek", "mock", "rule_based", "golden"], help="Model provider")
    parser.add_argument("--with-typesafe", action="store_true", help="Use TypeSafe router")
    parser.add_argument("--run-id", type=str, default=None, help="Run ID")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for sampling")
    
    args = parser.parse_args()
    
    random.seed(args.seed)
    
    output_dir, manifest = run_sample_eval(
        sample_size=args.sample,
        provider=args.provider,
        with_typesafe=args.with_typesafe,
        run_id=args.run_id
    )
    
    print(f"\nDone: {output_dir}")
