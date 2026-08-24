#!/usr/bin/env python3
"""build_logo_ko.py — SVC 타이틀 큰 로고 「最強ファイターズ」 -> 「최강 파이터즈」

    python3 build_logo_ko.py <입력.ngc> <출력.ngc> [--font Galmuri11-Bold.ttf] [--ips 출력.ips]

## 구조 (실측)

로고는 타일맵 평면 SCR1 의 **행4~10 × 열2~17** 에 있다. 128 × 56px, 타일 109장.
이 구간은 통째로 쓸 수 있다 — 다른 행과 공유하는 슬롯이 없고, 영역 안 중복도 한 장뿐이다.

읽히는 사본은 기록 주소 **+0x150000** 쪽이다 (타이틀 머리글과 같다).
109장 중 108장이 그 관계를 만족하고, 나머지 한 장(`0x01B0C0`)은 내용이 우연히 겹친
자리라 건드리지 않는다.

팔레트(실측): **0 = 투명, 1 = 주황(231,70,22), 2 = 빨강(201,19,38), 3 = 남색 외곽선**.

## 배치

원판은 「最強」(큰 한자 2자) + 「ファイターズ」 가 기울어 흐르는 그림 로고다.
한글은 그 위계를 두 줄로 옮긴다.

    「최강 파이터즈」  가로 2배 · 세로 4배 (음절당 약 19 × 40px), 한 줄

원판도 한 줄이고 글자가 세로로 긴 비례라 그 쪽에 맞췄다. 주황 채움 + 남색 1px 외곽선.

**맨 아랫줄(행10)은 비워 둔다.** 열9와 열10이 한 슬롯(`0x1B7690`)을 공유해서 서로 다른
그림을 넣을 수 없다. 그래서 그리는 높이를 48px 로 제한하고 마지막 타일 줄은 안 건드린다.
원판의 기울기·그라데이션까지는 글꼴 렌더링으로 안 된다 — 사람이 그려야 할 영역이다.
"""
import sys, os, argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tiletool'))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'SS1_SamuraiShodown_NGP', 'tools'))
import tilemap as TM

REC = os.path.join(HERE, '..', 'tiletool', 'rec_svc', '타이틀.json')
DELTA = 0x150000
ROWS = list(range(4, 11))
COLS = list(range(2, 18))
W, H = len(COLS) * 8, len(ROWS) * 8      # 128 x 56
ORANGE, RED, LINE = 1, 2, 3
LINES = [('최강 파이터즈', 2, 4)]   # (글자들, 가로배수, 세로배수). 빈칸은 띄어쓰기
CHAR_GAP = 1        # 음절 사이
WORD_GAP = 7        # 낱말 사이 (빈칸 자리)
LINE_GAP = 3
# 행10(맨 아랫줄)은 비워 둔다 — 열9·10 이 한 슬롯을 공유해서 서로 다른 그림을 못 넣는다.
DRAW_H = 48


def glyph(ch, font, sx, sy):
    f = ImageFont.truetype(font, 11)
    im = Image.new('L', (64, 64), 0)
    ImageDraw.Draw(im).text((6, 6), ch, font=f, fill=255)
    a = np.array(im) > 127
    ys, xs = np.nonzero(a)
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return np.kron(a, np.ones((sy, sx), bool))


def art(font, fill=ORANGE):
    lines = []
    for text, sx, sy in LINES:
        row = [(glyph(c, font, sx, sy) if c != ' ' else None) for c in text]
        lines.append(row)
    hs = [max(g.shape[0] for g in L if g is not None) for L in lines]
    tot = sum(hs) + LINE_GAP * (len(lines) - 1)
    if tot > DRAW_H:
        raise SystemExit('로고 높이 %dpx 가 %dpx 를 넘는다 (맨 아랫줄은 비워야 한다)'
                         % (tot, DRAW_H))
    m = np.zeros((H, W), bool)
    y = (DRAW_H - tot) // 2
    for L, hh in zip(lines, hs):
        wsum = sum((g.shape[1] if g is not None else WORD_GAP) for g in L) \
            + CHAR_GAP * (len(L) - 1)
        if wsum > W:
            raise SystemExit('로고 폭 %dpx 가 %dpx 를 넘는다' % (wsum, W))
        x = (W - wsum) // 2
        for g in L:
            if g is None:
                x += WORD_GAP + CHAR_GAP
                continue
            m[y:y + g.shape[0], x:x + g.shape[1]] |= g
            x += g.shape[1] + CHAR_GAP
        y += hh + LINE_GAP
    out = np.zeros((H, W), np.uint8)
    d = np.zeros_like(m)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            d |= np.roll(np.roll(m, dy, 0), dx, 1)
    out[d & ~m] = LINE
    out[m] = fill
    return out


def unpack(rom, ad):
    t = np.zeros((8, 8), np.uint8)
    for r in range(8):
        w = rom[ad + r * 2] | (rom[ad + r * 2 + 1] << 8)
        for c in range(8):
            t[r, c] = (w >> (14 - 2 * c)) & 3
    return t


def scr2_ghost_mask(orig, maps, s2r, grow=2):
    """SCR1 에 있던 원판 로고 그림의 자리 — SCR2 에서 지울 범위.

    SCR2 에도 같은 로고의 **외곽선 사본**이 따로 그려져 있다. SCR1 만 고치면
    SCR2 쪽 일본어 윤곽이 유령처럼 남는다. SCR1 원판 로고가 차지하던 픽셀을
    조금 부풀려 그 범위만 SCR2 에서 투명으로 만든다 (배경 하늘이 드러난다).
    """
    m1 = maps[1]
    g = np.zeros((len(ROWS) * 8, 20 * 8), bool)
    for i, r in enumerate(ROWS):
        for c in COLS:
            s = int(m1[r, c]) & 0x1FF
            if s not in s2r:
                continue
            t = unpack(orig, s2r[s])
            g[i * 8:i * 8 + 8, c * 8:c * 8 + 8] = t > 0
    for _ in range(grow):
        d = g.copy()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                d |= np.roll(np.roll(g, dy, 0), dx, 1)
        g = d
    return g


def _px(raw, y, x):
    w = raw[y * 2] | (raw[y * 2 + 1] << 8)
    return (w >> (14 - 2 * x)) & 3


def pack(t):
    raw = bytearray(16)
    for y in range(8):
        v = 0
        for x in range(8):
            v |= int(t[y, x]) << (14 - 2 * x)
        raw[y * 2] = v & 0xFF
        raw[y * 2 + 1] = v >> 8
    return bytes(raw)


def main(argv=None):
    ap = argparse.ArgumentParser(description='SVC 타이틀 큰 로고 한글화')
    ap.add_argument('rom')
    ap.add_argument('out')
    ap.add_argument('--font', default='Galmuri11-Bold.ttf')
    ap.add_argument('--fill', choices=('주황', '빨강'), default='주황')
    ap.add_argument('--ips', default=None)
    ap.add_argument('--preview', default=None)
    ap.add_argument('--ghost-grow', type=int, default=1,
                    help='SCR2 에서 지울 범위를 원판 로고보다 몇 px 부풀릴지')
    ap.add_argument('--max-shared-diff', type=int, default=24,
                    help='영역 안 중복 슬롯에서 허용할 어긋난 픽셀 수')
    a = ap.parse_args(argv)

    with open(a.rom, 'rb') as f:
        orig = f.read()
    rom = bytearray(orig)
    _, maps, s2r = TM.load_record(REC)
    m = maps[1]
    A = art(a.font, ORANGE if a.fill == '주황' else RED)

    want = {}
    clash = []
    skipped = 0
    for i, r in enumerate(ROWS):
        for j, c in enumerate(COLS):
            s = int(m[r, c]) & 0x1FF
            if s not in s2r:
                continue
            ad = s2r[s]
            if orig[ad:ad + 16] != orig[ad + DELTA:ad + DELTA + 16]:
                skipped += 1            # 사본 관계가 아닌 자리 — 우연히 내용이 겹친 주소다
                continue
            b = pack(A[i * 8:i * 8 + 8, j * 8:j * 8 + 8])
            tgt = ad + DELTA
            if tgt in want and want[tgt] != b:
                # 영역 안에서 한 슬롯을 두 칸이 공유한다. 한 벌만 쓸 수 있으므로
                # 먼저 계산된 쪽을 쓰고 어긋난 픽셀 수를 보고한다.
                nd = sum(1 for y in range(8) for x in range(8)
                         if _px(want[tgt], y, x) != _px(b, y, x))
                if nd > a.max_shared_diff:
                    raise SystemExit('중복 슬롯 0x%06X 이 %d픽셀 어긋난다 (행%d 열%d)'
                                     % (tgt, nd, r, c))
                clash.append((tgt, r, c, nd))
                continue
            want[tgt] = b
    for ad, b in want.items():
        rom[ad:ad + 16] = b
    for ad, r, c, nd in clash:
        print('  중복 슬롯 0x%06X: 행%d 열%d 가 %d픽셀 양보' % (ad, r, c, nd))

    # --- SCR2 에 남는 원판 로고 외곽선 지우기 ---
    m2 = maps[2]
    ghost = scr2_ghost_mask(orig, maps, s2r, a.ghost_grow)
    outside = set()
    for r in list(range(0, ROWS[0])) + list(range(ROWS[-1] + 1, 32)):
        for c in range(32):
            v = int(m2[r, c]) & 0x1FF
            if v in s2r:
                outside.add(v)
    for r in range(32):
        for c in range(32):
            v = int(maps[1][r, c]) & 0x1FF
            if v in s2r:
                outside.add(v)
    w2 = {}
    n2 = skip2 = 0
    for i, r in enumerate(ROWS):
        for c in range(20):
            s = int(m2[r, c]) & 0x1FF
            if s not in s2r or s in outside:
                skip2 += 1
                continue
            ad = s2r[s]
            if orig[ad:ad + 16] != orig[ad + DELTA:ad + DELTA + 16]:
                skip2 += 1
                continue
            t = unpack(orig, ad + DELTA)
            sub = ghost[i * 8:i * 8 + 8, c * 8:c * 8 + 8]
            t[sub] = 0
            b = pack(t)
            tgt = ad + DELTA
            if tgt in w2 and w2[tgt] != b:
                skip2 += 1                # 같은 슬롯을 두 칸이 쓴다 — 먼저 계산된 쪽을 둔다
                continue
            w2[tgt] = b
    for ad, b in w2.items():
        if rom[ad:ad + 16] != b:
            rom[ad:ad + 16] = b
            n2 += 1

    with open(a.out, 'wb') as f:
        f.write(bytes(rom))
    print('로고 타일 %d장 기록 (사본 관계 아님 %d장 건너뜀) -> %s' % (len(want), skipped, a.out))
    print('SCR2 유령 외곽선 %d장 정리 (건너뜀 %d)' % (n2, skip2))

    if a.preview:
        PAL = np.array([(20, 60, 140), (231, 70, 22), (201, 19, 38), (44, 42, 122)], np.uint8)
        Image.fromarray(PAL[A]).resize((W * 5, H * 5), Image.NEAREST).save(a.preview)

    if a.ips:
        from mkips import make
        from ips import apply_ips
        p = make(orig, bytes(rom))
        with open(a.ips, 'wb') as f:
            f.write(p)
        assert apply_ips(orig, p) == bytes(rom), 'IPS 왕복 검증 실패'
        print('IPS %d바이트 -> %s (왕복 검증 통과)' % (len(p), a.ips))
    return 0


if __name__ == '__main__':
    sys.exit(main())
