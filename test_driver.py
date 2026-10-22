"""Real packaged processes, mock NVDA playback/notification boundary."""
from pathlib import Path
import sys,time,json,wave
root=Path(__file__).resolve().parent
# Reuse the local recording NVDA adapter, not its old driver tests.
adapter=(root/'test_adapter.py').read_text()
exec(compile(adapter,str(root/'test_adapter.py'),'exec'))
r=root
class LangChangeCommand:
    def __init__(self,lang): self.lang=lang
sys.modules['speech.commands'].LangChangeCommand=LangChangeCommand
(root/'validation-samples').mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('testdriver',root/'addon/synthDrivers/douchTTS/__init__.py')
m=importlib.util.module_from_spec(spec);sys.modules['testdriver']=m;spec.loader.exec_module(m)
assert m.SynthDriver.check()
assert m.legacy_text('caf\u00e9 \u0153 \u2066') == 'caf\u00e9 oe '
assert len(m.VOICES)==4
d=m.SynthDriver()
def wait_done(n):
    limit=time.monotonic()+30
    while len(done.events)<n and time.monotonic()<limit:time.sleep(.01)
    assert len(done.events)==n,(n,len(done.events))
d.speak(['Hello Brandon.',IndexCommand(4),BreakCommand(20),CharacterModeCommand(True),'ABC',CharacterModeCommand(False),' End.'])
wait_done(1)
assert [e['index'] for e in index.events]==[4]
assert Player.instances[0].kw['outputDevice']=='test-device'
assert Player.instances[0].kw['samplesPerSec']==8000
assert sum(len(b) for p in Player.instances for b in p.frames)>1000
d._set_volume(0);d.speak(['Muted speech.']);wait_done(2)
assert Player.instances[-1].volume=={'all':0}
d._set_volume(100)
d.pause(False);d.pause(False);d.pause(True);d.pause(True)
d.speak(['Paused text.']);time.sleep(.2);assert len(done.events)==2
d.cancel();d.speak(['After cancellation.']);wait_done(3)
for pitch in (0,50,100):
    d._set_pitch(pitch)
    audio=b''.join(pcm for pcm,sr in d._synthesize('Hello Brandon.',('enus',pitch),50,d._generation))
    p=root/'validation-samples'/f'driver-pitch-{pitch}.wav'
    with wave.open(str(p),'wb') as w:w.setparams((1,2,8000,0,'NONE','not compressed'));w.writeframes(audio)
    assert len(audio)>1000
d.speak(['Testing longer speech. '*8,'123456789012345678901234567890123456789012345678']);wait_done(4)
d.speak(['Long running speech. '*100])
limit=time.monotonic()+5
while d._proc is None and time.monotonic()<limit:time.sleep(.005)
assert d._proc is not None
proc=d._proc;start=time.monotonic();d.cancel();cancel=time.monotonic()-start
assert cancel<.5
proc.wait(timeout=3)
d.speak(['Ready again.']);wait_done(5)
seen=[]
original_synthesize=d._synthesize
def recording(text,voice,rate,generation):
    seen.append(voice[0])
    yield from original_synthesize(text,voice,rate,generation)
d._synthesize=recording
d.speak(['English.',LangChangeCommand('es_ES'),'EspaÃ±ol.',LangChangeCommand('fr_CA'),'FranÃ§ais.',LangChangeCommand('pt_BR'),'PortuguÃªs.',LangChangeCommand(None),'English again.'])
wait_done(6)
assert seen==['enus','esmx','frca','ptbr','enus'],seen
for voice in m.VOICES:
 d._set_voice(voice)
 assert d._get_language()==m.VOICES[voice][1]
d._set_wordPauses(False);d._set_rateBoost(True);d._set_engineGain(25)
assert not d._get_wordPauses() and d._get_rateBoost() and d._get_engineGain()==25
captured=[]
def capture_settings(text,voice,rate,generation):
    captured.append(voice)
    yield from original_synthesize(text,voice,rate,generation)
d._synthesize=capture_settings
d.speak(['Hello.',LangChangeCommand('fr_CA'),'Bonjour.'])
wait_done(7)
assert len(captured)==2 and all(v[2:]==(False,True,25) for v in captured)
d.terminate()
assert not d._thread.is_alive() and all(p.closed for p in Player.instances)
report={'real_synthesis':True,'selected_device':True,'index_notifications':True,'breaks':True,'spelling':True,'volume_zero':True,'pause_resume':True,'cancel_active_worker_seconds':cancel,'speech_after_cancel':True,'long_text_chunking':True,'termination':True,'live_NVDA_tested':False}
(root/'driver-validation.json').write_text(json.dumps(report,indent=2))
print('PASS',report)
