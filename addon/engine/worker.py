"""Run original V3c speech code without booting the phone or patching synthesis."""
import sys,struct,json,time,argparse,subprocess,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'vendor'))
from unicorn import UC_HOOK_CODE,Uc,UC_ARCH_ARM,UC_MODE_ARM
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
FIRMWARE=ROOT/'firmware.bin'
def synthesize(text,language='enus',speed=100,word_pauses=True,gain=0):
 if language not in ('enus','esmx','frca','ptbr'):raise ValueError('Unsupported language')
 raw=text.encode('latin-1')
 if not 0<len(raw)<=200 or b'\0' in raw:raise ValueError('Expected 1..200 non-NUL Latin-1 bytes')
 if not 20<=speed<=500:raise ValueError('Speed percentage must be 20..500')
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x8000000);u.mem_write(0,FIRMWARE.read_bytes())
 def call(addr,*args):
  sp=0x7fe0000
  for reg,value in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),args):u.reg_write(reg,value)
  for i,value in enumerate(args[4:]):u.mem_write(sp+4*i,struct.pack('<I',value))
  u.reg_write(UC_ARM_REG_SP,sp);u.reg_write(UC_ARM_REG_LR,0x7fff000)
  u.emu_start(addr,0x7fff000,timeout=20000000,count=60000000)
  if u.reg_read(UC_ARM_REG_PC)!=0x7fff000:raise RuntimeError('Firmware execution limit reached')
  return u.reg_read(UC_ARM_REG_R0)
 u.mem_write(0x6000000,language.encode()+b'\0')
 if call(0x9396c7,0x5000000,0x400000)!=1:raise RuntimeError('Arena initialization failed')
 if call(0x13ad25,0x6000000,0x1c,8000,0x12f8160,0x6000100):raise RuntimeError('Voice initialization failed')
 ctx=struct.unpack('<I',u.mem_read(0x6000100,4))[0]
 if not 0x5000000<=ctx<0x5400000:raise RuntimeError('Unexpected context pointer')
 u.mem_write(0x6000200,raw+b'\0')
 if not -6<=gain<=6:raise ValueError('Invalid gain')
 if not word_pauses:
  def boundary(uc,a,n,d):
   sp=uc.reg_read(UC_ARM_REG_SP)
   def word(off):return struct.unpack('<I',uc.mem_read(sp+off,4))[0]
   previous=word(0x18)
   offsets=word(0x20);index=word(0x34)
   current=struct.unpack('<I',uc.mem_read(offsets+index,4))[0]
   # Keep initial and punctuation boundaries; connect only whitespace gaps.
   if previous<current<=len(raw) and raw[previous:current].strip()==b'':
    uc.reg_write(UC_ARM_REG_R0,0);uc.mem_write(sp+8,bytes(4))
  u.hook_add(UC_HOOK_CODE,boundary,begin=0x95c660,end=0x95c660)
 result=call(0x939225,ctx,0x6000200,speed,gain,0x6100000,0x100000,0x6000300,0x6000304)
 size,frames=struct.unpack('<II',u.mem_read(0x6000300,8))
 if result or not 0<size<=0x100000:raise RuntimeError(f'Synthesis failed {result}, {size}, {frames}')
 payload=bytes(u.mem_read(0x6100000,size));pos=count=0
 while pos<len(payload):pos+={0:1,1:3,3:11,4:23}[payload[pos]];count+=1
 if pos!=size or count!=frames:raise RuntimeError('Invalid EVRC packet structure')
 header=bytearray((ROOT/'qcp-header.bin').read_bytes());v=header.index(b'vrat');d=header.index(b'data')
 struct.pack_into('<II',header,v+8,1,frames);struct.pack_into('<I',header,d+4,size);struct.pack_into('<I',header,4,len(header)+size-8)
 return bytes(header)+payload,dict(text=text,language=language,speed_percent=speed,frames=frames,seconds=frames*.02,payload_bytes=size,sha256_payload=hashlib.sha256(payload).hexdigest())
if __name__=='__main__':
 request=json.loads(sys.stdin.buffer.read(8192))
 rate=max(0,min(100,int(request.get('rate',50))))
 qcp,metadata=synthesize(request['text'],request.get('language','enus'),min(500,round(100*2**((rate-50)/50)*(2 if request.get('rateBoost',False) else 1))),bool(request.get('wordPauses',True)),int(request.get('gain',0)))
 sys.stdout.buffer.write(qcp)
