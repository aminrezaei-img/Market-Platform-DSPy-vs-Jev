"""
DSPy Optimization Dataset - Phase 1.5
Separate dataset, not FinAgent, not R01-R06
40-80 synthetic banker requests, split 60/20/20
"""
from typing import List, Dict, Any
import random
import dspy

class DSPyOptimizationDataset:
    """
    Creates synthetic banker requests covering various types
    """
    def __init__(self, size: int = 60, seed: int = 42):
        self.size = size
        self.seed = seed
        random.seed(seed)
        self.tasks = self._generate_tasks()
        self.train, self.dev, self.holdout = self._split()

    def _generate_tasks(self) -> List[Dict[str, Any]]:
        base_templates = [
            # pre-meeting brief
            {
                "type": "pre_meeting_brief",
                "templates": [
                    "Prepare a pre-meeting brief for {company}, including relationship history, current exposure, recent activity and relevant external developments.",
                    "Prepare a brief for {company} ahead of client meeting. Cover relationship, credit, trading, external news, risks.",
                    "Draft pre-meeting brief for {company}: relationship overview, credit exposure, trading activity, external developments, material risks.",
                ],
                "companies": ["Nordic Industrial A/S", "Baltic Shipping Ltd", "Green Energy Solutions A/S", "Tech Ventures A/S"],
                "expected_specialists": ["internal", "research", "analysis"],
                "expected_tools": ["client_lookup", "relationship_summary", "credit_snapshot", "trade_activity", "document_search"],
                "risk": "medium"
            },
            # credit lookup
            {
                "type": "credit_lookup",
                "templates": [
                    "What is current credit exposure for {company}?",
                    "What is approved credit limit for {company}?",
                    "Show credit utilization for {company}",
                ],
                "companies": ["Nordic Industrial A/S", "Baltic Shipping Ltd", "Green Energy Solutions A/S"],
                "expected_specialists": ["internal"],
                "expected_tools": ["client_lookup", "credit_snapshot"],
                "risk": "medium"
            },
            # external research
            {
                "type": "external_research",
                "templates": [
                    "What were {company} revenues in 2025?",
                    "What is EBITDA trend for {company} 2024-2025?",
                    "What external developments affect {company}?",
                ],
                "companies": ["Nordic Industrial A/S", "Baltic Shipping Ltd", "Green Energy Solutions A/S"],
                "expected_specialists": ["research"],
                "expected_tools": ["document_search"],
                "risk": "low"
            },
            # missing internal information
            {
                "type": "missing_info",
                "templates": [
                    "What is current exposure for {company}?",
                    "Show GL summary for {company} including EBITDA",
                ],
                "companies": ["Green Energy Solutions A/S", "Tech Ventures A/S"],
                "expected_specialists": ["internal"],
                "expected_tools": ["credit_snapshot", "gl_summary"],
                "expected_answerability": "requires_internal_data",
                "risk": "medium"
            },
            # ambiguous request
            {
                "type": "ambiguous",
                "templates": [
                    "Tell me about {company}",
                    "What do we know about {company}?",
                    "Brief me on {company}",
                ],
                "companies": ["Nordic Industrial A/S", "Baltic Shipping Ltd"],
                "expected_specialists": ["internal", "research"],
                "expected_tools": ["client_lookup", "document_search"],
                "risk": "low"
            },
            # conflicting-data requirement
            {
                "type": "conflict_check",
                "templates": [
                    "What is approved credit limit for {company}? Check CRM and credit snapshot.",
                    "Verify credit limit for {company} across sources",
                ],
                "companies": ["Baltic Shipping Ltd"],
                "expected_specialists": ["internal"],
                "expected_tools": ["client_lookup", "credit_snapshot", "relationship_summary"],
                "expected_answerability": "conflict_detected",
                "risk": "critical"
            },
            # simple lookup
            {
                "type": "simple_lookup",
                "templates": [
                    "Who is coverage banker for {company}?",
                    "What is relationship tenure for {company}?",
                    "What products does {company} use?",
                ],
                "companies": ["Nordic Industrial A/S", "Baltic Shipping Ltd", "Green Energy Solutions A/S", "Tech Ventures A/S"],
                "expected_specialists": ["internal"],
                "expected_tools": ["client_lookup", "relationship_summary"],
                "risk": "low"
            },
            # calculation requirement
            {
                "type": "calculation",
                "templates": [
                    "Calculate utilization for {company} credit facility",
                    "What is YoY revenue growth for {company}?",
                    "Calculate EBITDA margin for {company} 2025",
                ],
                "companies": ["Nordic Industrial A/S", "Baltic Shipping Ltd"],
                "expected_specialists": ["internal", "analysis"],
                "expected_tools": ["credit_snapshot", "calculator"],
                "risk": "medium"
            },
            # human-review case
            {
                "type": "human_review",
                "templates": [
                    "Why did {company} EBITDA decline 17%?",
                    "What caused {company} revenue decline 20%?",
                    "What is {company} stock price today?",
                ],
                "companies": ["Nordic Industrial A/S"],
                "expected_specialists": ["research"],
                "expected_tools": ["document_search"],
                "expected_answerability": "incorrect_premise",
                "risk": "high"
            }
        ]

        tasks = []
        task_id = 0
        for _ in range(self.size):
            # Randomly pick template group
            group = random.choice(base_templates)
            template = random.choice(group["templates"])
            company = random.choice(group["companies"])

            query = template.format(company=company)

            # Build expected
            expected = {
                "task_id": f"DSPY_{task_id:03d}",
                "query": query,
                "company": company,
                "task_type": group["type"] if group["type"] in ["pre_meeting_brief", "credit_lookup", "conflict_check"] else "pre_meeting_brief",
                "expected_specialists": group["expected_specialists"],
                "expected_tools": group["expected_tools"],
                "expected_answerability": group.get("expected_answerability", "answerable"),
                "risk_level": group.get("risk", "medium"),
                "needs_human_review": group.get("expected_answerability") in ["conflict_detected", "incorrect_premise", "requires_internal_data"] or group.get("risk") in ["high", "critical"],
                "category": group["type"]
            }

            # Map to more precise task_type
            if group["type"] == "credit_lookup":
                expected["task_type"] = "credit_lookup"
            elif group["type"] == "conflict_check":
                expected["task_type"] = "conflict_check"
            elif group["type"] == "human_review":
                expected["task_type"] = "false_premise"

            tasks.append(expected)
            task_id += 1

        return tasks

    def _split(self):
        # 60% train, 20% dev, 20% holdout
        n = len(self.tasks)
        train_end = int(n * 0.6)
        dev_end = int(n * 0.8)

        train = self.tasks[:train_end]
        dev = self.tasks[train_end:dev_end]
        holdout = self.tasks[dev_end:]

        return train, dev, holdout

    def get_train(self) -> List[Dict[str, Any]]:
        return self.train

    def get_dev(self) -> List[Dict[str, Any]]:
        return self.dev

    def get_holdout(self) -> List[Dict[str, Any]]:
        return self.holdout

    def get_all(self) -> List[Dict[str, Any]]:
        return self.tasks

    def to_dspy_examples(self, split: str = "train") -> List[dspy.Example]:
        """
        Convert to dspy.Example for MIPROv2/GEPA
        """
        if split == "train":
            tasks = self.train
        elif split == "dev":
            tasks = self.dev
        elif split == "holdout":
            tasks = self.holdout
        else:
            tasks = self.tasks

        examples = []
        for task in tasks:
            ex = dspy.Example(
                request=task["query"],
                memory_context="No prior preferences",
                available_sources=["synthetic_crm", "synthetic_credit", "sec_filings", "trading", "gl"],
                available_tools=["client_lookup", "relationship_summary", "credit_snapshot", "trade_activity", "gl_summary", "document_search", "document_fetch", "calculator", "table_extractor"],
                task_type=task["task_type"],
                answerability=task["expected_answerability"],
                required_specialists=task["expected_specialists"],
                required_tools=task["expected_tools"],
                research_questions=[f"What is {task['company']} {task['category']}?", f"Any risks for {task['company']}?"],
                risk_level=task["risk_level"],
                needs_human_review=task["needs_human_review"]
            ).with_inputs("request", "memory_context", "available_sources", "available_tools")

            examples.append(ex)

        return examples

    def save(self, path: str = "data/dspy_optimization.json"):
        import json
        from pathlib import Path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump({
                "train": self.train,
                "dev": self.dev,
                "holdout": self.holdout,
                "all": self.tasks,
                "size": self.size,
                "seed": self.seed
            }, f, indent=2)

    def summary(self):
        from collections import Counter
        categories = Counter([t["category"] for t in self.tasks])
        return {
            "total": len(self.tasks),
            "train": len(self.train),
            "dev": len(self.dev),
            "holdout": len(self.holdout),
            "categories": dict(categories)
        }
