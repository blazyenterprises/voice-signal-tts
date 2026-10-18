"""Shared NVDA driver, Windows legacy-engine adapters, 2026."""
from collections import OrderedDict
from pathlib import Path
import queue
import subprocess
import threading
import unicodedata
import config
import nvwave
from logHandler import log
from synthDriverHandler import SynthDriver as BaseSynth, VoiceInfo, synthIndexReached, synthDoneSpeaking
from speech.commands import IndexCommand, CharacterModeCommand, BreakCommand, LangChangeCommand

NAME = Path(__file__).parent.name
ROOT = Path(__file__).resolve().parents[2] / 'engine'
VOICES = {'enus': ('English (United States)', 'en_US'), 'esmx': ('Spanish (Mexico)', 'es_MX'), 'frca': ('French (Canada)', 'fr_CA'), 'ptbr': ('Portuguese (Brazil)', 'pt_BR')}

def legacy_text(text):
    # Keep accents and language-specific letters; remove invisible controls.
    text = ''.join(c for c in text if unicodedata.category(c) not in ('Cf', 'Cs') and (unicodedata.category(c) != 'Cc' or c in '\t\r\n'))
    text = text.translate(str.maketrans({'\u2019': "'", '\u2018': "'", '\u201c': '"', '\u201d': '"', '\u2014': ' ', '\u2013': ' ', '\u2026': '...', '\u0153': 'oe', '\u0152': 'OE', '\u20ac': ' euro '}))
    text = unicodedata.normalize('NFC', text)
    result = []
    for c in text:
        if ord(c) <= 255: result.append(c)
        else:
            result.append(''.join(x for x in unicodedata.normalize('NFKD', c) if ord(x) <= 255 and not unicodedata.combining(x)) or ' ')
    return ''.join(result)

class SynthDriver(BaseSynth):
    name = NAME
    description = 'Voice Signal TTS'
    supportedSettings = (BaseSynth.VoiceSetting(), BaseSynth.RateSetting(), BaseSynth.PitchSetting(), BaseSynth.VolumeSetting())
    supportedCommands = {IndexCommand, CharacterModeCommand, BreakCommand, LangChangeCommand}
    supportedNotifications = {synthIndexReached, synthDoneSpeaking}
    @classmethod
    def check(cls):
        return all((ROOT / name).is_file() for name in ('runtime/python.exe','worker.py','firmware.bin','qcp-header.bin','ffmpeg.exe'))
    def __init__(self):
        self._voice = next(iter(VOICES)); self._rate = 50; self._pitch = 50; self._volume = 100
        self._lock = threading.RLock(); self._generation = 0; self._closed = False
        self._failed = False; self._proc = None; self._player = None; self._paused = threading.Event(); self._paused.set()
        self._queue = queue.Queue()
        self._thread = threading.Thread(target=self._worker, name=NAME, daemon=True); self._thread.start()
    def _get_availableVoices(self):
        return OrderedDict((k, VoiceInfo(k, v[0], v[1])) for k, v in VOICES.items())
    def _get_voice(self): return self._voice
    def _set_voice(self, value):
        if value not in VOICES: raise ValueError('Unknown voice')
        self._voice = value
    def _get_language(self): return VOICES[self._voice][1]
    def _get_rate(self): return self._rate
    def _set_rate(self, value): self._rate = max(0, min(100, int(value)))
    def _get_volume(self): return self._volume
    def _set_volume(self, value): self._volume = max(0, min(100, int(value)))
    def _get_pitch(self): return self._pitch
    def _set_pitch(self, value): self._pitch = max(0, min(100, int(value)))
    def speak(self, speechSequence):
        parts = []; buf = []; chars = False
        def flush():
            if buf:
                # Bound engine work so large documents remain interruptible.
                text = ' '.join(buf); buf.clear()
                while text:
                    cut = min(len(text), 48)
                    if cut < len(text):
                        boundary = text.rfind(' ', 0, cut)
                        if boundary > 0: cut = boundary
                    parts.append(('text', text[:cut])); text = text[cut:].lstrip()
        for item in speechSequence:
            if isinstance(item, str): buf.append(' '.join(item) if chars else item)
            elif isinstance(item, IndexCommand): flush(); parts.append(('index', item.index))
            elif isinstance(item, BreakCommand): flush(); parts.append(('break', max(0, min(item.time, 10000))))
            elif isinstance(item, CharacterModeCommand): flush(); chars = item.state
            elif isinstance(item, LangChangeCommand):
                flush(); parts.append(('language', item.lang))
        flush()
        with self._lock:
            if not self._closed: self._queue.put((self._generation, parts, (self._voice,self._pitch), self._rate, self._volume))
    def _current(self, generation): return not self._closed and generation == self._generation
    def _run(self, args, data, generation):
        with self._lock:
            if not self._current(generation): return None
            self._proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(ROOT), creationflags=subprocess.CREATE_NO_WINDOW)
            proc = self._proc
        try:
            out, err = proc.communicate(data, timeout=30)
            if not self._current(generation): return None
            if proc.returncode: raise RuntimeError(err.decode('utf-8', 'replace')[-1500:])
            return out
        except subprocess.TimeoutExpired:
            proc.kill(); proc.communicate(); raise RuntimeError('Speech synthesis timed out')
        finally:
            with self._lock:
                if self._proc is proc: self._proc = None
    def _synthesize(self, text, voice, rate, generation):
        text = legacy_text(text)
        if not text.strip(): return
        import json
        request = json.dumps({'text':text, 'rate':rate, 'language':voice[0]}).encode('utf-8')
        try:
            qcp = self._run([str(ROOT/'runtime/python.exe'), '-I', str(ROOT/'worker.py')], request, generation)
        except RuntimeError as error:
            if 'Synthesis failed' not in str(error) or len(text)<2: raise
            # Expanded numbers can exceed the firmware limit even in a short
            # string. Retry smaller pieces without discarding any characters.
            cut = text.rfind(' ',0,len(text)//2+1)
            if cut<1: cut=len(text)//2
            for part in (text[:cut],text[cut:]):
                if not self._current(generation): return
                yield from self._synthesize(part,voice,rate,generation)
            return
        if qcp is None: return
        args = [str(ROOT/'ffmpeg.exe'), '-v','error','-nostdin','-i','pipe:0']
        if voice[1] != 50:
            factor = 2**((voice[1]-50)/100)
            args += ['-af', 'asetrate=%d,aresample=8000,atempo=%.8f' % (round(8000*factor),1/factor)]
        pcm = self._run(args + ['-f','s16le','-acodec','pcm_s16le','-ar','8000','-ac','1','pipe:1'], qcp, generation)
        if pcm is None: return
        if not pcm or len(pcm)%2: raise RuntimeError('Invalid decoded speech')
        for offset in range(0,len(pcm),1600):
            if not self._current(generation): return
            yield pcm[offset:offset+1600],8000
    def _worker(self):
        while True:
            job = self._queue.get()
            if job is None: return
            generation, parts, voice, rate, volume = job
            if not self._current(generation): continue
            try:
                active_voice = voice
                for kind, value in parts:
                    if not self._current(generation): break
                    while not self._paused.wait(.05):
                        if not self._current(generation): break
                    if not self._current(generation): break
                    if kind=='language':
                        if value is None: selected = voice[0] if voice[0] in VOICES else self._voice
                        else:
                            language = value.replace('-', '_').lower()
                            selected = next((k for k,v in VOICES.items() if v[1].lower()==language), None)
                            if selected is None: selected = next((k for k,v in VOICES.items() if v[1][:2].lower()==language[:2]), voice[0])
                        active_voice = (selected, voice[1])
                        continue
                    if kind=='index':
                        if self._player: self._player.sync()
                        if self._current(generation): synthIndexReached.notify(synth=self,index=value)
                        continue
                    audio = iter([(b'\0\0'*int(8000*value/1000),8000)]) if kind=='break' else self._synthesize(value,active_voice,rate,generation)
                    try:
                        for pcm,sample_rate in audio:
                            while not self._paused.wait(.05):
                                if not self._current(generation): break
                            if not self._current(generation): break
                            with self._lock:
                                if not self._current(generation): break
                                if self._player is None or self._sample_rate != sample_rate:
                                    if self._player: self._player.close()
                                    self._sample_rate = sample_rate
                                    self._player = nvwave.WavePlayer(channels=1,samplesPerSec=sample_rate,bitsPerSample=16,outputDevice=config.conf['audio']['outputDevice'])
                                player = self._player
                                player.setVolume(all=volume/100)
                                if not self._paused.is_set(): player.pause(True)
                            player.feed(pcm)
                            if not self._current(generation): player.stop()
                    finally:
                        if hasattr(audio,'close'): audio.close()
                    if self._current(generation) and self._player: self._player.idle()
                if self._current(generation): synthDoneSpeaking.notify(synth=self)
            except Exception:
                if self._current(generation):
                    log.exception(NAME+' synthesis failed')
                    import wx
                    wx.CallAfter(self._fail, generation)
    def _fail(self, generation):
        if not self._current(generation) or self._failed: return
        self._failed = True
        import synthDriverHandler
        import ui
        if synthDriverHandler.getSynth() is self:
            synthDriverHandler.setSynth('espeak')
            ui.message(self.description + ' could not generate speech. Switched to eSpeak. See the NVDA log for details.')
    def cancel(self):
        with self._lock:
            self._generation += 1
            if self._proc and self._proc.poll() is None: self._proc.kill()
            if self._player: self._player.stop()
            self._paused.set()
            while True:
                try: self._queue.get_nowait()
                except queue.Empty: break
    def pause(self, switch):
        with self._lock:
            if bool(switch) == (not self._paused.is_set()): return
            if switch: self._paused.clear()
            else: self._paused.set()
            if self._player: self._player.pause(switch)
    def terminate(self):
        self.cancel()
        with self._lock: self._closed=True
        self._queue.put(None); self._thread.join(timeout=5)
        if self._player: self._player.close()
        super().terminate()
