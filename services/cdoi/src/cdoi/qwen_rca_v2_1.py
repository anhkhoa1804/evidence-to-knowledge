"""V2.1 Qwen adapter: V2 provider contract with separately versioned metadata."""
from __future__ import annotations

from typing import Any, Mapping

from .qwen_rca_v2 import QwenRCAAgentV2Model, rca_v2_system_prompt

QWEN_RCA_V2_1_ADAPTER_VERSION = "qwen_rca_openai_compatible_v2_1"


class QwenRCAAgentV21Model(QwenRCAAgentV2Model):
    """No provider-normalization change; V2.1 status validation lives in agent."""

    prompt_version = "rca_agent_qwen_v2_1"
    system_prompt = rca_v2_system_prompt()

    def public_metadata(self) -> Mapping[str, Any]:
        return {**super().public_metadata(), "adapter_version": QWEN_RCA_V2_1_ADAPTER_VERSION,
                "prompt_version": self.prompt_version,
                "status_contract_version": "rca_report_status_contract_v2_1"}
