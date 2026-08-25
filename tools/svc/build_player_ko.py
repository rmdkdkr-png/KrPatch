#!/usr/bin/env python3
"""build_player_ko.py — SVC 캐릭터 선택 화면 머리글을 한글로.

    python3 build_player_ko.py <입력.ngc> <출력.ngc> [--font Galmuri11-Bold.ttf] [--ips 출력.ips]
    python3 build_player_ko.py <입력.ngc> <구운롬.ngc> --check --core <libretro.so>

    PLAYER SELECT -> 플레이어 선택

## 구조 (실측)

메뉴 머리글 3종과 달리 **스프라이트가 아니라 타일맵**이다.
`SCR1` 행0~1 × 열1~18 (18칸 × 2줄, 144×16px)에 뜨고, VRAM 슬롯이 134~169로 이어진다.

타일은 `0x31F810` 부터 **연속 36장**이다. 이름판과 같은 `[윗줄 18장][아랫줄 18장]` 스트립.
36슬롯 전부가 `start + i*16` 을 유일하게 만족했고, 첫 타일에 표식을 심어 부팅해
화면 행0·열1 만 변하는 것을 확인했다 — **읽히는 사본이 맞다.**
(타이틀 타일은 사본이 둘이라 `+0x150000` 쪽이 읽혔다. 이건 사본이 하나다.)

관측 9화면 중 이 구간을 쓰는 것은 캐릭터 선택뿐이다. 다른 화면과 안 나눠 쓴다.

## 색

    0 투명   1 검은 외곽선   2 노란 채움   3 글자 뒤 파란 띠

파란 띠는 **글자보다 얇다**. 띠는 y6~11(6px), 글자는 y3~13(11px)이라 글자가 띠 위아래로
삐져나온다. 그래서 메뉴 머리글처럼 "원판 글자 자리도 띠에 포함" 규칙을 쓰면 안 된다 —
띠가 글자 높이만큼 두꺼워진다.

여기서는 **띠가 있는 열에서 위아래 끝을 읽고, 글자에 가린 열은 양옆에서 보간**한다.
메뉴 머리글에서 보간이 실패했던 것은 아는 열이 뾰족한 끝동강뿐이라 가운데가 홀쭉해져서였다.
여기는 144열 중 80열이 띠를 직접 보여 주고 빈 구간이 5열을 안 넘는다 — 보간이 안전하다.

## 조판

**Galmuri14 를 ppem 14 로, 배율 없이 그대로** 쓴다 (잉크 13×11~12px).
스트립이 16px 라 14px 글꼴이 외곽선까지 넣고도 들어간다 — 늘릴 필요가 없다.

다른 자리와 달리 여기만 Galmuri14 인 이유가 있다. 후보를 다 그려 보고 골랐다.

    Galmuri11-Bold ppem11 가로x2   글자가 뭉갠다. 가로만 늘리면 획이 2px/1px 로 어긋나는데
                                   「플」은 ㅍ·ㅡ·ㄹ 이 전부 가로획이라 통짜 덩어리가 된다
    Galmuri7 ppem8 x2 (등방)        7x7 에 「플」·「택」의 받침이 안 들어가 획이 붙는다
                                   (이름판의 「쿄」·「테리」는 단순해서 됐던 것뿐이다)
    Galmuri14 ppem14 (등방·원본크기)  음절이 또렷하다. 스트립 높이가 허락하므로 이걸 쓴다

글자마다 bbox 로 잘라내면 기준선이 어긋나므로 **세로는 공통 범위로** 자른다.
"""
import sys, os, argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tiletool'))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'SS1_SamuraiShodown_NGP', 'tools'))

LINE, FILL, RIBBON = 1, 2, 3
PPEM, STRETCH_X = 14, 1        # 원본 크기 그대로 — 늘리지 않는다
GAP, SPACE = 4, 14

START = 0x31F810
W = 18                      # 스트립 한 줄의 타일 수
TEXT = '플레이어 선택'

SCR1 = 0x9000
ROWS = (0, 1)
COLS = range(1, 19)


def unpack(b):
    t = np.zeros((8, 8), np.uint8)
    for y in range(8):
        v = b[y * 2] | (b[y * 2 + 1] << 8)
        for x in range(8):
            t[y, x] = (v >> (14 - 2 * x)) & 3
    return t


def pack(t):
    raw = bytearray(16)
    for y in range(8):
        v = 0
        for x in range(8):
            v |= int(t[y, x]) << (14 - 2 * x)
        raw[y * 2] = v & 0xFF
        raw[y * 2 + 1] = v >> 8
    return bytes(raw)


def strip_art(rom):
    """롬의 스트립 36장을 144×16 도안으로 편다."""
    A = np.zeros((16, W * 8), np.uint8)
    for i in range(W):
        A[0:8, i * 8:i * 8 + 8] = unpack(rom[START + i * 16:START + i * 16 + 16])
        A[8:16, i * 8:i * 8 + 8] = unpack(rom[START + (W + i) * 16:START + (W + i) * 16 + 16])
    return A


def write_strip(rom, A):
    for i in range(W):
        rom[START + i * 16:START + i * 16 + 16] = pack(A[0:8, i * 8:i * 8 + 8])
        b = START + (W + i) * 16
        rom[b:b + 16] = pack(A[8:16, i * 8:i * 8 + 8])


def band_of(A):
    """열마다 파란 띠의 위아래 끝. 글자에 가린 열은 양옆에서 보간한다."""
    known = {}
    for x in range(A.shape[1]):
        ys = np.nonzero(A[:, x] == RIBBON)[0]
        if len(ys):
            known[x] = (int(ys.min()), int(ys.max()))
    if not known:
        return {}
    xs = sorted(known)
    band = {}
    for x in range(A.shape[1]):
        if x in known:
            band[x] = known[x]
            continue
        left = [k for k in xs if k < x]
        right = [k for k in xs if k > x]
        if not left or not right:
            continue                       # 띠가 시작하기 전 / 끝난 뒤 — 띠 없음
        a, b = left[-1], right[0]
        w = (x - a) / (b - a)
        band[x] = tuple(int(round(known[a][i] + (known[b][i] - known[a][i]) * w))
                        for i in (0, 1))
    return band


def glyphs(text, font):
    """어절마다 글자 비트맵. 세로는 **공통 범위**로 잘라 기준선을 맞춘다."""
    f = ImageFont.truetype(font, PPEM)
    raw = {}
    for ch in text.replace(' ', ''):
        im = Image.new('L', (40, 40), 0)
        ImageDraw.Draw(im).text((8, 8), ch, font=f, fill=255)
        raw[ch] = np.array(im) > 127
    ys = [np.nonzero(a.any(1))[0] for a in raw.values()]
    y0, y1 = min(y.min() for y in ys), max(y.max() for y in ys)
    out = []
    for word in text.split(' '):
        gs = []
        for ch in word:
            a = raw[ch][y0:y1 + 1]
            xs = np.nonzero(a.any(0))[0]
            a = a[:, xs.min():xs.max() + 1]
            gs.append(np.kron(a, np.ones((1, STRETCH_X), bool)))   # 가로만 정수 배율
        out.append(gs)
    return out


def build(A, text, font):
    H, WD = A.shape
    band = band_of(A)
    ink = (A == LINE) | (A == FILL)
    ys, xs = np.nonzero(ink)
    y_lo, y_hi = int(ys.min()), int(ys.max())          # 원판 글자가 앉던 세로 범위

    out = A.copy()
    for x in range(WD):
        col = ink[:, x]
        if not col.any():
            continue
        out[col, x] = 0
        if x in band:
            lo, hi = band[x]
            sel = np.zeros(H, bool)
            sel[lo:hi + 1] = True
            out[sel & col, x] = RIBBON

    words = glyphs(text, font)
    wid = [sum(g.shape[1] for g in gs) + GAP * (len(gs) - 1) for gs in words]
    total = sum(wid) + SPACE * (len(words) - 1)
    if total > WD:
        raise SystemExit('%s 가 %dpx 에 안 들어간다 (%dpx)' % (text, WD, total))
    gh = max(g.shape[0] for gs in words for g in gs)
    y = y_lo + (y_hi - y_lo + 1 - gh) // 2
    x = (WD - total) // 2

    m = np.zeros((H, WD), bool)
    for gs, w in zip(words, wid):
        for g in gs:
            m[y:y + g.shape[0], x:x + g.shape[1]] |= g
            x += g.shape[1] + GAP
        x += SPACE - GAP
    d = np.zeros_like(m)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            d |= np.roll(np.roll(m, dy, 0), dx, 1)
    out[d & ~m] = LINE
    out[m] = FILL
    return out, (total, gh, y)


def screen_art(rom_path, core=None, presses=5):
    """구운 롬을 부팅해 머리글 36칸을 화면대로 합성한다."""
    import struct
    from observe import make_harness
    import tilemap as TM
    n = make_harness(rom_path, core)
    n.run(1300)
    for _ in range(presses):
        n.press('a', 8)
        n.run(70)
    n.run(200)
    v = TM.dump_vram(n)
    tiles = TM.tile_table(v)
    A = np.zeros((16, W * 8), np.uint8)
    for r in ROWS:
        for j, c in enumerate(COLS):
            s = struct.unpack_from('<H', v, SCR1 - 0x8000 + (r * 32 + c) * 2)[0] & TM.PAT_MASK
            A[r * 8:r * 8 + 8, j * 8:j * 8 + 8] = tiles[s]
    return A


def main(argv=None):
    ap = argparse.ArgumentParser(description='SVC 캐릭터 선택 머리글 한글화')
    ap.add_argument('rom')
    ap.add_argument('out')
    ap.add_argument('--font', default='Galmuri14.ttf')
    ap.add_argument('--text', default=TEXT)
    ap.add_argument('--ips', default=None)
    ap.add_argument('--preview', default=None)
    ap.add_argument('--core', default=None)
    ap.add_argument('--check', action='store_true',
                    help='굽지 않고, out 을 구운 롬으로 보고 화면과 도안을 대조한다')
    a = ap.parse_args(argv)

    with open(a.rom, 'rb') as f:
        orig = f.read()
    A = strip_art(orig)
    art, (total, gh, y) = build(A, a.text, a.font)

    if a.check:
        got = screen_art(a.out, a.core)
        diff = art != got
        print('도안 %s / 화면 %s' % (art.shape, got.shape))
        print('다른 픽셀 %d / %d' % (int(diff.sum()), diff.size))
        if diff.sum():
            ys, xs = np.nonzero(diff)
            print('자리: %s' % [(int(y_), int(x_)) for y_, x_ in zip(ys[:10], xs[:10])])
            return 1
        print('머리글이 의도한 그림 그대로 화면에 뜬다')
        return 0

    rom = bytearray(orig)
    write_strip(rom, art)
    print('%s -> %s  타일 %d장 기록 (글자 %dpx 폭, 높이 %dpx, y=%d)'
          % ('PLAYER SELECT', a.text, 2 * W, total, gh, y))

    if a.preview:
        PAL = np.array([(255, 0, 255), (30, 30, 30), (250, 220, 40), (40, 80, 220)], np.uint8)
        cv = Image.new('RGB', (W * 8 * 4, 2 * 64 + 8), (20, 20, 20))
        cv.paste(Image.fromarray(PAL[A]).resize((W * 8 * 4, 64), Image.NEAREST), (0, 0))
        cv.paste(Image.fromarray(PAL[art]).resize((W * 8 * 4, 64), Image.NEAREST), (0, 72))
        cv.save(a.preview)
        print('도안 -> %s' % a.preview)

    with open(a.out, 'wb') as f:
        f.write(bytes(rom))
    print('-> %s' % a.out)

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
