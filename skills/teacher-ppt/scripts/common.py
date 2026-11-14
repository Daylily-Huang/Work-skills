"""Small, dependency-free helpers shared by the teacher PPT workflow."""
from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parents[1]
NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships','c':'http://schemas.openxmlformats.org/drawingml/2006/chart','rel':'http://schemas.openxmlformats.org/package/2006/relationships','ct':'http://schemas.openxmlformats.org/package/2006/content-types'}
def tag(prefix,name):return '{'+NS[prefix]+'}'+name
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def write(path,value):
 p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def digest(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def catalog():return read(ROOT/'assets/catalog.json')
def project_path(job,value):
 p=Path(value);return p.resolve() if p.is_absolute() else (Path(job)/p).resolve()
def rel_path(job,target):
 base=Path(job).resolve();p=Path(target).resolve()
 try:return p.relative_to(base).as_posix()
 except ValueError:return str(p)
class Blocked(ValueError):pass
def need(condition,message):
 if not condition:raise Blocked(message)
