#!/usr/bin/env python3
"""Create deterministic per-experiment file hash inventories for CDOI V3."""
import hashlib, json, platform, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PY=Path('/home/anh-khoa/external_data/cdoi-extraction-competition-venv/bin/python')
TARGETS={
 'cdoi_governance_state_machine_v1':[
  'active: PYTHONPATH=/home/anh-khoa/vdt-infra-knowledge-graph /home/anh-khoa/external_data/cdoi-extraction-competition-venv/bin/python -u experiments/cdoi_governance_state_machine_v1/run.py --target active --scratch-root /tmp/cdoi_gsm_v1_scored_r3_active',
  'pinned: PYTHONPATH=/home/anh-khoa/vdt-infra-knowledge-graph:/home/anh-khoa/kp-submission-readiness-v1/src /home/anh-khoa/external_data/cdoi-extraction-competition-venv/bin/python -u experiments/cdoi_governance_state_machine_v1/run.py --target pinned --scratch-root /tmp/cdoi_gsm_v1_scored_r3_pinned'],
 'cdoi_support_state_propagation_v1':['PYTHONPATH=/home/anh-khoa/kp-submission-readiness-v1/src /home/anh-khoa/external_data/cdoi-extraction-competition-venv/bin/python -u experiments/cdoi_support_state_propagation_v1/run.py --scratch-root /tmp/cdoi_ssp_v1_scored_r4'],
 'cdoi_adapter_field_impact_v1':['PYTHONPATH=/home/anh-khoa/kp-submission-readiness-v1/src /home/anh-khoa/external_data/cdoi-extraction-competition-venv/bin/python -u experiments/cdoi_adapter_field_impact_v1/run.py --scratch-root /tmp/cdoi_afi_v1_scored_r3']}
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def git(*args): return subprocess.check_output(['git','-C',str(ROOT),*args],text=True).strip()
def main():
 pyver=subprocess.check_output([str(PY),'--version'],text=True).strip()
 for name,commands in TARGETS.items():
  base=ROOT/'experiments'/name
  files=[]
  for p in sorted(base.rglob('*')):
   if p.is_file() and p.name not in {'sha256_manifest.json','run_manifest.json'}:
    files.append({'path':p.relative_to(base).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p)})
  run={'experiment':name,'code_commit':'0d06382142a16a24ca50e87ca088fcfac3301199','branch':'master','working_tree_at_start':'preexisting .gitignore modification and untracked user files; preserved','active_source_commit':git('rev-parse','HEAD'),'pinned_submission_commit':'89f240b7a2f07a2d58f9952cd36a907ca48f218c','python':pyver,'python_executable':str(PY),'platform':platform.platform(),'commands':commands,'classification':'synthetic developer-authored behavior/contract evidence; not independent validation'}
  (base/'run_manifest.json').write_text(json.dumps(run,indent=2,sort_keys=True)+'\n')
  manifest={'algorithm':'SHA-256','experiment':name,'file_count':len(files),'files':files}
  (base/'sha256_manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
 print('WROTE',len(TARGETS),'experiment manifests')
if __name__=='__main__':main()
