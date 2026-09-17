"""
Factory to build workflow with all dependencies
"""
from pathlib import Path
from .providers.model_provider import RuleBasedSupervisorProvider, MockModelProvider, FrontierMockProvider
from .providers.internal_provider import SyntheticInternalDataProvider
from .providers.external_provider import MockExternalProvider
from .tools.gateway import ToolGateway
from .retrieval.hybrid_retriever import HybridRetriever
from .tracing.tracer import Tracer
from .memory.short_term import ShortTermMemory
from .memory.long_term import LongTermMemory
from .agents.supervisor import SupervisorAgent
from .agents.internal_data import InternalDataAgent
from .agents.research import ResearchAgent
from .agents.analysis import AnalysisAgent
from .agents.verifier import VerifierAgent
from .agents.synthesiser import SynthesiserAgent
from .orchestration.workflow import FinancialAgentWorkflow

def create_workflow(
    supervisor_type: str = "rule_based",  # rule_based, mock, frontier_cautious, frontier_aggressive, deepseek, typesafe_deepseek, typesafe_mock, typesafe_rule_based
    prompt_version: str = "supervisor-v1",
    retriever_type: str = "hybrid",
    tracer: Tracer = None,
    short_term_memory: ShortTermMemory = None,
    long_term_memory: LongTermMemory = None,
    simulate_failures: bool = False,
    with_typesafe: bool = False,
    typesafe_api_key: str = None,
    deepseek_api_key: str = None
) -> FinancialAgentWorkflow:

    # Providers
    if supervisor_type == "rule_based":
        model_provider = RuleBasedSupervisorProvider()
    elif supervisor_type == "mock":
        model_provider = MockModelProvider(model_name="mock-supervisor-v1")
    elif supervisor_type == "frontier_cautious":
        model_provider = FrontierMockProvider(model_name="claude-3-5-sonnet-20241022", prompt_version=prompt_version, cautious=True)
    elif supervisor_type == "frontier_aggressive":
        model_provider = FrontierMockProvider(model_name="claude-3-5-sonnet-20241022", prompt_version=prompt_version, cautious=False)
    elif supervisor_type == "deepseek":
        try:
            from .providers.deepseek_provider import DeepSeekProvider
            model_provider = DeepSeekProvider(
                model_name="deepseek-chat",
                prompt_version=prompt_version,
                api_key=deepseek_api_key
            )
        except Exception as e:
            print(f"DeepSeek provider failed: {e}, falling back to rule_based")
            model_provider = RuleBasedSupervisorProvider()
    elif supervisor_type in ["typesafe_deepseek", "typesafe_mock", "typesafe_rule_based"]:
        # TypeSafe hybrid: Jev router + underlying LLM provider
        # For factory, we still need a model_provider for supervisor, but we'll wrap with HybridSupervisor
        # The underlying provider is deepseek/mock/rule_based
        underlying = supervisor_type.replace("typesafe_", "")
        if underlying == "deepseek":
            try:
                from .providers.deepseek_provider import DeepSeekProvider
                base_provider = DeepSeekProvider(
                    model_name="deepseek-chat",
                    prompt_version=prompt_version,
                    api_key=deepseek_api_key
                )
            except Exception as e:
                print(f"DeepSeek failed: {e}, fallback to rule_based")
                base_provider = RuleBasedSupervisorProvider()
        elif underlying == "mock":
            base_provider = MockModelProvider(model_name="mock-supervisor-v1")
        else:
            base_provider = RuleBasedSupervisorProvider()
        
        # Try to create TypeSafe hybrid wrapper
        try:
            from .typesafe_eval.integration import HybridSupervisor
            # HybridSupervisor will be used in workflow, but for factory we need to store it
            # We'll create a special provider that delegates to HybridSupervisor
            from .providers.model_provider import ModelProvider
            from ..schemas.common import ModelMetadata
            from ..schemas.supervisor import SupervisorDecision
            import os
            
            # Store hybrid for later use in workflow — for now use base provider
            # Actual Jev routing will be done in workflow via with_typesafe flag
            model_provider = base_provider
            with_typesafe = True
        except Exception as e:
            print(f"TypeSafe hybrid failed: {e}, using base provider")
            model_provider = base_provider
    else:
        model_provider = RuleBasedSupervisorProvider()

    internal_provider = SyntheticInternalDataProvider(simulate_failures=simulate_failures)
    external_provider = MockExternalProvider()

    tool_gateway = ToolGateway(internal_provider=internal_provider, external_provider=external_provider)

    retriever = HybridRetriever(external_provider=external_provider)

    tracer = tracer or Tracer()
    short_term_memory = short_term_memory or ShortTermMemory()
    long_term_memory = long_term_memory or LongTermMemory()

    # Agents — with optional TypeSafe integration
    # If with_typesafe, wrap supervisor with HybridSupervisor and verifier with TypeSafeVerifier
    typesafe_router = None
    typesafe_verifier = None
    typesafe_guardrail = None
    
    if with_typesafe:
        try:
            from .typesafe_eval.integration import TypeSafeRouter, TypeSafeVerifier, TypeSafeGuardrail
            import os
            api_key = typesafe_api_key or os.getenv("TYPESAFE_API_KEY")
            if api_key:
                typesafe_router = TypeSafeRouter(api_key=api_key)
                typesafe_verifier = TypeSafeVerifier(api_key=api_key)
                typesafe_guardrail = TypeSafeGuardrail(api_key=api_key)
                print(f"TypeSafe enabled: Jev router + verifier + guardrail")
        except Exception as e:
            print(f"TypeSafe integration failed: {e}, continuing without")
    
    supervisor_agent = SupervisorAgent(model_provider=model_provider, tracer=tracer, prompt_version=prompt_version)
    # Attach TypeSafe components to supervisor agent for hybrid routing
    if typesafe_router:
        supervisor_agent.typesafe_router = typesafe_router
        supervisor_agent.typesafe_guardrail = typesafe_guardrail
        supervisor_agent.with_typesafe = True
    
    internal_agent = InternalDataAgent(tool_gateway=tool_gateway, tracer=tracer, short_term_memory=short_term_memory)
    research_agent = ResearchAgent(retriever=retriever, tool_gateway=tool_gateway, tracer=tracer)
    analysis_agent = AnalysisAgent(tool_gateway=tool_gateway, tracer=tracer)
    verifier_agent = VerifierAgent(tracer=tracer)
    if typesafe_verifier:
        verifier_agent.typesafe_verifier = typesafe_verifier
        verifier_agent.with_typesafe = True
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
        retriever_type=retriever_type
    )

    return workflow
