import sys
from pathlib import Path

import yaml

import youtube_intel.runtime_composition as composition
from youtube_intel.cli import main

root=Path(sys.argv[1]).resolve()
project=Path(__file__).resolve().parents[3]
assert root.is_relative_to(project / '.var' / 'd2-01')
(root/'config').mkdir(parents=True,exist_ok=True)
(root/'vault').mkdir(exist_ok=True)
config=yaml.safe_load((project / 'config/settings.example.yaml').read_text())
config['storage']['vault_root']=str(root/'vault')
config['cloud']['enabled']=False
(root/'config/settings.yaml').write_text(yaml.safe_dump(config))
(root/'config/channels.yaml').write_text('channels:\n  - channel_id: UC_x5XG1OV2P6uZZ5FSM9Ttw\n    enabled: false\n    priority: 1\n')
original=composition.build_local_source_run_runtime
class NoCredentials:
 def get(self):return None
 def save(self,value):raise AssertionError('no credentials')
 def delete(self):raise AssertionError('no credentials')
def build(**kwargs):
 kwargs['credential_store']=NoCredentials()
 return original(**kwargs)
composition.build_local_source_run_runtime=build
raise SystemExit(main(['--project-root',str(root),'serve-api','--database',str(root/'state.sqlite3'),'--port','18975']))
