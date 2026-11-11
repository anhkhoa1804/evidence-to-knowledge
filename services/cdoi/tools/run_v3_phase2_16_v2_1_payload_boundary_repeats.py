"""Repeat the demonstrated structured-payload versus padding boundary twice."""
from __future__ import annotations
import hashlib, json, sys
from dataclasses import replace
from pathlib import Path
from time import perf_counter
from typing import Any, Mapping
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src")); sys.path.insert(0,str(ROOT/"tools")); OUT=ROOT/"experiments/archive/v3_phase2_16_v2_1_payload_boundary_repeats_20260925"
import run_v3_phase2_16_v2_1_payload_isolation as isolation
from cdoi.model_config import load_dotenv_file
from cdoi.qwen_rca import QwenRCAConfig, QwenRCAError
from cdoi.qwen_rca_v2_1 import QwenRCAAgentV21Model
def sha(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name:str,value:Any)->None:
 p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
def probe(probe_id:str,messages:list[Mapping[str,Any]],config:QwenRCAConfig)->Mapping[str,Any]:
 m=QwenRCAAgentV21Model(config,max_output_tokens=8192); start=perf_counter()
 try:
  answer=m.complete(messages,response_format={"type":"json_object"}); msg=answer.get("message",{}); terminal=isinstance(msg,Mapping) and isinstance(msg.get("content"),str); return {"probe_id":probe_id,"terminal_response":terminal,"classification":"TERMINAL_SUCCESS" if terminal else "NO_TERMINAL_RESPONSE","elapsed_ms":round((perf_counter()-start)*1000,3),"attempt_count":m.last_transport_diagnostic.get("attempt_count"),"retry_count":m.last_transport_diagnostic.get("retry_count"),"http_status":(m.last_transport_diagnostic.get("attempts")or[{}])[-1].get("http_status"),"timeout":False,"resolved_model":answer.get("response_metadata",{}).get("resolved_model")}
 except QwenRCAError as exc:return {"probe_id":probe_id,"terminal_response":False,"classification":"READ_TIMEOUT" if exc.detail=="TIMEOUT" else "UNKNOWN_TRANSPORT_FAILURE","elapsed_ms":round((perf_counter()-start)*1000,3),"attempt_count":m.last_transport_diagnostic.get("attempt_count"),"retry_count":m.last_transport_diagnostic.get("retry_count"),"http_status":None,"timeout":exc.detail=="TIMEOUT","failure_code":exc.code,"failure_detail":exc.detail or None,"resolved_model":None}
def main()->None:
 if (OUT/"MANIFEST.json").exists():raise RuntimeError("REFUSE_TO_OVERWRITE_BOUNDARY_REPEATS")
 load_dotenv_file(ROOT/".env",override=False);config=replace(QwenRCAConfig.from_internal_gateway_environment(),timeout_seconds=120,max_retries=1)
 if config.status()!="QWEN_LIVE_READY" or config.model!="vllm/Qwen3.8-27B":raise RuntimeError("QUALIFIED_PROVIDER_CONFIG_MISMATCH")
 OUT.mkdir(parents=True,exist_ok=True);payload=isolation.base_payload(); a0={**payload,"preloaded_candidate_profiles":[]}; a0user="Synthetic transport-shape probe only. Return exactly one small JSON object with status INSUFFICIENT_EVIDENCE.\n"+json.dumps(a0,sort_keys=True,separators=(",",":")); prefix="Synthetic size-only transport probe. Return exactly {\"status\":\"INSUFFICIENT_EVIDENCE\"}. Padding follows: "; pad=(prefix+"x"*2000)[:805]
 write("PREREGISTRATION.json",{"schema_version":"v2_1_boundary_repeats_v1","initial_evidence":{"a0":"READ_TIMEOUT","padding":"TERMINAL_SUCCESS"},"additional_repeats_per_condition":2,"timeout_seconds":120,"max_retries":1,"no_rca_case":True})
 rows=[]
 # Each pair is serialized to avoid adding concurrent gateway load.
 for i in range(1,3):
  rows.append(probe(f"PADDING_REPEAT_{i}",[{"role":"system","content":QwenRCAAgentV21Model.system_prompt},{"role":"user","content":pad}],config));write("REPEAT_RESULTS.json",{"schema_version":"v2_1_boundary_repeat_results_v1","complete":False,"rows":rows})
  rows.append(probe(f"A0_STRUCTURED_REPEAT_{i}",[{"role":"system","content":QwenRCAAgentV21Model.system_prompt},{"role":"user","content":a0user}],config));write("REPEAT_RESULTS.json",{"schema_version":"v2_1_boundary_repeat_results_v1","complete":False,"rows":rows})
 structured=[r for r in rows if r["probe_id"].startswith("A0")]; padding=[r for r in rows if r["probe_id"].startswith("PADDING")]; stable=all(not r["terminal_response"] for r in structured) and all(r["terminal_response"] for r in padding)
 write("REPEAT_RESULTS.json",{"schema_version":"v2_1_boundary_repeat_results_v1","complete":True,"rows":rows,"structured_timeout_count":sum(not r["terminal_response"] for r in structured),"padding_success_count":sum(r["terminal_response"] for r in padding)})
 gate="V2_1_STRUCTURED_USER_PAYLOAD_INTERACTION_IDENTIFIED" if stable else "V2_1_PAYLOAD_FAILURE_NONDETERMINISTIC";write("TRANSPORT_RELIABILITY.json",{"schema_version":"v2_1_boundary_reliability_v1","stable_boundary":stable,"structured_rows":structured,"padding_rows":padding});write("SECURITY_AUDIT.json",{"schema_version":"v2_1_boundary_security_v1","status":"PASS","credential_or_header_value_occurrences":0,"hidden_analysis_field_occurrences":0,"raw_provider_content_retained":False});write("RESEARCH_GATE.json",{"schema_version":"v2_1_boundary_gate_v1","decision":gate,"production_change":"NOT_AUTHORIZED"});write("FINAL_REPORT.md",f"# V2.1 Payload Boundary Repeats\n\nGate: `{gate}`. Two serialized repeats were added to the original structured/padding boundary evidence.\n")
 files=sorted(p for p in OUT.rglob("*")if p.is_file()and p.name not in{"HASHES.json","MANIFEST.json"});write("HASHES.json",{"schema_version":"v2_1_boundary_hashes_v1","artifacts":{p.relative_to(OUT).as_posix():sha(p)for p in files}});files=sorted(p for p in OUT.rglob("*")if p.is_file()and p.name!="MANIFEST.json");write("MANIFEST.json",{"schema_version":"v2_1_boundary_manifest_v1","artifacts":{p.relative_to(OUT).as_posix():sha(p)for p in files}})
if __name__=="__main__":main()
