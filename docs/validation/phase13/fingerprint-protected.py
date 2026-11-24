import hashlib,json,os,subprocess
from pathlib import Path
base=Path('/Users/developer/Documents/yia-worktrees')
evidence=Path('/tmp/intelligence-phase13-evidence')
before=json.loads((evidence/'protected-before.json').read_text());after={}
for name,previous in before.items():
 p=base/name
 def git(*args):return subprocess.check_output(['git','--no-optional-locks',*args],cwd=p)
 content=hashlib.sha256()
 names=sorted(set(x.decode() for x in git('ls-files','--cached','--others','--exclude-standard','-z').split(b'\0') if x))
 for relative in names:
  q=p/relative
  data=os.readlink(q).encode() if q.is_symlink() else q.read_bytes() if q.is_file() else b''
  content.update(relative.encode()+b'\0'+(data if q.is_symlink() else hashlib.sha256(data).digest()))
 tree=hashlib.sha256();entries=0
 for directory,dirs,files in os.walk(p,followlinks=False):
  for entry in sorted(dirs+files):
   q=Path(directory)/entry;s=q.lstat();relative=q.relative_to(p).as_posix()
   tree.update(f'{relative}|{s.st_mode}|{s.st_size}|{s.st_mtime_ns}\n'.encode());entries+=1
 current={'head':git('rev-parse','HEAD').decode().strip(),'status':git('status','--porcelain=v1','--untracked-files=all').decode(),'content_sha256':content.hexdigest(),'tree_metadata_sha256':tree.hexdigest(),'entries':entries}
 after[name]=current
 print(name,'MATCH' if current==previous else 'DIFF',flush=True)
(evidence/'protected-after.json').write_text(json.dumps(after,indent=2))
assert after==before,'protected worktree fingerprint changed'
