#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ss1_build2.py — SS1 한글 대사 빌드 (폰트표 확장 + 글리프 + 대사 재배치)

조판: 한글 1음절 = 세로 2셀 → 한 페이지 = 한 줄(최대 17음절)
      페이지 = [상단코드열] F8 [하단코드열],  페이지 사이 FA F9,  끝 FF
슬롯: 0~122 → 코드 0x1A~0x94 / 123~217 → 0x99~0xF7 (예약 0x95~0x98 보존)
재배치: 원본 문자열은 길이 제약이 있으므로 자유 영역(0x36900~)으로 옮기고
        롬 전체에서 3바이트 포인터를 찾아 갱신한다.
"""
import sys, struct
sys.path.insert(0, '/root/ss2_work'); sys.path.insert(0, '/root/ss2_work/ss1')
import ss1_fontpatch2 as F
import ss1_tool as T
import ss1_ko

ROM_IN  = '/root/ss2_work/ss1/Samurai Shodown! (JUE) [M][!].ngp'
REL_BASE = 0x36900          # 재배치 목적지(0xFF 자유 영역)
REL_LIMIT = 0x4FF00
SPACE = 0x92
NL, PAGE, CLR, END = 0xF8, 0xFA, 0xF9, 0xFF
RESERVED = set(range(0x95, 0x99))
MAX_COLS = 17

# 주소 보정: 스캐너가 영문 첫 줄을 건너뛴 두 문장
ADDR_FIX = {0x34357: 0x3434F, 0x34379: 0x3436A}


class SlotPool:
    def __init__(self): self.map = {}; self.order = []
    def get(self, bm):
        if bm in self.map: return self.map[bm]
        s = len(self.order)
        if s >= 217: raise RuntimeError('슬롯 217칸 초과')
        self.map[bm] = s; self.order.append(bm); return s
    def code(self, bm): return F.code_of(self.get(bm))


GPLAN = None

def glyph_plan():
    global GPLAN
    if GPLAN is None:
        chars = sorted({c for t in ss1_ko.KO for c in t if c not in '/ '})
        GPLAN = T.plan_glyphs(chars)
    return GPLAN


INTERLEAVE = True    # gfx13 렌더러 패치와 페어: [윗코드][받침코드]… (F8 없음)

def encode(text, pool, tail):
    out = bytearray()
    pages = [p.strip() for p in text.split('/') if p.strip()]
    for i, page in enumerate(pages):
        if len(page) > MAX_COLS: raise ValueError('한 줄 %d자 초과: %s' % (MAX_COLS, page))
        tops, bots = [], []
        for ch in page:
            if ch == ' ': tops.append(SPACE); bots.append(SPACE); continue
            t, b = glyph_plan()[ch]
            tops.append(pool.code(t)); bots.append(pool.code(b))
        if INTERLEAVE:
            for t, b in zip(tops, bots): out += bytes([t, b])
        else:
            out += bytes(tops) + bytes([NL]) + bytes(bots)
        if i < len(pages) - 1: out += bytes([PAGE, CLR])
    if tail: out += bytes([PAGE, CLR])
    out.append(END)
    return bytes(out), pages


def validate(body):
    assert body[-1] == END, '종결 FF 없음'
    core = body[:-1]
    if core.endswith(bytes([PAGE, CLR])): core = core[:-2]
    for p in core.split(bytes([PAGE, CLR])):
        if INTERLEAVE:
            assert NL not in p, '인터리브 모드에 F8 존재'
            assert len(p) % 2 == 0, '페어 홀수 (%d)' % len(p)
        else:
            assert p.count(bytes([NL])) == 1, '페이지당 F8이 1개가 아님'
            a, b = p.split(bytes([NL]))
            assert len(a) == len(b), '상·하단 길이 불일치 (%d/%d)' % (len(a), len(b))
        assert not set(p) - {NL} & set() and not set(p) & RESERVED, '예약 코드 사용'
    return core.count(bytes([PAGE, CLR])) + 1


def find_ptrs(rom, addr):
    pat = struct.pack('<I', 0x200000 + addr)[:3]
    out = []; st = 0
    while True:
        k = rom.find(pat, st)
        if k < 0: break
        out.append(k); st = k + 1
    return out


def load_rows():
    rows = []
    for line in open('/root/ss2_work/ss1/SS1_번역표.tsv', encoding='utf-8'):
        if line.startswith('#'): continue
        p = line.rstrip('\n').split('\t')
        if len(p) >= 3: rows.append((int(p[0], 16), int(p[1]), p[2]))
    return rows


REGIONS = ((0x33000, 0x36460), (0x010380, 0x010600))    # 스토리 대사 / 초필살기·승리 대사
OUTER_TBL, OUTER_N = 0x34160, 14          # 승리대사 2개짜리 소표를 가리키는 상위표
LIST_TBL, LIST_N = 0x354BD, 14            # 5바이트 레코드 목록(FF 종결)을 가리키는 상위표
CODE_PTRS = [(0x012AEF, 0x012AFB), (0x012C1F, 0x012C2B), (0x012FE6, 0x012FF2)]


def _tgt(raw, k):
    return int.from_bytes(raw[k:k+3], 'little') - 0x200000


def _in_region(t):
    return any(lo <= t < hi for lo, hi in REGIONS)


def _is_en(raw, t):
    if not _in_region(t): return False
    b = raw[t:raw.index(b'\xff', t)]
    return sum(1 for x in b if x < 0x1A) > sum(1 for x in b if 0x1A <= x < 0x88)


def _tables(raw):
    """4바이트 항목(하위3B=대사구역 주소, 4번째=0x00)이 2개 이상 이어지는 구간"""
    def ok(i):
        return raw[i+3] == 0x00 and _in_region(_tgt(raw, i))
    out = []; i = 0; N = len(raw) - 4
    while i < N:
        if ok(i):
            j = i; n = 0
            while j < N and ok(j): j += 4; n += 1
            if n >= 2: out.append((i, n))
            i = j
        else: i += 1
    return out


def mirror_english(rom, raw, newaddr, log=None):
    """본체 언어가 영어일 때도 한글이 나오도록 영문 포인터를 한글 문자열로 돌린다.
    표 구조: [일본어 L개][영어 L개] 가 반복. 승리대사는 상위표→2항목 소표 구조."""
    done = set(); skipped = 0; filled = 0

    def put(slot, jp_addr, tail=(0x00,), allow_null=False):
        """slot(영문 포인터 칸)을 jp_addr의 한글 문자열로 돌린다.
        allow_null=True 면 원본이 널(00 00 00 00)인 칸도 채운다 —
        영문판에 번역이 아예 없는 보스 대사(아마쿠사·잔쿠로·시키)용."""
        nonlocal skipped, filled
        if jp_addr not in newaddr: return False
        if allow_null and raw[slot:slot+4] == b'\x00\x00\x00\x00':
            struct.pack_into('<I', rom, slot, 0x200000 + newaddr[jp_addr])
            done.add(jp_addr); filled += 1; return True
        if raw[slot+3] not in tail: skipped += 1; return False
        t = _tgt(raw, slot)
        # 대사 구역 안이면서 우리가 번역한 일본어 문장이 아닌 것 = 영문(또는 「……」) 칸
        if not _in_region(t) or t in newaddr: skipped += 1; return False
        struct.pack_into('<I', rom, slot, (0x200000 + newaddr[jp_addr]) | (raw[slot+3] << 24))
        done.add(jp_addr); return True

    for a, n in _tables(raw):
        if a == OUTER_TBL: continue
        tags = ['M' if _tgt(raw, a+k*4) in newaddr else '.' for k in range(n)]
        k = 0
        while k < n:
            if tags[k] != 'M': k += 1; continue
            s = k
            while k < n and tags[k] == 'M': k += 1
            L = k - s
            for i in range(L):
                slot = a + (s + L + i) * 4      # 표 길이를 넘어서도 주소로 직접 접근
                put(slot, _tgt(raw, a + (s + i) * 4), allow_null=True)

    # 승리대사: 상위표 앞 14개=일본어 소표, 뒤 14개=영어 소표
    for k in range(OUTER_N):
        jp_mini = _tgt(raw, OUTER_TBL + k * 4)
        en_mini = _tgt(raw, OUTER_TBL + (OUTER_N + k) * 4)
        for j in (0, 1):
            put(en_mini + j * 4, _tgt(raw, jp_mini + j * 4))

    # 5바이트 레코드 목록(승패 대사 묶음): 앞 14목록 = 일본어, 뒤 14목록 = 영어
    def records(addr):
        out = []
        while raw[addr] != 0xFF:
            out.append(addr + 1); addr += 5
        return out

    for k in range(LIST_N):
        jl = records(_tgt(raw, LIST_TBL + k * 4))
        el = records(_tgt(raw, LIST_TBL + (LIST_N + k) * 4))
        for js, es in zip(jl, el):
            put(es, _tgt(raw, js))

    # 코드에 박힌 포인터 쌍
    for jp_slot, en_slot in CODE_PTRS:
        put(en_slot, _tgt(raw, jp_slot), tail=(0x00, 0x34))

    if log is not None:
        log.append((len(done), skipped, filled))
    return done


def build(out_path, report=True):
    raw = open(ROM_IN, 'rb').read()
    rom = bytearray(raw)
    F.patch(rom)
    rows = load_rows()
    assert len(rows) == len(ss1_ko.KO), '문장 수 불일치'

    pool = SlotPool()
    plans = []
    for (addr, ln, jp), ko in zip(rows, ss1_ko.KO):
        addr = ADDR_FIX.get(addr, addr)
        end = raw.index(b'\xff', addr)
        orig = raw[addr:end]
        tail = orig.endswith(bytes([PAGE, CLR]))
        body, pages = encode(ko, pool, tail)
        validate(body)
        plans.append(dict(addr=addr, orig=len(orig) + 1, body=body, pages=len(pages), ko=ko))

    # 글리프 기록
    for slot, bm in enumerate(pool.order):
        F.write_glyph(rom, slot, bm)

    # 재배치 + 포인터 갱신
    cur = REL_BASE
    skipped = []
    for p in plans:
        new = cur
        rom[new:new + len(p['body'])] = p['body']
        cur += len(p['body'])
        hits = find_ptrs(raw, p['addr'])
        n = 0
        for k in hits:
            nxt = raw[k + 3]
            if nxt in (0x00, 0x34):
                struct.pack_into('<I', rom, k, (0x200000 + new) | (raw[k + 3] << 24))
                n += 1
            else:
                skipped.append((p['addr'], k, nxt))
        p['new'] = new; p['nptr'] = n
        assert n > 0, '포인터 없음: %06X' % p['addr']
    assert cur < REL_LIMIT, '재배치 영역 초과'

    # 영어 본체 설정에서도 한글이 나오도록 영문 포인터 미러링
    newaddr = {p['addr']: p['new'] for p in plans}
    log = []
    mirrored = mirror_english(rom, raw, newaddr, log)

    open(out_path, 'wb').write(rom)
    if report:
        tot_old = sum(p['orig'] for p in plans)
        tot_new = sum(len(p['body']) for p in plans)
        print('문장 %d / 슬롯 %d·217' % (len(plans), len(pool.order)))
        print('원본 %d B → 한글 %d B (%.2f배)' % (tot_old, tot_new, tot_new / tot_old))
        print('재배치 %06X~%06X (자유영역 여유 %d B)' % (REL_BASE, cur, REL_LIMIT - cur))
        print('포인터 갱신 %d개 / 보류 %d개' % (sum(p['nptr'] for p in plans), len(skipped)))
        print('영문 미러링 %d/%d 문장 (원본 영문판 빈칸 %d개 새로 채움 / 대상 아님 %d칸)'
              % (len(mirrored), len(plans), log[0][2], log[0][1]))
        miss = [p['addr'] for p in plans if p['addr'] not in mirrored]
        if miss: print('  미러 안 된 문장 %d개: %s' % (len(miss), ' '.join('%06X' % a for a in miss[:12])))
        for a, k, nx in skipped: print('  보류 %06X ← %06X (다음바이트 %02X)' % (a, k, nx))
        print('→', out_path)
    return plans, pool


if __name__ == '__main__':
    build(sys.argv[1] if len(sys.argv) > 1 else '/root/ss2_work/ss1/SS1_Korean_v0.1.ngp')
