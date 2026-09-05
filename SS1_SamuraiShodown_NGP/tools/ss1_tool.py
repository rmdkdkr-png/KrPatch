#!/usr/bin/env python3
"""ss1_tool.py — 사무라이 쇼다운!(NGP) 한글화 작업 도구

기능:
  dump   <rom> [out.tsv]        스크립트 덤프 (주소 / 바이트 / 원문)
  verify <rom>                  왕복검증: 롬 → 텍스트 → 롬 재인코딩이 바이트 동일한지
  slots  <trans.tsv>            번역문의 글리프 슬롯 사용량 집계 (상한 222)
  font   <trans.tsv> [out.png]  필요 글리프 시트 렌더 (검수용)

포맷 (P0 해독):
  1바이트 = 1글자, 코드 = 글리프번호 + 26, 0xFF 종결
  제어: F8 개행 / F9 끝 / FA 대기 / FB·FC·FE 소수 사용
한글 조판 (P1 확정):
  음절 = 세로 2셀(8×16). 상단 = (초성,중성) '받침형' 렌더, 하단 = 실제 받침(없으면 공백)
  폰트 = Galmuri11-Condensed (7×11, dwidth 8)
"""
import sys, os, json
sys.path.insert(0, '/root/ss2_work'); sys.path.insert(0, '/root/ss2_work/v067b')

SCRIPT_LO, SCRIPT_HI = 0x33000, 0x36000
CODE_BASE = 26
SLOT_MIN, SLOT_MAX = 0x1A, 0xF7        # 글리프에 쓸 수 있는 코드 범위
SLOT_LIMIT = SLOT_MAX - SLOT_MIN + 1   # 222
CTRL = {0xF8: '{개행}', 0xF9: '{끝}', 0xFA: '{대기}', 0xFB: '{FB}', 0xFC: '{FC}', 0xFE: '{FE}'}
CTRL_REV = {v: k for k, v in CTRL.items()}

HIRA = 'あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわん'
KATA = 'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワン'
SPECIAL = {110: '゛', 111: '。', 113: '、', 120: ' '}
SPECIAL_REV = {v: k for k, v in SPECIAL.items()}


def jp_char(code):
    g = code - CODE_BASE
    if 0 <= g < len(HIRA): return HIRA[g]
    if 55 <= g < 55 + len(KATA): return KATA[g - 55]
    return SPECIAL.get(g)


def jp_code(ch):
    i = HIRA.find(ch)
    if i >= 0: return i + CODE_BASE
    i = KATA.find(ch)
    if i >= 0: return i + 55 + CODE_BASE
    if ch in SPECIAL_REV: return SPECIAL_REV[ch] + CODE_BASE
    return None


def decode(buf):
    """바이트열 → 표시 문자열 (미확인 코드는 <XX>)"""
    out = []
    for b in buf:
        c = jp_char(b)
        if c is not None: out.append(c)
        elif b in CTRL: out.append(CTRL[b])
        else: out.append('<%02X>' % b)
    return ''.join(out)


def encode(text):
    """표시 문자열 → 바이트열 (decode의 역함수)"""
    out = bytearray(); i = 0
    while i < len(text):
        if text[i] == '{':
            j = text.index('}', i) + 1
            out.append(CTRL_REV[text[i:j]]); i = j; continue
        if text[i] == '<':
            out.append(int(text[i + 1:i + 3], 16)); i += 4; continue
        c = jp_code(text[i])
        if c is None: raise ValueError('인코딩 불가 문자: %r' % text[i])
        out.append(c); i += 1
    return bytes(out)


def scan(rom):
    """스크립트 구역에서 0xFF 종결 문자열 수집 → [(주소, 바이트열)]"""
    def ok(b): return jp_char(b) is not None or b in CTRL
    out = []; i = SCRIPT_LO
    while i < SCRIPT_HI:
        if not ok(rom[i]): i += 1; continue
        s = i; n = 0
        while i < len(rom) and rom[i] != 0xFF and n < 200 and (ok(rom[i]) or CODE_BASE <= rom[i] <= 0xFB):
            i += 1; n += 1
        if rom[i:i + 1] == b'\xff' and n >= 4:
            out.append((s, bytes(rom[s:i]))); i += 1
        else:
            i = s + 1
    return out


# ---------- 한글 조판 ----------
_font_cache = {}

def _glyphs():
    if 'g' not in _font_cache:
        import bdf_render as B
        _font_cache['B'] = B
        _font_cache['g'] = B.parse_bdf('/root/ss2_work/galmuri_repo/dist/Galmuri11-Condensed.bdf')
    return _font_cache['B'], _font_cache['g']


def _cell(ch, off=1):
    B, (props, glyphs) = _glyphs()
    gl = glyphs.get(ord(ch))
    if gl is None: return [[0] * 8 for _ in range(16)]
    pts, (w, h, xo, yo) = B.glyph_pixels(gl)
    a = [[0] * 8 for _ in range(16)]
    base = 11 - h - yo            # BDF 베이스라인 기준 세로 정렬(한글 h=11,yo=0 → 0)
    for rx, ry in pts:
        X, Y = rx + xo, ry + off + base
        if 0 <= Y < 16 and 0 <= X < 8: a[Y][X] = 1
    return a


BLANK8 = tuple(tuple([0] * 8) for _ in range(8))


def ko_glyphs(ch):
    """한글 음절 → (상단 8×8, 하단 8×8). 비한글은 (글리프, 공백)

    상단 8행의 마지막 줄(7행)이 비면 받침이 한 칸 떠서 '두 번째 줄'처럼 보인다.
    그런 (초성,중성) 조합은 상단을 1px 내려 그려 받침과 붙인다.
    판단이 ref(초성·중성)만으로 이뤄지므로 같은 조합끼리는 계속 슬롯을 공유한다."""
    if not ('가' <= ch <= '힣'):
        g = _cell(ch)
        return tuple(map(tuple, g[:8])), tuple(map(tuple, g[8:]))
    c = ord(ch) - 0xAC00
    cho, jung, jong = c // 588, (c % 588) // 28, c % 28
    ref = chr(0xAC00 + (cho * 21 + jung) * 28 + 4)      # 더미 받침 'ㄴ' → 받침형 모음
    g = _cell(ref)
    if not any(g[7]) and any(g[6]):                     # 7행이 비었으면 1px 내려 붙인다
        g = _cell(ref, off=2)
    top = tuple(map(tuple, g[:8]))
    bot = tuple(map(tuple, _cell(ch)[8:])) if jong else BLANK8
    return top, bot


def natural_glyphs(ch):
    """음절 자체를 위/아래로 그냥 자른 형태 (받침형 압축을 쓰지 않음)"""
    g = _cell(ch)
    return tuple(map(tuple, g[:8])), tuple(map(tuple, g[8:]))


def plan_glyphs(chars):
    """글자집합 → {글자: (상단,하단)}.
    기본은 받침형 상단 공유(슬롯 절약). 같은 모양으로 뭉개지는 글자만
    '자연 분할'로 바꿔 가독성을 지킨다. (예: 루/류/르)"""
    import collections
    plan = {c: ko_glyphs(c) for c in chars}
    while True:
        m = collections.defaultdict(list)
        for c, g in plan.items(): m[g].append(c)
        bad = [v for v in m.values() if len(v) > 1]
        if not bad: break
        changed = False
        for grp in bad:
            for c in grp:
                if plan[c] != natural_glyphs(c):
                    plan[c] = natural_glyphs(c); changed = True
        if not changed:
            raise RuntimeError('해소 불가 충돌: %s' % bad)
    return plan


def allocate(texts):
    """번역문들 → 슬롯 할당표. 반환 (슬롯목록, 음절→(상코드,하코드), 통계)"""
    order = []; index = {}
    def slot(bitmap):
        if bitmap not in index:
            index[bitmap] = len(order); order.append(bitmap)
        return index[bitmap]
    mapping = {}
    for t in texts:
        for ch in t:
            if ch in ('\n',): continue
            if ch in mapping: continue
            top, bot = ko_glyphs(ch)
            mapping[ch] = (slot(top), slot(bot))
    stats = dict(slots=len(order), limit=SLOT_LIMIT, remain=SLOT_LIMIT - len(order),
                 chars=len(mapping))
    return order, mapping, stats


def slot_report(texts):
    order, mapping, st = allocate(texts)
    print(f"슬롯 {st['slots']} / {st['limit']}  (여유 {st['remain']})   고유 글자 {st['chars']}")
    if st['remain'] < 0:
        # 초과 유발 글자 지목: 마지막에 새 슬롯을 만든 글자들
        seen = set(); culprits = []
        used = 0
        for t in texts:
            for ch in t:
                if ch in seen: continue
                seen.add(ch)
                top, bot = ko_glyphs(ch)
                new = sum(1 for b in (top, bot) if b not in seen)
                used += 1
        print('  ※ 초과 상태 — 희귀 (초성,중성) 조합을 쓰는 글자를 줄이세요.')
    return st


def main():
    if len(sys.argv) < 2: print(__doc__); return
    cmd = sys.argv[1]
    if cmd == 'dump':
        rom = open(sys.argv[2], 'rb').read()
        out = sys.argv[3] if len(sys.argv) > 3 else 'ss1_script.tsv'
        rows = scan(rom)
        with open(out, 'w') as f:
            f.write('# addr\tlen\tjp\tko(번역을 여기에)\n')
            for a, b in rows: f.write('%06X\t%d\t%s\t\n' % (a, len(b), decode(b)))
        print(f'{len(rows)}문자열 → {out}')
    elif cmd == 'verify':
        rom = open(sys.argv[2], 'rb').read()
        rows = scan(rom); ok = bad = 0
        for a, b in rows:
            try:
                if encode(decode(b)) == b: ok += 1
                else: bad += 1; print('불일치', hex(a))
            except Exception as e:
                bad += 1; print('오류', hex(a), e)
        print(f'왕복검증: 일치 {ok} / 불일치 {bad}')
    elif cmd == 'slots':
        texts = []
        for line in open(sys.argv[2]):
            if line.startswith('#'): continue
            p = line.rstrip('\n').split('\t')
            if len(p) >= 4 and p[3].strip(): texts.append(p[3])
        slot_report(texts)
    elif cmd == 'font':
        texts = []
        for line in open(sys.argv[2]):
            if line.startswith('#'): continue
            p = line.rstrip('\n').split('\t')
            if len(p) >= 4 and p[3].strip(): texts.append(p[3])
        order, mapping, st = allocate(texts)
        from PIL import Image
        cols = 16; rows = (len(order) + cols - 1) // cols
        im = Image.new('L', (cols * 9, rows * 9), 40); px = im.load()
        for i, bm in enumerate(order):
            gx, gy = (i % cols) * 9, (i // cols) * 9
            for r in range(8):
                for k in range(8):
                    if bm[r][k]: px[gx + k, gy + r] = 255
        out = sys.argv[3] if len(sys.argv) > 3 else 'ss1_font_sheet.png'
        im.resize((im.width * 4, im.height * 4), Image.NEAREST).save(out)
        print(f"슬롯 {st['slots']}/{st['limit']} → {out}")
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
