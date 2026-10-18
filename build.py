from pathlib import Path
import zipfile,shutil,json,hashlib,ast
root=Path(__file__).resolve().parent
addon=root/'addon'
shutil.copy2(root/'README.txt',addon/'README.txt')
for f in addon.rglob('*.py'):
 if 'vendor' not in f.parts and 'runtime' not in f.parts:ast.parse(f.read_text(encoding='utf-8'))
out=root/'dist/0.1.0';out.mkdir(parents=True,exist_ok=True)
f=out/'voiceSignalTTS-0.1.0.nvda-addon'
with zipfile.ZipFile(f,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(addon.rglob('*')):
  if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':z.write(p,p.relative_to(addon))
with zipfile.ZipFile(f) as z:
 assert z.testzip() is None
 assert 'manifest.ini' in z.namelist() and 'synthDrivers/douchTTS/__init__.py' in z.namelist()
 assert 'engine/runtime/python.exe' in z.namelist()
(out/'provenance.json').write_text(json.dumps(dict(version='0.1.0',internal_codename='douch tts',public_name='Voice Signal TTS',source='USC_V3c_04.08.00R_PRIii05698_MONSTER_01.shx',firmware_sha256=hashlib.sha256((addon/'engine/firmware.bin').read_bytes()).hexdigest(),addon_sha256=hashlib.sha256(f.read_bytes()).hexdigest()),indent=2))
shutil.copy2(root/'README.txt',out/'README.txt')
print(f, f.stat().st_size)
