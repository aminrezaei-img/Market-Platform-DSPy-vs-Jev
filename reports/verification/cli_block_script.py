
import sys
sys.path.insert(0, 'src')
from financial_agent.enterprise.evidence_pack import EvidencePackGenerator
generator = EvidencePackGenerator()
mock_results = {"metrics": {"accuracy": 0.90}, "p0_failures": 0, "p1_failures": 1, "model_versions": {}, "datasets": [], "scorer_versions": []}
pack = generator.generate(
    candidate_identity="markets.pre_meeting_brief@1.3.0-unsafe",
    baseline_identity="markets.pre_meeting_brief@1.2.0",
    experiment_results=mock_results,
    evidence_type="measured"
)
print(f"Decision: {pack.lifecycle_decision}")
print(f"P1 increased 0 -> 1")
sys.exit(1 if pack.lifecycle_decision == "BLOCK" else 0)
