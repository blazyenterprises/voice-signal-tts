from pathlib import Path
import subprocess,json,struct,array,math,wave
r=Path(__file__).resolve().parent;e=r/'addon/engine';out=r/'validation-samples/0.2.0';out.mkdir(parents=True,exist_ok=True)
results=[]
def run(text,lang='enus',**settings):
 p=subprocess.run([str(e/'runtime/python.exe'),'-I',str(e/'worker.py')],input=json.dumps(dict(text=text,language=lang,**settings)).encode(),capture_output=True,timeout=30)
 assert p.returncode==0,p.stderr.decode();q=p.stdout;v=q.index(b'vrat');frames=struct.unpack_from('<I',q,v+12)[0]
 return q,frames
for lang,text in [('enus','Hello hello hello.'),('esmx','Hola hola hola.'),('frca','Bonjour bonjour bonjour.'),('ptbr','Ola ola ola.')]:
 original,n=run(text,lang);connected,m=run(text,lang,wordPauses=False);assert m<n,(lang,n,m)
 for label,q in [('original',original),('connected',connected)]:
  p=out/f'{lang}-{label}.wav';subprocess.run([str(e/'ffmpeg.exe'),'-v','error','-y','-i','pipe:0',str(p)],input=q,check=True)
 results.append(dict(language=lang,original_seconds=n*.02,connected_seconds=m*.02))
for text in ['Hello. Hello.','Hello, hello.','Hello! Hello?','Hello\nhello.']:
 # Newline is deliberately an ordinary whitespace boundary; punctuation is retained.
 if '\n' not in text:assert run(text)[0]==run(text,wordPauses=False)[0],text
normal,n=run('Hello hello hello.');boost,b=run('Hello hello hello.',rateBoost=True);assert b<n
quiet,c=run('Hello hello hello.',gain=-6);assert c==n
rms=[]
for q in [normal,quiet]:
 p=subprocess.run([str(e/'ffmpeg.exe'),'-v','error','-i','pipe:0','-f','s16le','pipe:1'],input=q,capture_output=True,check=True);a=array.array('h',p.stdout);rms.append(math.sqrt(sum(x*x for x in a)/len(a)))
assert rms[1]<rms[0]*.5
(r/'controls-validation.json').write_text(json.dumps(dict(languages=results,punctuation_preserved=True,gain_rms=rms,rate_boost_frames=[n,b],live_NVDA_tested=False),indent=2));print('PASS',results,rms)
