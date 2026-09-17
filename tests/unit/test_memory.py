"""Unit tests for memory isolation"""
import pytest
from src.financial_agent.memory.short_term import ShortTermMemory
from src.financial_agent.memory.long_term import LongTermMemory
from src.financial_agent.schemas.memory import MemoryItem, MemoryType

def test_short_term_memory():
    stm = ShortTermMemory()
    ctx = stm.create_engagement(
        tenant_id="tenant_1",
        user_id="user_1",
        client_id="client_001",
        engagement_id="eng_001"
    )
    assert ctx["client_id"] == "client_001"

    stm.add_message("eng_001", "user", "Prepare brief")
    assert len(stm.get("eng_001")["conversation_history"]) == 1

    stm.update_facts("eng_001", {"exposure": 450})
    assert stm.get("eng_001")["facts"]["exposure"] == 450

def test_long_term_memory_no_authoritative():
    ltm = LongTermMemory()
    # Should fail if trying to store authoritative exposure
    item = MemoryItem(
        tenant_id="tenant_1",
        user_id="user_1",
        client_id="client_001",
        memory_type=MemoryType.long_term_preference,
        content={"credit_exposure": 450_000_000},
        is_authoritative=True,
        source="test"
    )
    with pytest.raises(ValueError):
        ltm.store(item)

    # Should succeed for non-authoritative preference
    item2 = MemoryItem(
        tenant_id="tenant_1",
        user_id="user_1",
        client_id=None,
        memory_type=MemoryType.long_term_preference,
        content={"brief_format": "bullet_points"},
        is_authoritative=False,
        source="user"
    )
    assert ltm.store(item2) == True

def test_memory_isolation_r06():
    ltm = LongTermMemory()

    # Store memory for Client A
    item_a = MemoryItem(
        tenant_id="tenant_danske_mock",
        user_id="user_banker_001",
        client_id="client_001",
        memory_type=MemoryType.long_term_decision,
        content={"risk_appetite": "conservative", "note": "Client A is conservative"},
        is_authoritative=False,
        source="analyst"
    )
    ltm.store(item_a)

    # Store user preference (should be retrievable for all clients)
    pref = MemoryItem(
        tenant_id="tenant_danske_mock",
        user_id="user_banker_001",
        client_id=None,
        memory_type=MemoryType.long_term_preference,
        content={"brief_format": "detailed"},
        is_authoritative=False,
        source="user"
    )
    ltm.store(pref)

    # Retrieve for Client B - should NOT get Client A specific memory
    results_b = ltm.retrieve_client_isolated(
        tenant_id="tenant_danske_mock",
        user_id="user_banker_001",
        client_id="client_002"
    )

    # Should only have user preference, not Client A memory
    client_ids = [r.client_id for r in results_b]
    assert "client_001" not in client_ids
    # Should have None (user-scoped) and possibly client_002 if any
    assert all(cid in [None, "client_002"] for cid in client_ids)

    # Retrieve for Client A - should get Client A memory
    results_a = ltm.retrieve_client_isolated(
        tenant_id="tenant_danske_mock",
        user_id="user_banker_001",
        client_id="client_001"
    )
    assert any(r.client_id == "client_001" for r in results_a)
    assert any("conservative" in str(r.content) for r in results_a)

def test_cross_client_leak_p0():
    ltm = LongTermMemory()
    item_a = MemoryItem(
        tenant_id="tenant_danske_mock",
        user_id="user_banker_001",
        client_id="client_001",
        memory_type=MemoryType.long_term_decision,
        content={"risk_appetite": "conservative"},
        is_authoritative=False,
        source="analyst"
    )
    ltm.store(item_a)

    # Try to retrieve with wrong isolation - direct retrieve that includes client_001 for client_002 should fail
    # Our retrieve_client_isolated should prevent leak, but test that direct DB query would be caught
    # Actually retrieve_client_isolated is designed to prevent leak, so it should PASS (no leak)
    # To simulate leak, we need to check that if someone bypasses isolation, it's detected

    # This should NOT leak
    results = ltm.retrieve_client_isolated("tenant_danske_mock", "user_banker_001", "client_002")
    assert not any(r.client_id == "client_001" for r in results)
