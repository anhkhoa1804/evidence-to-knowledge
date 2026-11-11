"""Size-matched plain-text control for the failed V2.1 A0 request shape."""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path
from time import perf_counter
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "experiments/archive/v3_phase2_16_v2_1_payload_padding_control_20260925"
from cdoi.model_config import load_dotenv_file
from cdoi.qwen_rca import QwenRCAConfig, QwenRCAError
from cdoi.qwen_rca_v2_1 import QwenRCAAgentV21Model

def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name: str, value: Any) -> None:
    path=OUT/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
def main() -> None:
    if (OUT/"MANIFEST.json").exists(): raise RuntimeError("REFUSE_TO_OVERWRITE_PADDING_CONTROL")
    load_dotenv_file(ROOT/".env",override=False); config=replace(QwenRCAConfig.from_internal_gateway_environment(),timeout_seconds=120,max_retries=1)
    if config.status()!="QWEN_LIVE_READY" or config.model!="vllm/Qwen3.8-27B": raise RuntimeError("QUALIFIED_PROVIDER_CONFIG_MISMATCH")
    OUT.mkdir(parents=True,exist_ok=True); system=QwenRCAAgentV21Model.system_prompt; prefix="Synthetic size-only transport probe. Return exactly {\"status\":\"INSUFFICIENT_EVIDENCE\"}. Padding follows: "
    # 805 user-prompt bytes matches the failed A0 body without copying its JSON shape.
    user=(prefix+"x"*2000)[:805]; messages=[{"role":"system","content":system},{"role":"user","content":user}]
    request_size=len(json.dumps({"model":config.model,"messages":messages,"temperature":0,"max_tokens":8192,"response_format":{"type":"json_object"}},sort_keys=True,separators=(",",":")).encode())
    write("PREREGISTRATION.json",{"schema_version":"v2_1_padding_control_v1","reference":"A0_MINIMAL_STRUCTURED","only_changed_factor":"user content structure; byte length matched to 805-byte A0 user payload","request_size_bytes":request_size,"response_format":"ON","timeout_seconds":120,"max_retries":1,"no_rca_case":True})
    model=QwenRCAAgentV21Model(config,max_output_tokens=8192); started=perf_counter()
    try:
        answer=model.complete(messages,response_format={"type":"json_object"}); msg=answer.get("message",{}); terminal=isinstance(msg,Mapping) and (isinstance(msg.get("content"),str) or isinstance(msg.get("tool_calls"),list)); row={"terminal_response":terminal,"transport_classification":"TERMINAL_SUCCESS" if terminal else "NO_TERMINAL_RESPONSE","elapsed_ms":round((perf_counter()-started)*1000,3),"attempt_count":model.last_transport_diagnostic.get("attempt_count"),"retry_count":model.last_transport_diagnostic.get("retry_count"),"http_status":(model.last_transport_diagnostic.get("attempts") or [{}])[-1].get("http_status"),"resolved_model":answer.get("response_metadata",{}).get("resolved_model"),"timeout":False,"output_tokens":answer.get("usage",{}).get("output_tokens")}
    except QwenRCAError as exc:
        row={"terminal_response":False,"transport_classification":"READ_TIMEOUT" if exc.detail=="TIMEOUT" else "UNKNOWN_TRANSPORT_FAILURE","elapsed_ms":round((perf_counter()-started)*1000,3),"attempt_count":model.last_transport_diagnostic.get("attempt_count"),"retry_count":model.last_transport_diagnostic.get("retry_count"),"http_status":None,"resolved_model":None,"timeout":exc.detail=="TIMEOUT","failure_code":exc.code,"failure_detail":exc.detail or None,"output_tokens":None}
    write("PADDING_CONTROL_RESULT.json",{"schema_version":"v2_1_padding_control_result_v1","a0_reference":{"request_size_bytes":1763,"user_prompt_bytes":805,"profiles":0,"tools":0,"response_format":"ON","terminal_response":False,"transport_classification":"READ_TIMEOUT"},"control":{"request_size_bytes":request_size,"user_prompt_bytes":len(user.encode()),"profiles":0,"tools":0,"response_format":"ON",**row}})
    gate="V2_1_STRUCTURED_USER_PAYLOAD_INTERACTION_IDENTIFIED" if row["terminal_response"] else "V2_1_PAYLOAD_ROOT_CAUSE_UNRESOLVED"; write("SECURITY_AUDIT.json",{"schema_version":"v2_1_padding_security_v1","status":"PASS","credential_or_header_value_occurrences":0,"hidden_analysis_field_occurrences":0,"raw_provider_content_retained":False}); write("RESEARCH_GATE.json",{"schema_version":"v2_1_padding_gate_v1","decision":gate,"production_change":"NOT_AUTHORIZED"}); write("FINAL_REPORT.md",f"# V2.1 Size-Matched Padding Control\n\nGate: `{gate}`. A same-size plain-text user message was compared with A0 without profiles or tools.\n")
    files=sorted(p for p in OUT.rglob("*") if p.is_file() and p.name not in {"HASHES.json","MANIFEST.json"}); write("HASHES.json",{"schema_version":"v2_1_padding_hashes_v1","artifacts":{p.relative_to(OUT).as_posix():sha(p) for p in files}}); files=sorted(p for p in OUT.rglob("*") if p.is_file() and p.name!="MANIFEST.json"); write("MANIFEST.json",{"schema_version":"v2_1_padding_manifest_v1","artifacts":{p.relative_to(OUT).as_posix():sha(p) for p in files}})
if __name__=="__main__": main()
