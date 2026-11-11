"""Fixed-config, Phase-2.11-only development evaluation for Phase 2.15."""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from cdoi.model_config import load_dotenv_file
from cdoi.qwen_rca import QwenRCAAgentModel,QwenRCAConfig
from cdoi.rcaeval_evaluation import RCAEvalCase,adapt_cached_case_to_store
from cdoi.hypothesis_generation import HypothesisConfiguration,generate_evidence_aware_hypotheses
from cdoi.candidate_evidence_profile import CandidateEvidenceProfileBuilder
from cdoi.rca_investigation import CandidateSourceMode,InvestigationMode,PreparedRCAInvestigation,RCAAgentV0,RCAOrchestrator

OUT=ROOT/'experiments/archive/v3_phase2_15_qwen_development_20260924'; P211=ROOT/'experiments/archive/v3_phase2_11'; CACHE=ROOT/'data/benchmarks/external/rcaeval/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e'; INDEX=ROOT/'data/benchmarks/external/rcaeval/cases.parquet'
def write(p,v): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 if OUT.exists(): raise RuntimeError('REFUSE_TO_OVERWRITE_PHASE215_DEVELOPMENT_ARCHIVE')
 load_dotenv_file(ROOT/'.env',override=False); config=QwenRCAConfig.from_internal_gateway_environment()
 if config.status()!='QWEN_LIVE_READY': raise RuntimeError('QWEN_LIVE_RUNTIME_NOT_READY')
 import pyarrow.parquet as pq
 pilot=tuple(json.loads((P211/'EXPERIMENT_MANIFEST.json').read_text())['pilot_case_ids'])
 rows={str(x['case']):x for x in pq.read_table(INDEX,columns=['case','dataset','system','inject_time','time_start','time_end','has_logs','has_traces']).to_pylist()}
 write(OUT/'CONFIG.json',{'schema_version':'v3_phase2_15_development_config_v1','configuration':config.public_metadata(),'prompt_version':'rca_agent_qwen_v1','candidate_source':'H1_THEN_H5_FALLBACK','max_tool_calls':12,'max_rounds':8,'phase212_holdout':'PROHIBITED_NOT_READ'})
 agent=RCAAgentV0(QwenRCAAgentModel(config),max_tool_calls=12,max_candidate_profiles=6); orch=RCAOrchestrator(); outputs=[]
 # All candidate/run artifacts are generated without reading a GT column.
 for case_id in pilot:
  r=rows[case_id]; case=RCAEvalCase(case_id,str(r['dataset']),str(r['system']),int(r['inject_time']),int(r['time_start']) if r['time_start'] is not None else None,int(r['time_end']) if r['time_end'] is not None else None,bool(r['has_logs']),bool(r['has_traces']))
  adapted,store,_,_=adapt_cached_case_to_store(case,CACHE/case_id,OUT/'stores'/f'{case_id}.sqlite')
  view=store.logical_view(); cfg=HypothesisConfiguration(); h1=generate_evidence_aware_hypotheses(store,view,configuration=cfg,include_metric=True,include_trace=False,include_topology=False,include_temporal_change=False); h5=generate_evidence_aware_hypotheses(store,view,configuration=cfg,include_metric=True,include_trace=True,include_topology=True,include_temporal_change=True)
  union=tuple(sorted({x.candidate_id:x for x in (*h1.candidates,*h5.candidates)}.values(),key=lambda x:x.candidate_id)); profiles=CandidateEvidenceProfileBuilder(store.context,store,(*h1.aggregate_evidence,*h5.aggregate_evidence)).build_all(union)
  prepared=PreparedRCAInvestigation(store.context,store,h1.candidates,h5.candidates,profiles)
  report=orch.run(prepared,OUT/'RUNS'/case_id,InvestigationMode.AGENT,CandidateSourceMode.H1_THEN_H5_FALLBACK,agent,agent.model.public_metadata())
  outputs.append({'case_id':case_id,'status':report.status,'primary_candidate_id':report.primary_hypothesis.candidate_id if report.primary_hypothesis else None,'tool_calls':report.tool_calls,'latency_records':list(agent.model.records)})
  store.close()
 # Development labels are consumed Phase 2.11 data and are read only now.
 truth={p.stem:json.loads(p.read_text())['evaluations']['H5_COMBINED'].get('ground_truth_service_id') for p in (P211/'CASE_EVALUATIONS').glob('*.json')}
 evaluated=[]
 for row in outputs:
  report=json.loads((OUT/'RUNS'/row['case_id']/'RCA_REPORT.json').read_text()); primary=report.get('primary_hypothesis') or {}; candidate=primary.get('candidate_id'); run_candidates=json.loads((OUT/'RUNS'/row['case_id']/'CANDIDATES.json').read_text())['candidates']; byid={x['candidate_id']:x['subject_node_id'].removeprefix('entity:') for x in run_candidates}; predicted=byid.get(candidate); gt=truth[row['case_id']]; evaluated.append({**row,'ground_truth_service_id':gt,'predicted_service_id':predicted,'top1_correct':predicted==gt if predicted else False,'ground_truth_in_final_hypotheses':gt in [byid.get(x.get('candidate_id')) for x in [primary,*report.get('alternative_hypotheses',[])]], 'unknown_evidence_ids':0})
 total=len(evaluated); top1=sum(x['top1_correct'] for x in evaluated); technical=sum(x['status']=='TECHNICAL_FAILURE' for x in evaluated); abstain=sum(x['status']=='INSUFFICIENT_EVIDENCE' for x in evaluated)
 write(OUT/'PILOT_RESULTS.json',{'schema_version':'v3_phase2_15_qwen_pilot_v1','evaluated_count':total,'top1_correct':top1,'top1_accuracy':top1/total if total else None,'technical_failures':technical,'abstentions':abstain,'grounding_unknown_evidence_ids':sum(x['unknown_evidence_ids'] for x in evaluated),'cases':evaluated,'development_only':True})
 write(OUT/'RESEARCH_GATE.json',{'schema_version':'v3_phase2_15_development_gate_v1','decision':'QWEN_LIVE_RCA_DEVELOPMENT_EVALUATED','phase212_holdout':'NOT_READ','independent_validation':'DATA_MISSING','canonical_kg_mutation':'NONE'})
 paths=sorted(p for p in OUT.rglob('*.json') if p.name not in {'HASHES.json','MANIFEST.json'}); write(OUT/'HASHES.json',{'artifacts':{p.relative_to(OUT).as_posix():sha(p) for p in paths}}); paths=sorted(p for p in OUT.rglob('*.json') if p.name!='MANIFEST.json'); write(OUT/'MANIFEST.json',{'artifacts':{p.relative_to(OUT).as_posix():sha(p) for p in paths}})
if __name__=='__main__': main()
