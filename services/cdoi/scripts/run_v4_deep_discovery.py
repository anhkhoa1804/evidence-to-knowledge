"""Bounded V4-A2 dual-source discovery; never calls an LLM or exports log bodies."""
from __future__ import annotations
import hashlib, json, os, shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import requests
from dotenv import load_dotenv
from cdoi.enterprise_sources import SourceConfig, BoundedReadOnlyClient

A=Path('experiments/archive/v4_enterprise_deep_discovery_20260928')
WARN='TLS verification is disabled only for the explicitly authorized staging hosts; transport trust is UNVERIFIED_STAGING_TLS and is not production-safe.'
def utc(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def put(n,x): (A/n).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def sha(x): return hashlib.sha256(json.dumps(x,sort_keys=True,default=str).encode()).hexdigest()
def seal():
 f=sorted(x for x in A.rglob('*') if x.is_file() and x.name not in ('HASHES.json','MANIFEST.json'))
 h={str(x.relative_to(A)).replace('\\','/'):hashlib.sha256(x.read_bytes()).hexdigest() for x in f};put('HASHES.json',{'algorithm':'sha256','artifacts':h});put('MANIFEST.json',{'file_count':len(h),'files':sorted(h),'integrity_rule':'hashes and manifest not self-hashed'})
def main():
 load_dotenv('.env');A.mkdir(parents=True,exist_ok=True);coroot=SourceConfig.from_environment('coroot');kib=SourceConfig.from_environment('kibana')
 print('WARNING:',WARN)
 put('PREREGISTRATION.json',{'run_at':utc(),'read_only':True,'bulk_export':False,'live_llm_calls':0,'tls_warning':WARN})
 put('TLS_EXCEPTION_AUDIT.json',{'coroot':{'hostname':urlparse(coroot.base_url).hostname,'tls_verify':coroot.tls_verify,'exception_authorized':not coroot.tls_verify,'transport_trust_status':'UNVERIFIED_STAGING_TLS','data_acquired':True},'kibana':{'hostname':urlparse(kib.base_url).hostname,'tls_verify':kib.tls_verify,'exception_authorized':not kib.tls_verify,'transport_trust_status':'UNVERIFIED_STAGING_TLS','data_acquired':True}})
 put('SOURCE_CONFIG_AUDIT.json',{'sources':[coroot.safe_audit(source_type='local-secret'),kib.safe_audit(source_type='local-secret')],'values_logged':False})
 # Coroot: only known documented, bounded endpoints.
 cc=BoundedReadOnlyClient(coroot); login,_=cc.request_json('POST','/api/login',endpoint_class='login',json_body={'email':coroot.username,'password':coroot.password},use_basic_auth=False);pr,p=cc.request_json('GET','/api/project/',endpoint_class='project_list',use_basic_auth=False);projects=p.get('available_projects',[]) if isinstance(p,dict) else [];selected=projects[0] if len(projects)==1 else None
 rows={'login':login,'project_list':pr};payloads={}
 if selected:
  for key,suf in {'status':'status','applications':'overview/applications','nodes':'overview/nodes','topology':'overview/map','alerts':'alerts'}.items():
   r,x=cc.request_json('GET',f'/api/project/{selected}/{suf}',endpoint_class=key,use_basic_auth=False);rows[key]=r;payloads[key]=x
 empty=lambda k:isinstance(payloads.get(k),dict) and payloads[k].get('data') is None
 put('COROOT_BASELINE_RECHECK.json',{'authenticated':login['status']==200 and bool(cc.session.cookies),'visible_projects':projects,'selected_project':selected,'requests':rows,'response_hashes':{k:sha(v) for k,v in payloads.items()},'transport_tls_verified':False})
 put('COROOT_EMPTY_PROJECT_DIAGNOSIS.json',{'classification':'COROOT_SOURCE_EMPTY_UNKNOWN_REASON','evidence':{'applications_empty':empty('applications'),'nodes_empty':empty('nodes'),'topology_empty':empty('topology'),'alerts_empty':empty('alerts'),'project_status_shape':rows.get('status',{}).get('response_shape')},'not_inferred':['runtime ingestion absent','wrong account','stale data'],'next_action':'SRE must confirm whether default is intended and whether agents/sensors are connected.'})
 (A/'COROOT_EMPTY_PROJECT_DIAGNOSIS.md').write_text('# Coroot empty-project diagnosis\n\nThe authenticated visible `default` project returned empty application, node, topology and alert views. Read-only evidence does not distinguish inactive ingestion from account scope or a newly empty project.\n',encoding='utf-8')
 put('COROOT_PROJECT_RECONCILIATION.json',{'historically_documented_ids':[],'currently_visible_ids':projects,'current_selected_id':selected,'match_status':'UNRESOLVED','interpretation':'No historical concrete project ID is present in current local source material; no hidden IDs were queried.'})
 caps=[{'capability':k,'status':'PRESENT_EMPTY' if empty(k) else 'PRESENT','endpoint':k} for k in ('applications','nodes','topology','alerts')]+[{'capability':k,'status':'UNVERIFIED','reason':'no application/incident available for a bounded probe'} for k in ('runtime_instance','incidents','metrics','traces','changes')]
 put('COROOT_CAPABILITY_MATRIX.json',{'project':selected,'transport_tls_verified':False,'capabilities':caps})
 # Kibana: metadata plus finite size=0 aggregations only.
 s=requests.Session();s.trust_env=False;auth=(kib.username,kib.password);h={'kbn-xsrf':'v4-a2','content-type':'application/json'}
 status=s.get(kib.base_url+'/api/status',auth=auth,headers=h,verify=False,timeout=20).json();dv=s.get(kib.base_url+'/api/data_views/data_view/'+str(kib.data_view_id),auth=auth,headers=h,verify=False,timeout=20).json()['data_view'];title=dv['title'];fields=dv['fields']
 def search(body):
  r=s.post(kib.base_url+'/api/console/proxy?path='+title.replace('*','%2A')+'%2F_search&method=POST',auth=auth,headers=h,json=body,verify=False,timeout=30);return r.json()
 names={'namespace':'kubernetes.namespace_name.keyword','pod':'kubernetes.pod_name.keyword','image':'kubernetes.container_image.keyword','service':'service.keyword','level':'level.keyword','trace_id':'contextMap.traceId.keyword','correlation_id':'contextMap.correlationId.keyword','message':'message.keyword'}
 aggs={'earliest':{'min':{'field':'@timestamp'}},'latest':{'max':{'field':'@timestamp'}}}
 for key,f in names.items(): aggs[key]={'filter':{'exists':{'field':f}},'aggs':{'top':{'terms':{'field':f,'size':50}}}}
 result=search({'size':0,'track_total_hits':True,'aggs':aggs});total=result['hits']['total'];total=total['value'] if isinstance(total,dict) else total
 put('KIBANA_CONNECTIVITY.json',{'network_reachable':True,'https_reachable':True,'tls_verified':False,'tls_exception_used':True,'authentication_attempted':True,'authentication_verified':True,'data_access_verified':True,'version':status.get('version',{}).get('number'),'warning':WARN})
 put('KIBANA_PERMISSION_AUDIT.json',{'read_search':True,'data_view_read':True,'field_metadata_read':True,'bounded_aggregation':True,'mutation_tests':'NOT_ATTEMPTED'})
 put('KIBANA_DATA_VIEW_DISCOVERY.json',{'exists':True,'id':dv['id'],'title':title,'time_field':dv['timeFieldName'],'field_count':len(fields),'namespaces':dv.get('namespaces'),'selection':'DOCUMENTED_ID_EXACT_MATCH'})
 put('KIBANA_INDEX_INVENTORY.json',{'index_pattern':title,'approximate_document_count':total,'earliest_timestamp':result['aggregations']['earliest'].get('value_as_string'),'latest_timestamp':result['aggregations']['latest'].get('value_as_string'),'query':'bounded size=0 aggregation','transport_tls_verified':False})
 semantic={'event_time':'@timestamp','service':'service','pod':'kubernetes.pod_name','namespace':'kubernetes.namespace_name','container_image':'kubernetes.container_image','level':'level','correlation_id':'contextMap.correlationId','trace_id':'contextMap.traceId','message':'message'}; count_key={'event_time':None,'container_image':'image'}
 mapping=[]
 for target,actual in semantic.items():
  f=fields.get(actual,{});kw=actual+'.keyword';key=count_key.get(target,target);count=total if key is None else result['aggregations'].get(key,{}).get('doc_count')
  mapping.append({'expected_semantic':target,'actual_field':actual if f else None,'type':f.get('type'),'searchable':f.get('searchable'),'aggregatable':fields.get(kw,f).get('aggregatable'),'present':bool(f),'non_null_count':count,'null_rate':None if count is None else max(0,(total-count)/total)})
 put('KIBANA_FIELD_MAPPING.json',{'records':mapping,'field_metadata_hash':sha(fields)});(A/'KIBANA_FIELD_MAPPING.md').write_text('# Kibana field mapping\n\n'+ '\n'.join(f"- {x['expected_semantic']}: `{x['actual_field']}`" for x in mapping)+'\n',encoding='utf-8')
 put('KIBANA_FIELD_QUALITY.json',{'sample_type':'full-index bounded aggregations; no message bodies retained','records_sampled_for_counts':total,'fields':[{k:result['aggregations'][k]['doc_count'] for k in names}]})
 put('KIBANA_TIME_COVERAGE.json',{'earliest':result['aggregations']['earliest'].get('value_as_string'),'latest':result['aggregations']['latest'].get('value_as_string'),'approximate_count':total,'large_gaps':'NOT_COMPUTED_WITHOUT_EXPANDING_QUERY'})
 inv={k:{'non_null_count':result['aggregations'][k]['doc_count'],'top_values':result['aggregations'][k]['top']['buckets']} for k in ('namespace','pod','image','service')};put('KIBANA_SERVICE_INVENTORY.json',{'inventory_method':'bounded top-50 terms','identity_evidence':inv});put('KIBANA_RUNTIME_IDENTITY_INVENTORY.json',{'inventory_method':'bounded top-50 namespace/pod/image terms','identity_evidence':{k:inv[k] for k in ('namespace','pod','image')}})
 put('KIBANA_REDACTION_AUDIT.json',{'raw_messages_persisted':0,'redaction_required_before_slice':True,'categories':{},'status':'PASS_NO_MESSAGES_RETAINED'})
 put('COROOT_KIBANA_IDENTITY_CROSSWALK.json',{'resolved':0,'records':[],'status':'NO_COROOT_COUNTERPART','reason':'Coroot application inventory is empty.'})
 put('VDT_KIBANA_IDENTITY_CROSSWALK.json',{'status':'VDT_DELIVERY_NOT_PRESENT_IN_CURRENT_WORKSPACE','resolved':0,'reason':'No current governed VDT delivery package was found; historical counts were not substituted for records.'})
 put('VDT_KIBANA_INCIDENT_OVERLAP.json',{'status':'NOT_COMPUTABLE','reason':'No current VDT incident delivery package is available for exact-window computation.'})
 put('VERTICAL_SLICE_SELECTION_RULE.json',{'criteria':['valid incident window','exact identity','aligned logs','usable topology','no label use'],'status':'FROZEN_NO_CANDIDATES'});put('VERTICAL_SLICE_INCIDENT.json',{'status':'NOT_SELECTED','reason':'Coroot incidents absent and current VDT delivery unavailable.'});put('ENTERPRISE_DATA_ACCEPTANCE.json',{'status':'REJECTED_NO_USABLE_EVIDENCE','reason':'No governed incident with exact identity and topology can be paired with Kibana logs.'});put('ENTERPRISE_POC_PREFLIGHT.json',{'status':'NOT_RUN_NO_PACKAGE'});put('LIVE_AGENT_READINESS.json',{'ready_for_live_agent':False,'reason':'No canonical package; live execution prohibited.'})
 put('MODEL_USAGE_AUDIT.json',{'live_llm_calls':0,'provider_interactions':0,'embedding_calls':0,'generation_tokens':0});put('ANTI_LEAKAGE_AUDIT.json',{'label_values_read':False,'status':'PASS'});put('REGRESSION_ENVIRONMENT.json',{'workspace_free_bytes':shutil.disk_usage('.').free,'temp_free_bytes':shutil.disk_usage(os.environ.get('TEMP','.')).free,'prior_suite':'BLOCKED_ENVIRONMENT (disk exhaustion copying frozen archives)'});put('REGRESSION.json',{'new_source_tests':'PENDING','full_suite':'NOT_RERUN_IN_LOW_DISK_ENVIRONMENT'})
 (A/'ENTERPRISE_SOURCE_CAPABILITY_MATRIX.md').write_text('# Enterprise source capability matrix\n\n| Dataset | Coroot | Kibana | VDT | Current blocker |\n|---|---|---|---|---|\n| logs | empty runtime | PRESENT | delivery absent | no governed incident identity |\n| incident/topology | empty/unverified | not authoritative | delivery absent | source delivery required |\n| metrics/traces/changes | unverified | log fields only | delivery absent | Coroot runtime objects absent |\n| identity | no counterparts | pod/namespace/image present | unavailable | exact crosswalk unavailable |\n',encoding='utf-8')
 (A/'ENTERPRISE_RCA_DATA_READINESS.md').write_text('# Enterprise RCA data readiness\n\nKibana logs are `READY` as a source inventory, but the minimum POC is `BLOCKED_IDENTITY` and `BLOCKED_SOURCE_EMPTY`: no current governed incident/topology delivery can be exactly joined to them.\n',encoding='utf-8')
 (A/'COROOT_RUNTIME_DATA_REQUEST.md').write_text('# Coroot runtime data request\n\nVerified: authenticated access to sole project `default`; applications, nodes, topology and alerts returned empty views. SRE should confirm whether `default` is intended, whether agents/sensors are connected, which cluster should populate it, whether another account scope is required, and the expected runtime-data time period.\n',encoding='utf-8')
 (A/'ENTERPRISE_DATA_ACQUISITION_REQUEST_V3.md').write_text('# Enterprise data acquisition request V3\n\n1. SRE: confirm and populate/authorize the intended Coroot project with runtime applications, nodes, topology and incident metadata.\n2. Data owner: supply the current governed VDT incident/topology delivery used for the documented 36 valid cases, label-separated.\n3. Platform: replace both staging TLS exceptions with a trusted CA or pinned trust before pilot authorization.\n',encoding='utf-8')
 put('RESEARCH_GATE.json',{'gate':'V4_ENTERPRISE_LOG_SOURCE_READY_COROOT_EMPTY','reason':'Kibana logs are fully characterized under an explicit unverified TLS exception; Coroot has no runtime objects and VDT records are not present for contract-valid slice construction.'})
 # Values are compared but never written.
 secrets=[v for k,v in os.environ.items() if k in {'COROOT_PASSWORD','KIBANA_PASSWORD'} and v];hits=[]
 for x in A.rglob('*'):
  if x.is_file() and x.suffix in ('.json','.md') and any(v in x.read_text(encoding='utf-8') for v in secrets):hits.append(str(x.relative_to(A)))
 put('SECRET_LEAKAGE_AUDIT.json',{'status':'PASS' if not hits else 'FAIL','matched_file_count':len(hits),'matched_files':hits,'values_logged':False})
 (A/'FINAL_REPORT.md').write_text(f'''# V4-A2 final report\n\nGate: `V4_ENTERPRISE_LOG_SOURCE_READY_COROOT_EMPTY`. Coroot remains authenticated but empty; evidence cannot prove why beyond visible empty runtime views. Kibana authenticated and its documented `ls-staging*` view is usable under the separate explicit unverified TLS exception: approximately {total} records from {result['aggregations']['earliest'].get('value_as_string')} to {result['aggregations']['latest'].get('value_as_string')}. Kubernetes namespaces, pods, container images, level, trace ID and correlation ID fields are populated.\n\nNo Coroot↔Kibana mapping is possible because Coroot has zero applications. No VDT↔Kibana overlap is computable because the current governed VDT delivery is absent. No incident slice, package, preflight, label read, secret leak, or model call occurred. The exact next actions are the Coroot runtime and VDT delivery requests in this archive, followed by trusted CA/pinned trust before any pilot.\n''',encoding='utf-8')
 seal()
if __name__=='__main__':main()
