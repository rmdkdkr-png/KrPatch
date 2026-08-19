# -*- coding: utf-8 -*-
"""t900dis.py — TLCS-900/H 미니 디스어셈블러 (beetle 인터프리터 표 기반, SS1 작업용 부분집합)"""
RB=['W','A','B','C','D','E','H','L']
RW=['WA','BC','DE','HL','IX','IY','IZ','SP']
RL=['XWA','XBC','XDE','XHL','XIX','XIY','XIZ','XSP']
CC=['F','LT','LE','ULE','OV','MI','Z','C','T','GE','GT','UGT','NOV','PL','NZ','NC']
SRC={0x19:'LD16m',0x04:'PUSH',
     **{0x20+i:'LD %s,mem'%RW[i] for i in range(8)},
     **{0x20+i:'LD r%d,mem'%i for i in ()}, }
def dis(rom, a, end):
    out=[]
    while a<end:
        st=a; b=rom[a]; a+=1; txt=None
        def imm(n):
            nonlocal a
            v=int.from_bytes(rom[a:a+n],'little'); a+=n; return v
        if b in (0x00,):
            txt='NOP'
        elif b==0x0E: txt='RET'
        elif b==0x09: txt='PUSH #%02X'%imm(1)
        elif 0x20<=b<=0x27: txt='LD %s,#%02X'%(RB[b&7],imm(1))
        elif 0x28<=b<=0x2F: txt='PUSH %s'%RW[b&7]
        elif 0x30<=b<=0x37: txt='LD %s,#%04X'%(RW[b&7],imm(2))
        elif 0x38<=b<=0x3F: txt='PUSH %s'%RL[b&7]
        elif 0x40<=b<=0x47: txt='LD %s,#%08X'%(RL[b&7],imm(4))
        elif 0x48<=b<=0x4F: txt='POP %s'%RW[b&7]
        elif 0x58<=b<=0x5F: txt='POP %s'%RL[b&7]
        elif 0x60<=b<=0x6F:
            d=imm(1); d=d-256 if d>127 else d; txt='JR %s,%06X'%(CC[b&15],a+d)
        elif 0x70<=b<=0x7F:
            d=imm(2); d=d-65536 if d>32767 else d; txt='JRL %s,%06X'%(CC[b&15],a+d)
        elif b==0x1A: txt='JP %04X'%imm(2)
        elif b==0x1B: txt='JP %06X'%imm(3)
        elif b==0x1C: txt='CALL %04X'%imm(2)
        elif b==0x1D: txt='CALL %06X'%imm(3)
        elif b==0x1E:
            d=imm(2); d=d-65536 if d>32767 else d; txt='CALR %06X'%(a+d)
        elif b==0x08: 
            ad=imm(1); v=imm(1); txt='LD (0x%02X),#%02X'%(ad,v)
        elif b==0x0A:
            ad=imm(1); v=imm(2); txt='LDW (0x%02X),#%04X'%(ad,v)
        else:
            cls=None; mem=''; size=0
            if 0x80<=b<=0xB7 or 0xB8<=b<=0xBF:
                grp=(b>>4)-8   # 0=srcB,1=srcW,2=srcL,3=dst
                size=[0,1,2,None][grp] if grp<3 else None
                cls=['srcB','srcW','srcL','dst'][grp]
                if b&8: 
                    d=imm(1); d=d-256 if d>127 else d
                    mem='(%s%+d)'%(RL[b&7],d)
                else: mem='(%s)'%RL[b&7]
            elif b&0xF0 in (0xC0,0xD0,0xE0,0xF0):
                lo=b&0xF; grp={0xC0:0,0xD0:1,0xE0:2,0xF0:3}[b&0xF0]
                size=[0,1,2,None][grp]
                cls=['srcB','srcW','srcL','dst'][grp]
                if lo==0: mem='(0x%02X)'%imm(1)
                elif lo==1: mem='(0x%04X)'%imm(2)
                elif lo==2: mem='(0x%06X)'%imm(3)
                elif lo==3:
                    m=imm(1)
                    if m==0x03: mem='(%s+r8:%02X)'%(RL[imm(1)>>2 if False else 0],imm(1))
                    elif m==0x07: mem='(r32+r16)'; imm(2)
                    elif m==0x13: 
                        d=imm(2); mem='(pc%+d)'%d
                    else:
                        if (m&3)==1: d=imm(2); mem='(%s%+d)'%(RL[(m>>2)&7] if m>=0xE0 else 'r%02X'%m, d-65536 if d>32767 else d)
                        else: mem='(r%02X)'%m
                elif lo==4: mem='(-%s)'%RL[(imm(1)>>2)&7]
                elif lo==5:
                    m=imm(1); mem='(%s+)'%RL[(m>>2)&7]
                elif lo==7 and grp<3:
                    cls=['regB','regW','regL'][grp]; mem='r#%02X'%imm(1)
                elif lo>=8 and grp<3:
                    cls=['regB','regW','regL'][grp]
                    mem=[RB,RW,RL][grp][b&7]
                else:
                    txt='?? %02X'%b
            if txt is None and cls:
                op=rom[a]; a+=1
                if cls.startswith('src'):
                    if 0x20<=op<=0x27: txt='LD %s,%s'%([RB,RW,RL][size][op&7],mem)
                    elif 0x28<=op<=0x2F: txt='???28 %s'%mem
                    elif 0x30<=op<=0x37: txt='EX %s,%s'%([RB,RW,RL][size][op&7],mem)
                    elif 0x38<=op<=0x3F:
                        n=[1,2,4][size]; v=imm(n)
                        txt='%s %s,#%X'%(['ADD','ADC','SUB','SBC','AND','XOR','OR','CP'][op&7],mem,v)
                    elif 0x40<=op<=0x4F: txt='MUL%s %s,%s'%('S' if op&8 else '',[RW,RL,RL][size][op&7],mem)
                    elif 0x60<=op<=0x67: txt='INC #%d,%s'%(((op&7) or 8),mem)
                    elif 0x68<=op<=0x6F: txt='DEC #%d,%s'%(((op&7) or 8),mem)
                    elif 0x80<=op<=0x87: txt='ADD %s,%s'%([RB,RW,RL][size][op&7],mem)
                    elif 0x88<=op<=0x8F: txt='ADD %s,%s'%(mem,[RB,RW,RL][size][op&7])
                    elif 0x90<=op<=0x97: txt='ADC %s,%s'%([RB,RW,RL][size][op&7],mem)
                    elif 0xA0<=op<=0xA7: txt='SUB %s,%s'%([RB,RW,RL][size][op&7],mem)
                    elif 0xC0<=op<=0xC7: txt='AND %s,%s'%([RB,RW,RL][size][op&7],mem)
                    elif 0xC8<=op<=0xCF: txt='AND %s,%s'%(mem,[RB,RW,RL][size][op&7])
                    elif 0xE0<=op<=0xE7: txt='OR %s,%s'%([RB,RW,RL][size][op&7],mem)
                    elif 0xE8<=op<=0xEF: txt='OR %s,%s'%(mem,[RB,RW,RL][size][op&7])
                    elif 0xF0<=op<=0xF7: txt='CP %s,%s'%([RB,RW,RL][size][op&7],mem)
                    elif 0xF8<=op<=0xFF: txt='CP %s,%s'%(mem,[RB,RW,RL][size][op&7])
                    elif op==0x19: txt='LD (0x%04X),%s'%(imm(2),mem)
                    elif op==0x04: txt='PUSH %s'%mem
                    elif 0x10<=op<=0x17: txt=['LDI','LDIR','LDD','LDDR','CPI','CPIR','CPD','CPDR'][op&7]
                    elif 0x78<=op<=0x7F: txt='%s %s'%(['RLC','RRC','RL','RR','SLA','SRA','SLL','SRL'][op&7],mem)
                    else: txt='src?%02X %s'%(op,mem)
                elif cls=='dst':
                    if op==0x00: txt='LD %s,#%02X'%(mem,imm(1))
                    elif op==0x02: txt='LDW %s,#%04X'%(mem,imm(2))
                    elif op==0x14: txt='LD %s,(0x%04X)'%(mem,imm(2))
                    elif op==0x16: txt='LDW %s,(0x%04X)'%(mem,imm(2))
                    elif 0x20<=op<=0x27: txt='LDA %s,%s'%(RW[op&7],mem)
                    elif 0x30<=op<=0x37: txt='LDA %s,%s'%(RL[op&7],mem)
                    elif 0x40<=op<=0x47: txt='LD %s,%s'%(mem,RB[op&7])
                    elif 0x50<=op<=0x57: txt='LDW %s,%s'%(mem,RW[op&7])
                    elif 0x60<=op<=0x67: txt='LDL %s,%s'%(mem,RL[op&7])
                    elif 0xB0<=op<=0xB7: txt='RES #%d,%s'%(op&7,mem)
                    elif 0xB8<=op<=0xBF: txt='SET #%d,%s'%(op&7,mem)
                    elif 0xC8<=op<=0xCF: txt='BIT #%d,%s'%(op&7,mem)
                    elif 0xD0<=op<=0xDF: txt='JP %s,%s'%(CC[op&15],mem)
                    elif 0xE0<=op<=0xEF: txt='CALL %s,%s'%(CC[op&15],mem)
                    else: txt='dst?%02X %s'%(op,mem)
                else:  # reg
                    size={'regB':0,'regW':1,'regL':2}[cls]
                    if op==0x03: txt='LD %s,#%X'%(mem,imm([1,2,4][size]))
                    elif op==0x04: txt='PUSH %s'%mem
                    elif op==0x05: txt='POP %s'%mem
                    elif op==0x06: txt='CPL %s'%mem
                    elif op==0x07: txt='NEG %s'%mem
                    elif op==0x0C: txt='LINK %s,#%d'%(mem,imm(2))
                    elif op==0x12: txt='EXTZ %s'%mem
                    elif op==0x13: txt='EXTS %s'%mem
                    elif op==0x1C: 
                        d=imm(1); txt='DJNZ %s,%06X'%(mem,a+(d-256 if d>127 else d))
                    elif 0x30<=op<=0x34: txt='%s #%d,%s'%(['RES','SET','CHG','BIT','TSET'][op-0x30],imm(1),mem)
                    elif 0x40<=op<=0x47: txt='MUL %s,%s'%([RW,RL][min(size,1)][op&7],mem)
                    elif 0x60<=op<=0x67: txt='INC #%d,%s'%(((op&7) or 8),mem)
                    elif 0x68<=op<=0x6F: txt='DEC #%d,%s'%(((op&7) or 8),mem)
                    elif 0x70<=op<=0x7F: txt='SCC %s,%s'%(CC[op&15],mem)
                    elif 0x80<=op<=0x87: txt='ADD %s,%s'%([RB,RW,RL][size][op&7],mem)
                    elif 0x88<=op<=0x8F: txt='LD %s,%s'%([RB,RW,RL][size][op&7],mem)
                    elif 0x98<=op<=0x9F: txt='LD %s,%s'%(mem,[RB,RW,RL][size][op&7])
                    elif 0xA8<=op<=0xAF: txt='LD %s,#%d'%(mem,op&7)
                    elif 0xC8<=op<=0xCF:
                        n=[1,2,4][size]
                        txt='%s %s,#%X'%(['ADD','ADC','SUB','SBC','AND','XOR','OR','CP'][op&7],mem,imm(n))
                    elif 0xD8<=op<=0xDF: txt='CP %s,#%d'%(mem,op&7)
                    elif 0xE8<=op<=0xEF: txt='%s %s,#%d'%(['RLC','RRC','RL','RR','SLA','SRA','SLL','SRL'][op&7],mem,imm(1))
                    else: txt='reg?%02X %s'%(op,mem)
            elif txt is None:
                txt='?? %02X'%b
        out.append((st, rom[st:a], txt))
    return out

if __name__=='__main__':
    import sys
    rom=open('/root/ss2_work/ss1/Samurai Shodown! (JUE) [M][!].ngp','rb').read()
    lo=int(sys.argv[1],16); hi=int(sys.argv[2],16)
    for st,by,txt in dis(rom,lo,hi):
        print('%06X  %-18s %s'%(st,' '.join('%02X'%x for x in by),txt))
