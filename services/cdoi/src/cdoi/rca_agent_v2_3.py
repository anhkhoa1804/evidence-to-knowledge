"""Separately versioned exact read-only tool-argument protocol."""
from __future__ import annotations

from .rca_agent_v2_2 import RCAAgentV22

RCA_AGENT_V2_3_PROMPT_VERSION = "rca_agent_staged_tool_contract_v2_3"
RCA_AGENT_V2_3_TRACE_VERSION = "rca_agent_trace_v2_3"


class RCAAgentV23(RCAAgentV22):
    trace_schema_version = RCA_AGENT_V2_3_TRACE_VERSION

    def __init__(self, model, *, budget=None):
        super().__init__(model, budget=budget)
        self.trace_schema_version = RCA_AGENT_V2_3_TRACE_VERSION
