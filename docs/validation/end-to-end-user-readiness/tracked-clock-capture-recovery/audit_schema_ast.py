import ast
import json
import subprocess
from pathlib import Path

base = 'bc306d16289f7cf8938851f05c9b35b9cc4f9781'
review = json.loads(Path('.var/tracked-clock-capture-recovery/schema40-reviewed-edits.json').read_text())
changes = []

def migration(value, version):
    if isinstance(value, ast.Constant):
        return value.value == f'{version:03d}_add_' + ('local_text_input_proofs.sql' if version == 39 else 'tracked_content_retry.sql')
    return isinstance(value, ast.Tuple) and len(value.elts) == 2 and isinstance(value.elts[0], ast.Constant) and value.elts[0].value == version and migration(value.elts[1], version)

for path in sorted({item['file'] for item in review}):
    before = subprocess.check_output(['git', 'show', f'{base}:{path}'], text=True)
    after = Path(path).read_text()
    lines = {item['line'] for item in review if item['file'] == path}
    def compare(left, right, location='module'):
        if isinstance(left, ast.FunctionDef) and left.name == 'test_migration39_failure_preserves38_all_rows_and_data':
            old = ast.get_source_segment(before, left)
            expected = old.replace('broken = replace(migrations[-1], sql=migrations[-1].sql + "\\nSELECT injected_unknown_function();")\n    monkeypatch.setattr(repository, "_load_migrations", lambda: (*migrations[:-1], broken))', 'migration39 = next(migration for migration in migrations if migration.version == 39)\n    broken = replace(migration39, sql=migration39.sql + "\\nSELECT injected_unknown_function();")\n    monkeypatch.setattr(repository, "_load_migrations", lambda: (*tuple(m for m in migrations if m.version < 39), broken))').replace('assert repository.initialize(now=NOW).version == 39', 'assert repository.initialize(now=NOW).version == 40')
            assert ast.dump(ast.parse(expected).body[0]) == ast.dump(right), (path, location)
            changes.append(dict(file=path, function=left.name, reason='Explicit historical039 failure selection and normal full initialize40; all original38 rollback/data assertions unchanged.'))
            return
        if isinstance(left, ast.Constant) and isinstance(right, ast.Constant) and left.value != right.value:
            a, b = left.value, right.value
            allowed = (a == 39 and b == 40 and left.lineno in lines)
            allowed |= a == 24 and b == 25 and left.lineno in {116,1706,214,50} and path.endswith(('test_task021_source_policy_filtering.py','test_task022_personalized_distillation.py','test_task023_topic_timeline.py','test_task025a_saved_intelligence.py'))
            allowed |= a == '039_add_local_text_input_proofs.sql' and b == '040_add_tracked_content_retry.sql' and left.lineno in {143,146}
            if 'phase_h2c_lineage_schema' in path:
                allowed |= isinstance(a, str) and ((a.replace("40, '040_future.sql'", "41, '041_future.sql'") == b) or (a == 'PRAGMA user_version = 40' and b == 'PRAGMA user_version = 41') or (a == 'PRAGMA user_version = 39' and b == 'PRAGMA user_version = 40') or (a == 'DELETE FROM schema_migrations WHERE version = 40' and b == 'DELETE FROM schema_migrations WHERE version = 41'))
            assert allowed, (path, location, left.lineno, a, b)
            changes.append(dict(file=path,line=left.lineno,before=a,after=b,ast=location))
            return
        assert type(left) is type(right), (path,location,type(left),type(right))
        if isinstance(left, ast.AST):
            for name in left._fields:
                compare(getattr(left,name),getattr(right,name),location+'.'+name)
        elif isinstance(left,list):
            if len(right) == len(left)+1 and left and migration(left[-1],39) and migration(right[-1],40):
                changes.append(dict(file=path,ast=location,reason='Append actual040 history entry, preserve all preceding migrations including039.'))
                right = right[:-1]
            assert len(left) == len(right), (path,location,len(left),len(right))
            for i,(a,b) in enumerate(zip(left,right)):
                compare(a,b,location+f'[{i}]')
        else:
            assert left == right, (path,location,left,right)
    compare(ast.parse(before),ast.parse(after))
Path('.var/tracked-clock-capture-recovery/schema40-ast-audit.json').write_text(json.dumps(changes,indent=2)+'\n')
print(f'PASS: {len(changes)} reviewed AST changes; no unrelated AST changes across {len({r["file"] for r in review})} files')
