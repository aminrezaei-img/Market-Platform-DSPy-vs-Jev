"""
Internal Data Provider Abstraction
Current: SyntheticInternalDataProvider
Future: DatabricksInternalDataProvider
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
from pathlib import Path
from ..schemas.tools import ToolResult, ToolStatus
from ..schemas.common import GovernanceMetadata

class InternalDataProvider(ABC):
    @abstractmethod
    def client_lookup(self, client_name: str = None, client_id: str = None) -> ToolResult:
        pass

    @abstractmethod
    def relationship_summary(self, client_id: str) -> ToolResult:
        pass

    @abstractmethod
    def credit_snapshot(self, client_id: str) -> ToolResult:
        pass

    @abstractmethod
    def trade_activity(self, client_id: str, days: int = 30) -> ToolResult:
        pass

    @abstractmethod
    def gl_summary(self, client_id: str) -> ToolResult:
        pass

class SyntheticInternalDataProvider(InternalDataProvider):
    """
    Deterministic synthetic data for 4 corporate clients exercising reliability conditions.
    Client A: Normal complete case
    Client B: Conflicting credit information
    Client C: Missing authoritative exposure field
    Client D: Tool/data availability failure
    """
    def __init__(self, data_path: Optional[Path] = None, simulate_failures: bool = False):
        self.simulate_failures = simulate_failures
        self.clients = self._load_fixtures()

    def _load_fixtures(self) -> Dict[str, Dict[str, Any]]:
        # Deterministic fixtures - no randomness during eval
        base_time = datetime(2026, 9, 10, 12, 0, 0)
        return {
            "nordic_industrial": {
                "client_id": "client_001",
                "client_name": "Nordic Industrial A/S",
                "cvr": "12345678",
                "industry": "Industrial Manufacturing",
                "country": "DK",
                "relationship": {
                    "coverage_banker": "Anders Jensen",
                    "relationship_tenure_years": 7,
                    "products": ["Revolving Credit Facility", "FX Hedging", "Cash Management"],
                    "risk_rating": "BBB+",
                    "last_review": "2026-06-15",
                    "next_review": "2026-12-15",
                    "relationship_summary": "Long-standing client in industrial sector. Stable cash flows, conservative management. Recent expansion into German market."
                },
                "credit": {
                    "limit": 800_000_000,
                    "exposure": 450_000_000,
                    "utilization_pct": 56.25,
                    "currency": "DKK",
                    "facility_type": "Revolving Credit Facility",
                    "maturity": "2027-06-30",
                    "collateral": "Corporate guarantee + receivables",
                    "covenants": ["Leverage <3.5x", "Interest coverage >4.0x"],
                    "last_updated": base_time.isoformat(),
                    "status": "performing"
                },
                "trades": {
                    "recent_trades": [
                        {"date": "2026-09-01", "type": "FX Forward", "notional": 50_000_000, "currency": "EUR/DKK", "counterparty": "Nordic Industrial"},
                        {"date": "2026-08-28", "type": "Interest Rate Swap", "notional": 200_000_000, "currency": "DKK", "counterparty": "Nordic Industrial"},
                    ],
                    "total_volume_30d": 320_000_000,
                    "pnl_30d": 1_200_000
                },
                "gl": {
                    "total_assets": 2_100_000_000,
                    "total_liabilities": 1_200_000_000,
                    "equity": 900_000_000,
                    "revenue_ytd": 1_800_000_000,
                    "ebitda_ytd": 320_000_000,
                    "last_updated": base_time.isoformat()
                }
            },
            "baltic_shipping": {
                "client_id": "client_002",
                "client_name": "Baltic Shipping Ltd",
                "cvr": "87654321",
                "industry": "Shipping & Logistics",
                "country": "DK",
                "relationship": {
                    "coverage_banker": "Mette Larsen",
                    "relationship_tenure_years": 4,
                    "products": ["Term Loan", "Trade Finance"],
                    "risk_rating": "BB",
                    "last_review": "2026-07-20",
                    "next_review": "2027-01-20",
                    "relationship_summary": "Cyclical shipping client. Exposure to freight rates. Recently requested limit increase."
                },
                "credit": {
                    # CONFLICT: This will conflict with CRM which says 800m vs here 900m for R03
                    "limit": 900_000_000,  # Conflicts with CRM 800m for R03 demo
                    "exposure": 720_000_000,
                    "utilization_pct": 80.0,
                    "currency": "DKK",
                    "facility_type": "Term Loan + RCF",
                    "maturity": "2028-03-15",
                    "collateral": "Vessel mortgage",
                    "covenants": ["LTV <70%", "DSCR >1.2x"],
                    "last_updated": (base_time - timedelta(days=2)).isoformat(),
                    "status": "performing with warning"
                },
                "trades": {
                    "recent_trades": [
                        {"date": "2026-09-05", "type": "Bunker Fuel Hedge", "notional": 30_000_000, "currency": "USD", "counterparty": "Baltic Shipping"},
                    ],
                    "total_volume_30d": 180_000_000,
                    "pnl_30d": -500_000
                },
                "gl": {
                    "total_assets": 3_500_000_000,
                    "total_liabilities": 2_800_000_000,
                    "equity": 700_000_000,
                    "revenue_ytd": 900_000_000,
                    "ebitda_ytd": 180_000_000,
                    "last_updated": base_time.isoformat()
                },
                # For conflict demo: CRM says 800m
                "crm_override": {
                    "credit_limit": 800_000_000
                }
            },
            "green_energy": {
                "client_id": "client_003",
                "client_name": "Green Energy Solutions A/S",
                "cvr": "11223344",
                "industry": "Renewable Energy",
                "country": "DK",
                "relationship": {
                    "coverage_banker": "Suresh Kette",
                    "relationship_tenure_years": 2,
                    "products": ["Project Finance", "Green Bond"],
                    "risk_rating": "BBB-",
                    "last_review": "2026-08-01",
                    "next_review": "2027-02-01",
                    "relationship_summary": "Growth stage renewable developer. Project finance heavy. Missing current exposure due to system migration."
                },
                "credit": {
                    # MISSING for R02
                    "limit": None,  # Missing
                    "exposure": None,  # Missing - system migration
                    "utilization_pct": None,
                    "currency": "DKK",
                    "facility_type": "Project Finance",
                    "maturity": "2030-12-31",
                    "collateral": "Project assets",
                    "covenants": ["DSCR >1.3x"],
                    "last_updated": None,
                    "status": "data_migration",
                    "migration_note": "Exposure data unavailable due to Databricks migration - contact Credit Ops"
                },
                "trades": {
                    "recent_trades": [],
                    "total_volume_30d": 0,
                    "pnl_30d": 0
                },
                "gl": {
                    "total_assets": 1_500_000_000,
                    "total_liabilities": 900_000_000,
                    "equity": 600_000_000,
                    "revenue_ytd": 400_000_000,
                    "ebitda_ytd": None,  # Missing
                    "last_updated": base_time.isoformat()
                }
            },
            "tech_ventures": {
                "client_id": "client_004",
                "client_name": "Tech Ventures A/S",
                "cvr": "55667788",
                "industry": "Technology",
                "country": "DK",
                "relationship": {
                    "coverage_banker": "Lars Nielsen",
                    "relationship_tenure_years": 1,
                    "products": ["Venture Debt"],
                    "risk_rating": "B+",
                    "last_review": "2026-08-20",
                    "next_review": "2026-11-20",
                    "relationship_summary": "Early stage tech. High risk, high growth. Data source intermittently unavailable."
                },
                "credit": {
                    "limit": 150_000_000,
                    "exposure": 120_000_000,
                    "utilization_pct": 80.0,
                    "currency": "DKK",
                    "facility_type": "Venture Debt",
                    "maturity": "2027-08-20",
                    "collateral": "IP + personal guarantee",
                    "covenants": ["Cash runway >6 months"],
                    "last_updated": base_time.isoformat(),
                    "status": "performing"
                },
                "trades": {
                    "recent_trades": [],
                    "total_volume_30d": 0,
                    "pnl_30d": 0
                },
                "gl": {
                    "total_assets": 300_000_000,
                    "total_liabilities": 200_000_000,
                    "equity": 100_000_000,
                    "revenue_ytd": 80_000_000,
                    "ebitda_ytd": -20_000_000,
                    "last_updated": base_time.isoformat()
                },
                "simulate_timeout": True  # For R04
            }
        }

    def _find_client(self, client_name: str = None, client_id: str = None) -> Optional[Dict[str, Any]]:
        if client_id:
            for c in self.clients.values():
                if c["client_id"] == client_id:
                    return c
        if client_name:
            # Fuzzy match
            lower = client_name.lower()
            for key, client in self.clients.items():
                if lower in client["client_name"].lower() or key in lower:
                    return client
                if client["client_id"].lower() == lower:
                    return client
            # Also try exact Nordic Industrial for default
            if "nordic" in lower:
                return self.clients["nordic_industrial"]
        return None

    def _make_governance(self, source: str, authoritative: bool = True, permitted: bool = True) -> GovernanceMetadata:
        return GovernanceMetadata(
            source=source,
            authoritative=authoritative,
            freshness_timestamp=datetime.utcnow(),
            permitted=permitted,
            provenance=f"synthetic_{source} v1",
            retrieved_at=datetime.utcnow()
        )

    def client_lookup(self, client_name: str = None, client_id: str = None) -> ToolResult:
        client = self._find_client(client_name, client_id)
        if not client:
            return ToolResult(
                tool_name="client_lookup",
                status=ToolStatus.not_found,
                data=None,
                error_code="CLIENT_NOT_FOUND",
                error_message=f"Client not found: {client_name} {client_id}",
                governance=self._make_governance("synthetic_crm", authoritative=True)
            )
        # Return minimal client info
        return ToolResult(
            tool_name="client_lookup",
            status=ToolStatus.success,
            data={
                "client_id": client["client_id"],
                "client_name": client["client_name"],
                "cvr": client["cvr"],
                "industry": client["industry"],
                "country": client["country"]
            },
            governance=self._make_governance("synthetic_crm", authoritative=True)
        )

    def relationship_summary(self, client_id: str) -> ToolResult:
        client = self._find_client(client_id=client_id)
        if not client:
            return ToolResult(
                tool_name="relationship_summary",
                status=ToolStatus.not_found,
                data=None,
                error_code="CLIENT_NOT_FOUND",
                governance=self._make_governance("synthetic_crm")
            )
        # For Baltic Shipping, simulate CRM conflict
        data = client["relationship"].copy()
        if client["client_id"] == "client_002" and "crm_override" in client:
            # CRM says 800m but credit snapshot says 900m - this is the conflict
            data["crm_credit_limit"] = client["crm_override"]["credit_limit"]

        return ToolResult(
            tool_name="relationship_summary",
            status=ToolStatus.success,
            data=data,
            governance=self._make_governance("synthetic_crm", authoritative=False)
        )

    def credit_snapshot(self, client_id: str) -> ToolResult:
        # Simulate timeout for client_004 if flag set
        client = self._find_client(client_id=client_id)
        if not client:
            return ToolResult(
                tool_name="credit_snapshot",
                status=ToolStatus.not_found,
                data=None,
                error_code="CLIENT_NOT_FOUND",
                governance=self._make_governance("synthetic_credit")
            )

        if client.get("simulate_timeout") and self.simulate_failures:
            return ToolResult(
                tool_name="credit_snapshot",
                status=ToolStatus.timeout,
                data=None,
                error_code="TIMEOUT",
                error_message="Credit system timeout after 5s - Databricks cluster starting",
                governance=self._make_governance("synthetic_credit", authoritative=True)
            )

        credit_data = client["credit"]
        # Check for missing
        if credit_data.get("exposure") is None and credit_data.get("limit") is None:
            return ToolResult(
                tool_name="credit_snapshot",
                status=ToolStatus.source_unavailable,
                data=credit_data,
                error_code="DATA_MIGRATION",
                error_message="Exposure data unavailable due to migration",
                governance=self._make_governance("synthetic_credit", authoritative=True)
            )

        # Check for conflict case - return success but data contains conflict marker
        if client["client_id"] == "client_002":
            # This will be detected by verifier comparing with CRM
            pass

        return ToolResult(
            tool_name="credit_snapshot",
            status=ToolStatus.success,
            data=credit_data,
            governance=self._make_governance("synthetic_credit", authoritative=True)
        )

    def trade_activity(self, client_id: str, days: int = 30) -> ToolResult:
        client = self._find_client(client_id=client_id)
        if not client:
            return ToolResult(
                tool_name="trade_activity",
                status=ToolStatus.not_found,
                data=None,
                error_code="CLIENT_NOT_FOUND",
                governance=self._make_governance("synthetic_trades")
            )
        return ToolResult(
            tool_name="trade_activity",
            status=ToolStatus.success,
            data=client["trades"],
            governance=self._make_governance("synthetic_trades", authoritative=True)
        )

    def gl_summary(self, client_id: str) -> ToolResult:
        client = self._find_client(client_id=client_id)
        if not client:
            return ToolResult(
                tool_name="gl_summary",
                status=ToolStatus.not_found,
                data=None,
                error_code="CLIENT_NOT_FOUND",
                governance=self._make_governance("synthetic_gl")
            )
        return ToolResult(
            tool_name="gl_summary",
            status=ToolStatus.success,
            data=client["gl"],
            governance=self._make_governance("synthetic_gl", authoritative=True)
        )

    def list_clients(self) -> List[Dict[str, Any]]:
        return [{"client_id": v["client_id"], "client_name": v["client_name"]} for v in self.clients.values()]
