# Agent Registry Runtime Reconstruction

**Verdict:** VERIFIED

## REG-01: Instantiate from registry only
{'agent': 'markets.pre_meeting_brief@1.2.0', 'reconstructed': True, 'workflow_created': True, 'output_path': 'runs/verification/registry_v1_2_0_output.json', 'trace_path': 'traces/verification/registry_v1_2_0.jsonl', 'passed': True}

## REG-02: Changed policy changes runtime behaviour
{'agent': 'markets.pre_meeting_brief@1.2.1-verification', 'base_policy': {'allow': ['client_lookup', 'relationship_summary', 'credit_snapshot', 'trade_activity', 'document_search', 'calculator', 'table_extractor']}, 'new_policy': {'allow': ['client_lookup', 'relationship_summary', 'credit_snapshot', 'trade_activity', 'document_search', 'table_extractor']}, 'calculator_removed': True, 'output_path': 'runs/verification/registry_v1_2_1_output.json', 'trace_path': 'traces/verification/registry_v1_2_1.jsonl', 'passed': True}

## REG-03: Deleting entry causes fail not fallback
{'agent': 'non.existent.agent@9.9.9', 'expected': 'fail', 'actual': 'failed as expected: Agent non.existent.agent@9.9.9 not found in registry - cannot reconstruct, no fallback', 'passed': True}

