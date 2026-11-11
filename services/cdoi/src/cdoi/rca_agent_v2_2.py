"""Separately versioned staged-provider RCA agent.

The V2.1 semantic/report validator and H1/H5 policy are deliberately reused.
Only the provider interaction is staged by a V2.2 model adapter; no canonical
or causal authority is added.
"""
from __future__ import annotations

from .rca_agent_v2_1 import RCAAgentV21

RCA_AGENT_V2_2_PROMPT_VERSION = "rca_agent_staged_v2_2"
RCA_AGENT_V2_2_TRACE_VERSION = "rca_agent_trace_v2_2"


class RCAAgentV22(RCAAgentV21):
    trace_schema_version = RCA_AGENT_V2_2_TRACE_VERSION

    def __init__(self, model, *, budget=None):
        if budget is None:
            super().__init__(model)
        else:
            super().__init__(model, budget=budget)
        self.trace_schema_version = RCA_AGENT_V2_2_TRACE_VERSION
