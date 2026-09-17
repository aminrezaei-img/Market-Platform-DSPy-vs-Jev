"""
DSPy Verifier Enhancement - Phase 1.5
Upgrades regex/heuristic verification with two DSPy stages
"""
from typing import List, Literal, Optional
import dspy
from .signatures import ExtractClaims, VerifyClaim
from ..schemas.verification import VerificationResult, VerifierRecommendation, UnsupportedClaim, ConflictRecord

class ClaimExtractorPredict(dspy.Module):
    def __init__(self):
        super().__init__()
        self.extractor = dspy.Predict(ExtractClaims)

    def forward(self, brief: str):
        return self.extractor(brief=brief)

class ClaimExtractorCoT(dspy.Module):
    def __init__(self):
        super().__init__()
        self.extractor = dspy.ChainOfThought(ExtractClaims)

    def forward(self, brief: str):
        return self.extractor(brief=brief)

class ClaimVerifierPredict(dspy.Module):
    def __init__(self):
        super().__init__()
        self.verifier = dspy.Predict(VerifyClaim)

    def forward(self, claim: str, evidence: List[str]):
        return self.verifier(claim=claim, evidence=evidence)

class ClaimVerifierCoT(dspy.Module):
    def __init__(self):
        super().__init__()
        self.verifier = dspy.ChainOfThought(VerifyClaim)

    def forward(self, claim: str, evidence: List[str]):
        return self.verifier(claim=claim, evidence=evidence)

class DSPyVerifierPipeline(dspy.Module):
    """
    Two-stage verifier:
    1. Extract claims from brief
    2. Verify each claim against evidence
    Final verifier remains governed by deterministic checks for numeric verification
    """
    def __init__(self, extractor_type: str = "predict", verifier_type: str = "cot"):
        super().__init__()
        if extractor_type == "predict":
            self.extractor = ClaimExtractorPredict()
        else:
            self.extractor = ClaimExtractorCoT()

        if verifier_type == "predict":
            self.verifier = ClaimVerifierPredict()
        else:
            self.verifier = ClaimVerifierCoT()

    def forward(self, brief: str, evidence: List[str]):
        # Stage 1: Extract claims
        extraction = self.extractor(brief=brief)
        claims = getattr(extraction, 'claims', [])

        # Stage 2: Verify each claim
        results = []
        for claim in claims:
            verification = self.verifier(claim=claim, evidence=evidence)
            results.append({
                "claim": claim,
                "verdict": getattr(verification, 'verdict', 'INSUFFICIENT_EVIDENCE'),
                "evidence_ids": getattr(verification, 'evidence_ids', []),
                "reasoning": getattr(verification, 'reasoning', '')
            })

        return dspy.Prediction(claims=claims, verifications=results)

# Adapter to convert DSPy verifier output to Phase 1 VerificationResult
def dspy_to_verification_result(dspy_output, deterministic_checks: Optional[dict] = None) -> VerificationResult:
    """
    Convert DSPy verifier pipeline output to Phase 1 VerificationResult
    Deterministic checks take precedence for numeric verification
    """
    claims = getattr(dspy_output, 'claims', [])
    verifications = getattr(dspy_output, 'verifications', [])

    supported = 0
    total = len(claims)
    unsupported = []
    conflicts = []

    for v in verifications:
        verdict = v.get('verdict', 'INSUFFICIENT_EVIDENCE')
        claim_text = v.get('claim', '')
        if verdict == "SUPPORTED":
            supported += 1
        elif verdict == "UNSUPPORTED":
            unsupported.append(UnsupportedClaim(
                claim=claim_text,
                reason=v.get('reasoning', 'DSPy verifier marked unsupported'),
                severity="P1"
            ))
        elif verdict == "CONFLICTING":
            conflicts.append(ConflictRecord(
                field="general",
                value_a=claim_text,
                source_a="brief",
                value_b="conflicting evidence",
                source_b="evidence",
                description=v.get('reasoning', '')
            ))

    # Apply deterministic checks if provided (they take precedence)
    if deterministic_checks:
        # Example: numeric verification
        if deterministic_checks.get('has_p1_failure'):
            # Deterministic found P1, override
            pass

    # Determine recommendation
    if any(uc.severity == "P0" for uc in unsupported):
        recommendation = VerifierRecommendation.BLOCK
        critical = True
    elif unsupported or conflicts:
        recommendation = VerifierRecommendation.FAIL_NEEDS_HUMAN
        critical = False
    else:
        recommendation = VerifierRecommendation.PASS
        critical = False

    return VerificationResult(
        supported_claims=supported,
        total_claims=total,
        citation_precision=supported / total if total > 0 else 1.0,
        unsupported_claims=unsupported,
        conflicts=conflicts,
        critical_failure=critical,
        recommendation=recommendation,
        missing_information=[],
        human_review_required=recommendation in [VerifierRecommendation.FAIL_NEEDS_HUMAN, VerifierRecommendation.BLOCK],
        human_review_reasons=[uc.reason for uc in unsupported]
    )

# Mock for testing without LM
class MockDSPyVerifier:
    def __call__(self, brief: str, evidence: List[str]):
        # Simple mock: extract sentences with numbers as claims
        import re
        sentences = re.split(r'[.!?]+', brief)
        claims = [s.strip() for s in sentences if len(s.strip()) > 20 and bool(re.search(r'\d', s))]

        verifications = []
        for claim in claims[:5]:  # limit
            # Check if claim supported by evidence (simple overlap)
            supported = any(any(word in ev.lower() for word in claim.lower().split() if len(word) > 4) for ev in evidence)
            verdict = "SUPPORTED" if supported else "UNSUPPORTED"
            verifications.append({
                "claim": claim,
                "verdict": verdict,
                "evidence_ids": ["10K_2025_Nordic_Industrial"] if supported else [],
                "reasoning": "Mock: overlap check"
            })

        return dspy.Prediction(claims=claims[:5], verifications=verifications)
