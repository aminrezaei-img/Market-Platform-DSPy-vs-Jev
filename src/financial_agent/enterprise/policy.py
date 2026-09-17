"""
Policy / Entitlement Layer - lightweight rules-based
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from enum import Enum

class PolicyDecision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"

class PolicyInput(BaseModel):
    identity: str = "user_banker_001"
    agent: str = "markets.pre_meeting_brief"
    agent_version: str = "1.2.0"
    client: Optional[str] = None
    tool: str = "client_lookup"
    action: str = "read"  # read, write, mutate
    tenant_id: str = "tenant_danske_mock"
    user_id: str = "user_banker_001"

class PolicyRule(BaseModel):
    id: str
    description: str
    agent_pattern: str = "*"  # supports * wildcard or exact
    tool_pattern: str = "*"
    action_pattern: str = "*"
    decision: PolicyDecision
    priority: int = 100  # lower = higher priority

class PolicyEngine:
    """
    Lightweight policy abstraction per spec section 9
    Input: identity, agent, client, tool, action
    Output: ALLOW, DENY, REQUIRE_APPROVAL
    All decisions traced
    """
    def __init__(self):
        self.rules: List[PolicyRule] = self._default_rules()
        self.decision_log: List[Dict[str, Any]] = []

    def _default_rules(self) -> List[PolicyRule]:
        return [
            PolicyRule(
                id="research_no_credit",
                description="research_agent cannot call credit_snapshot",
                agent_pattern="research*",
                tool_pattern="credit_snapshot",
                action_pattern="*",
                decision=PolicyDecision.DENY,
                priority=10
            ),
            PolicyRule(
                id="research_no_client_lookup",
                description="research_agent cannot call client_lookup",
                agent_pattern="research*",
                tool_pattern="client_lookup",
                action_pattern="*",
                decision=PolicyDecision.DENY,
                priority=10
            ),
            PolicyRule(
                id="research_no_trade",
                description="research_agent cannot call trade_activity",
                agent_pattern="research*",
                tool_pattern="trade_activity",
                action_pattern="*",
                decision=PolicyDecision.DENY,
                priority=10
            ),
            PolicyRule(
                id="internal_credit_allow",
                description="internal_agent can call credit_snapshot",
                agent_pattern="internal*",
                tool_pattern="credit_snapshot",
                action_pattern="*",
                decision=PolicyDecision.ALLOW,
                priority=20
            ),
            PolicyRule(
                id="change_credit_limit_approval",
                description="changing credit limit requires approval",
                agent_pattern="*",
                tool_pattern="change_credit_limit",
                action_pattern="*",
                decision=PolicyDecision.REQUIRE_APPROVAL,
                priority=5
            ),
            PolicyRule(
                id="mutate_requires_approval",
                description="any state-mutating action requires approval",
                agent_pattern="*",
                tool_pattern="*",
                action_pattern="mutate",
                decision=PolicyDecision.REQUIRE_APPROVAL,
                priority=15
            ),
            PolicyRule(
                id="default_allow",
                description="default allow",
                agent_pattern="*",
                tool_pattern="*",
                action_pattern="*",
                decision=PolicyDecision.ALLOW,
                priority=1000
            ),
        ]

    def _matches(self, pattern: str, value: str) -> bool:
        if pattern == "*":
            return True
        if pattern.endswith("*"):
            return value.startswith(pattern[:-1])
        if pattern.startswith("*"):
            return value.endswith(pattern[1:])
        return pattern == value

    def evaluate(self, policy_input: PolicyInput) -> PolicyDecision:
        # Sort by priority
        sorted_rules = sorted(self.rules, key=lambda r: r.priority)

        for rule in sorted_rules:
            if (self._matches(rule.agent_pattern, policy_input.agent) and
                self._matches(rule.tool_pattern, policy_input.tool) and
                self._matches(rule.action_pattern, policy_input.action)):

                decision = rule.decision

                # Log decision
                log_entry = {
                    "input": policy_input.model_dump(),
                    "rule_id": rule.id,
                    "rule_description": rule.description,
                    "decision": decision.value,
                    "timestamp": "2026-09-15T00:00:00Z"
                }
                self.decision_log.append(log_entry)

                return decision

        # Default allow if no rule matches
        return PolicyDecision.ALLOW

    def add_rule(self, rule: PolicyRule):
        self.rules.append(rule)

    def get_log(self) -> List[Dict[str, Any]]:
        return self.decision_log

    def check_tool_access(self, agent_id: str, tool_id: str, action: str = "read") -> PolicyDecision:
        inp = PolicyInput(agent=agent_id, tool=tool_id, action=action)
        return self.evaluate(inp)
