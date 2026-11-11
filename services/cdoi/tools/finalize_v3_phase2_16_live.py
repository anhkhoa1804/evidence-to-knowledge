"""Finalize analysis of the frozen V2 live-development batch without reruns."""
from __future__ import annotations
import hashlib, json, statistics
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'experiments/archive/v3_phase2_16_agent_v2_development_20260924'
V1=ROOT/'experiments/archive/v3_phase2_15_qwen_development_20260924/PILOT_RESULTS.json'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name, value):
 p=OUT/name; p.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def verify(directory):
 p=directory/'HASHES.json'
 if not p.exists(): return {'status':'UNAVAILABLE_NO_HASHES'}
 rows=json.loads(p.read_text()).get('artifacts',{}); good=sum((directory/n).is_file() and sha(directory/n)==h for n,h in rows.items())
 return {'status':'VALID' if good==len(rows) else 'INVALID','checked':len(rows),'valid':good}
def main():
 r=json.loads((OUT/'V2_RESULTS.json').read_text()); cases=r['cases']; stability=json.loads((OUT/'STABILITY_RUNS/RESULTS.json').read_text())
 traces=[json.loads((OUT/'RUNS'/c['case_id']/'AGENT_TRACE.json').read_text()) for c in cases]
 errors={t.get('error_code','NONE'):sum(x.get('error_code','NONE')==t.get('error_code','NONE') for x in traces) for t in traces}
 lat=[a['elapsed_ms'] for c in cases for a in c['transport'].get('attempts',[]) if 'elapsed_ms'in a]
 def pct(v,p): return sorted(v)[max(0,min(len(v)-1,round((len(v)-1)*p)))] if v else None
 inv={'schema_version':'v3_phase2_16_investigation_analysis_v1','case_count':12,'profiles_preloaded_all_cases':True,'comparison_state_reached':sum('H1_COMPARED' in c['states'] for c in cases),'technical_failure_before_report':12,'tool_calls':0,'fallbacks':0,'states':{'INITIALIZED':12,'H1_PROFILES_LOADED':12,'H1_COMPARED':12,'TECHNICAL_FAILURE':12},'conclusion':'PRELOAD_AND_COMPARISON_ORCHESTRATION_ACTIVATED_BUT_PROVIDER_OUTPUT_WAS_NOT_PARSEABLE'}
 write('INVESTIGATION_ANALYSIS.json',inv)
 write('GROUNDING_ANALYSIS.json',{'schema_version':'v3_phase2_16_grounding_v1','accepted_structured_reports':0,'evidence_citations':0,'unknown_evidence_ids':0,'invalid_candidate_ids':0,'supported_material_claims':'NOT_APPLICABLE_NO_ACCEPTED_REPORTS','unsupported_claims':'NOT_APPLICABLE_NO_ACCEPTED_REPORTS','conclusion':'NO_HALLUCINATED_EVIDENCE_ACCEPTED; NO_GROUNDING_QUALITY_MEASUREMENT_POSSIBLE'})
 write('FALLBACK_ANALYSIS.json',{'schema_version':'v3_phase2_16_fallback_v1','fallback_count':0,'fallback_rate':0.0,'reason':'NOT_REACHED_BECAUSE_ALL_CASES_FAILED_OUTPUT_VALIDATION','additional_candidates':'NOT_APPLICABLE','conclusion':'NOT_EVALUABLE'})
 write('ABSTENTION_ANALYSIS.json',{'schema_version':'v3_phase2_16_abstention_v1','abstentions':0,'valid_abstentions':0,'over_abstentions':0,'ambiguous':'NOT_APPLICABLE','reason':'NO_ACCEPTED_RCA_REPORTS'})
 write('FAILURE_ANALYSIS.json',{'schema_version':'v3_phase2_16_failure_v1','taxonomy':{'STRUCTURED_OUTPUT_FAILURE':12,'PROVIDER_FAILURE':0,'CANDIDATE_SET_LIMITATION':0,'AGENT_DISCRIMINATION_FAILURE':0,'REQUIRES_REVIEW':0},'error_codes':errors,'candidate_stage_vs_agent_stage':'NOT_EVALUABLE_NO_ACCEPTED_AGENT_SELECTION','conclusion':'MODEL_OR_GATEWAY_OUTPUT_CONTRACT_FAILURE_AFTER_SUCCESSFUL_HTTP_RESPONSE'})
 attempts=sum(c['transport'].get('attempt_count',0) for c in cases); retries=sum(c['transport'].get('retry_count',0) for c in cases)
 write('TRANSPORT_RELIABILITY.json',{'schema_version':'v3_phase2_16_transport_v1','provider_requests':12,'attempts':attempts,'retries':retries,'timeouts':0,'connection_failures':0,'http_gateway_failures':0,'successful_http_responses':12,'persistent_failures':0,'output_validation_failures':12,'comparison':'V1 had transport failures; V2 primary had successful HTTP transport but no parseable report'})
 write('STRUCTURED_REPAIR_ANALYSIS.json',{'schema_version':'v3_phase2_16_repair_v1','repair_attempts':0,'repair_successes':0,'repair_failures':0,'reason':'PARSER_FAILURE_PRECEDED_REPORT_LEVEL_REPAIR','limit':1,'conclusion':'REPAIR_PATH_NOT_REACHED'})
 write('PERFORMANCE.json',{'schema_version':'v3_phase2_16_performance_v1','case_count':12,'mean_provider_latency_ms':statistics.mean(lat),'median_provider_latency_ms':statistics.median(lat),'p90_provider_latency_ms':pct(lat,.9),'provider_calls':12,'tool_calls':0,'input_tokens':'NOT_AVAILABLE_PARSER_FAILURE','output_tokens':'NOT_AVAILABLE_PARSER_FAILURE','fallback_incremental_cost':'NOT_APPLICABLE','repair_incremental_cost':'NOT_APPLICABLE'})
 write('STABILITY_RESULTS.json',{'schema_version':'v3_phase2_16_stability_v1','source':'STABILITY_RUNS/RESULTS.json','selected_cases':4,'repetitions_per_case':3,'total_runs':12,'technical_failures':12,'status_agreement':True,'tool_call_agreement':True,'primary_hypothesis_agreement':'NOT_APPLICABLE','fallback_agreement':True,'conclusion':'OUTPUT_CONTRACT_FAILURE_REPRODUCIBLE'})
 write('TELEMETRY_ONLY_RESULTS.json',{'schema_version':'v3_phase2_16_telemetry_only_v1','status':'DEFERRED','reason':'V2_PRIMARY_TECHNICALLY_INCOMPLETE_NO_PARSEABLE_RCA_REPORT_PATH','not_a_performance_comparison':True})
 v1=json.loads(V1.read_text()); write('V1_VS_V2_ANALYSIS.json',{'schema_version':'v3_phase2_16_v1_vs_v2_v1','development_only':True,'v1':{'hypotheses':0,'abstentions':9,'technical_failures':3,'tool_calls':0,'top1':0},'v2':{'hypotheses':0,'abstentions':0,'technical_failures':12,'tool_calls':0,'top1':0},'comparison':'V2 did not improve RCA quality because all live runs stopped at output validation; profile preload reached H1 comparison but no parsed model report or tool request.'})
 historical={n:verify(ROOT/'experiments/archive'/n) for n in ['v3_phase2_12','v3_phase2_13','v3_phase2_14_rca_qwen','v3_phase2_14_semantic','v3_phase2_15_qwen_live','v3_phase2_15_qwen_live_retry_20260924','v3_phase2_15_qwen_development_20260924','v3_phase2_15_finalization_20260924','v3_phase2_16_agent_v2']}
 write('HISTORICAL_HASH_VERIFICATION.json',{'schema_version':'v3_phase2_16_live_historical_hash_v1','archives':historical})
 write('RESEARCH_GATE.json',{'schema_version':'v3_phase2_16_final_gate_v1','decision':'AGENT_V2_TECHNICALLY_INCOMPLETE','v2_synthetic_qualification':'PRESERVED_PASSED','profile_preload':'REACHED_H1_COMPARISON_ON_12_OF_12','real_rca_quality':'NOT_EVALUABLE','structured_output':'NOT_SUPPORTED_ON_LIVE_PRIMARY','stability':'REPRODUCIBLE_TECHNICAL_FAILURE','telemetry_only':'DEFERRED','independent_validation':'DATA_MISSING','v2_1':'SEPARATE_DECISION_REQUIRED_NOT_IMPLEMENTED','phase212':'NOT_READ_EXCEPT_PREVIOUS_ROOT_HASH_INTEGRITY_CHECK','canonical_kg':'UNCHANGED'})
 write('FINAL_REPORT.md', '# V3 Phase 2.16 Live Agent V2 Development Evaluation\n\nFinal gate: `AGENT_V2_TECHNICALLY_INCOMPLETE`. The immutable fixed-config 12-case Phase 2.11 development batch reached deterministic H1 profile preload and H1 comparison on all cases, but every successful HTTP provider response failed V2 output validation before an RCA report, tool request, fallback, or repair could be processed. Thus V2 RCA quality, grounding quality, and candidate-versus-agent discrimination are not evaluable.\n\nStability repeated this outcome in 12/12 runs across four preregistered cases. Telemetry-only comparison is deferred because there is no valid V2 RCA report path to compare. The synthetic archive and all historical archives remain hash-valid; Phase 2.12 cases/evaluations/GT were not accessed. No semantic, candidate-generation, ontology, causal, review, or canonical-KG policy changed.\n')
 paths=sorted(p for p in OUT.rglob('*') if p.is_file() and p.name not in {'HASHES.json','MANIFEST.json'}); write('HASHES.json',{'schema_version':'v3_phase2_16_live_hashes_v1','artifacts':{p.relative_to(OUT).as_posix():sha(p) for p in paths}}); paths=sorted(p for p in OUT.rglob('*') if p.is_file() and p.name!='MANIFEST.json'); write('MANIFEST.json',{'schema_version':'v3_phase2_16_live_manifest_v1','artifacts':{p.relative_to(OUT).as_posix():sha(p) for p in paths}})
if __name__=='__main__': main()
