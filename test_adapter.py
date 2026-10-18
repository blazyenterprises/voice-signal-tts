"""Integration tests with real rsynth process and a recording NVDA audio adapter."""
import importlib.util,sys,types,time,threading
from pathlib import Path
r=Path(__file__).resolve().parent
import tempfile
(r/'test-temp').mkdir(exist_ok=True)
tempfile.tempdir=str(r/'test-temp')
name=sys.argv[1] if len(sys.argv)>1 else 'rsynthClassic'
class Base:
 @staticmethod
 def VoiceSetting():return None
 RateSetting=VolumeSetting=PitchSetting=VoiceSetting
 def terminate(self):pass
class Notification:
 def __init__(self):self.events=[]
 def notify(self,**kw):self.events.append(kw)
index=Notification();done=Notification()
class Command:pass
class IndexCommand(Command):
 def __init__(self,index):self.index=index
class BreakCommand(Command):
 def __init__(self,time):self.time=time
class CharacterModeCommand(Command):
 def __init__(self,state):self.state=state
class Player:
 instances=[]
 def __init__(self,**kw):self.kw=kw;self.frames=[];self.stopped=0;self.closed=False;self.running=False;self.paused=False;self.instances.append(self)
 def feed(self,pcm):self.running=True;self.frames.append(pcm)
 def idle(self):pass
 def sync(self):pass
 def stop(self):self.stopped+=1;self.running=False;self.paused=False
 def pause(self,x):
  if not x and self.running and not self.paused:raise OSError("AUDCLNT_E_NOT_STOPPED: redundant resume")
  self.paused=x
 def close(self):self.closed=True
 def setVolume(self,**kw):self.volume=kw
sys.modules['config']=types.SimpleNamespace(conf={'audio':{'outputDevice':'test-device'}})
sys.modules['nvwave']=types.SimpleNamespace(WavePlayer=Player)
sys.modules['logHandler']=types.SimpleNamespace(log=types.SimpleNamespace(exception=lambda x: (_ for _ in ()).throw(AssertionError(x))))
sys.modules['synthDriverHandler']=types.SimpleNamespace(SynthDriver=Base,VoiceInfo=lambda *x:x,synthIndexReached=index,synthDoneSpeaking=done)
sys.modules['speech']=types.ModuleType('speech');sys.modules['speech.commands']=types.SimpleNamespace(IndexCommand=IndexCommand,BreakCommand=BreakCommand,CharacterModeCommand=CharacterModeCommand)
