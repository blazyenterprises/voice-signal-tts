from pathlib import Path
import subprocess,json,struct,time,wave,array
root=Path(__file__).resolve().parent
engine=root/'addon/engine'
out=root/'validation-samples';out.mkdir(exist_ok=True)
results=[]
def run(text,rate,pitch,name,language='enus'):
    start=time.monotonic()
    q=subprocess.run([str(engine/'runtime/python.exe'),'-I',str(engine/'worker.py')],input=json.dumps(dict(text=text,rate=rate,pitch=pitch,language=language)).encode(),capture_output=True,timeout=30)
    assert q.returncode==0,q.stderr.decode(errors='replace')
    assert q.stdout[:4]==b'RIFF'
    args=[str(engine/'ffmpeg.exe'),'-v','error','-i','pipe:0']
    if pitch!=50:
        factor=2**((pitch-50)/100)
        args+=['-af',f'asetrate={round(8000*factor)},aresample=8000,atempo={1/factor:.8f}']
    p=subprocess.run(args+['-f','s16le','-ac','1','-ar','8000','pipe:1'],input=q.stdout,capture_output=True,timeout=15)
    assert p.returncode==0,p.stderr
    a=array.array('h',p.stdout)
    assert len(a)>160 and max(map(abs,a))>100
    with wave.open(str(out/(name+'.wav')),'wb') as w:w.setparams((1,2,8000,0,'NONE','not compressed'));w.writeframes(p.stdout)
    r=dict(name=name,rate=rate,pitch=pitch,seconds=len(a)/8000,wall_seconds=time.monotonic()-start,peak=max(map(abs,a)))
    results.append(r);print(r,flush=True)
    return r,p.stdout
text='Hello Brandon. This is the Motorola phone voice.'
slow,_=run(text,0,50,'rate-0')
normal,n=run(text,50,50,'default')
fast,_=run(text,100,50,'rate-100')
assert slow['seconds']>normal['seconds']>fast['seconds']
low,l=run(text,50,0,'pitch-0');high,h=run(text,50,100,'pitch-100')
assert l!=n and h!=n and l!=h
assert abs(low['seconds']-normal['seconds'])<.2 and abs(high['seconds']-normal['seconds'])<.2
run('1234567890',50,50,'numbers')
run('Testing longer speech. '*2,100,100,'fast-high')
for language,text in [('esmx','Hola. El teléfono está aquí. Uno dos tres.'),('frca','Bonjour. Écoutez cette voix française.'),('ptbr','Olá. Esta é uma função de português.')]:
    run(text,50,50,language,language)
(root/'engine-validation.json').write_text(json.dumps(results,indent=2))
print('PASS native rate, independent audio pitch, EVRC decoding, packaged runtime')
