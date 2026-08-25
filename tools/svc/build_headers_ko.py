#!/usr/bin/env python3
"""build_headers_ko.py — SVC 메뉴 머리글 3종을 한글로.

    python3 build_headers_ko.py <입력.ngc> <출력.ngc> [--font Galmuri11-Bold.ttf] [--ips 출력.ips]

    MAIN MENU    -> 메인 메뉴
    GAME SELECT  -> 게임 선택
    STYLE SELECT -> 스타일 선택

## 구조 (실측)

머리글은 타일맵이 아니라 **스프라이트**다. 세 화면이 타일 풀 하나
(`0x22A800`~`0x22AF00`, 112장)를 나눠 쓴다.

    MAIN MENU     타일  0~26   (0x22A800~0x22A9A0)
    STYLE SELECT  타일 27~62   (0x22A9B0~0x22ABE0)
    GAME SELECT   타일 64~98   (0x22AC00~0x22AE20)

**본체는 안 겹친다.** 겹치는 건 띠 끝동강 몇 장뿐이다(타일 99·102 등 — 화면끼리 공유).
그래서 **자기 구간 밖 타일은 건드리지 않는다.** 끝동강은 글자가 없는 장식이라
원판 그대로 둬도 아무 문제가 없다. 이 규칙을 안 지키고 셋을 한 롬에 구웠더니
서로의 띠를 덮어써서 셋 다 깨졌다.

y 값이 여러 개로 나오는 것은 애니메이션이 아니다 — 끝동강이 별도 스프라이트라서다.
글자 자체는 가로 한 줄이고, 900프레임을 지켜봐도 좌표가 안 변한다.

## 주소를 어떻게 잡나

내용으로 찾으면 안 된다. 파란 띠 타일은 여러 장이 내용이 같아서 첫 일치를 쓰면
남의 자리에 글자를 써 넣는다. 그래서 **풀의 타일마다 번호를 점으로 심은 롬**을 만들어
화면에서 번호를 직접 읽는다. 번호는 `k mod 64` 라 후보가 둘인데, 원판 내용이 맞는
쪽을 골라 확정한다.

## 한 화면 안에서도 타일이 겹친다

`MAIN MENU` 는 32칸이 고유 타일 **30장**만 쓴다. 두 장이 두 칸씩에 걸려 있다
(`MAIN` 의 M 과 `MENU` 의 M 이 같은 타일이다). 그 칸에 서로 다른 그림을 넣으면
나중 쓰기가 앞 쓰기를 덮어 두 칸 다 어긋난다 — 실제로 6칸이 깨졌다.

그래서 **글자를 가로로 움직여 가며 겹친 칸의 그림이 서로 같아지는 자리**를 찾는다.
가운데에서 가까운 순으로 훑고, 조건을 만족하는 첫 자리를 쓴다. 겹친 칸이 둘 다
글자 없는 띠만 남으면 조건이 성립한다. 조건에는 **안 쓰는 공유 끝동강 위에
획이 걸치지 않을 것**도 넣는다 — 걸치면 그 획만 화면에서 빠진다.

## 원판 띠를 지키는 법

이 타일에는 글자(1=검은 외곽선, 2=노란 채움)와 **그 뒤의 파란 띠(3)**가 같이 있다.
글자만 지우고 나머지를 투명으로 두면 띠가 글자 자리마다 끊긴다.

띠 범위는 열마다 **파란 픽셀 + 원판 글자 픽셀**의 위아래 끝으로 잡는다.
원판 글자가 있던 자리는 띠가 덮고 있었기 때문이다. 파란 픽셀만 보면 글자에 가린 열에서
띠가 얇아지고, 양옆에서 보간하면 끝동강이 뾰족해 가운데가 홀쭉해진다 — 둘 다 겪었다.

## 조판

**Galmuri11-Bold ppem 11 을 가로만 정수 2배** (20×10px).
띠가 12px 뿐이라 세로는 못 키운다. 1.5배로 늘리면 어떤 열은 1px, 어떤 열은 2px 이 되어
획이 고르지 않다 — 픽셀 글꼴은 정수 배율로만 늘린다.

세로 중앙은 **띠 본체**(열마다 잰 범위의 최빈값) 기준으로 잡는다. 끝동강까지 넣어
최대/최소를 쓰면 글자가 위로 밀려 화면 밖으로 잘린다 (STYLE SELECT 에서 실제로 잘렸다).
"""
import sys, os, struct, argparse, tempfile
from collections import Counter, defaultdict
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tiletool'))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'SS1_SamuraiShodown_NGP', 'tools'))
import tilemap as TM

LINE, FILL, RIBBON = 1, 2, 3
PPEM, STRETCH_X = 11, 2
GAP = 2
POOL = 0x22A800

# (이름, A 누르는 횟수, 한글, 자기 타일 번호 구간)
HEADERS = [
    ('MAIN MENU',    2, '메인 메뉴',   (0, 26)),
    ('STYLE SELECT', 4, '스타일 선택', (27, 62)),
    ('GAME SELECT',  3, '게임 선택',   (64, 98)),
]


def pack(t):
    raw = bytearray(16)
    for yy in range(8):
        v = 0
        for xx in range(8):
            v |= int(t[yy, xx]) << (14 - 2 * xx)
        raw[yy * 2] = v & 0xFF
        raw[yy * 2 + 1] = v >> 8
    return bytes(raw)


def glyph(ch, font):
    f = ImageFont.truetype(font, PPEM)
    im = Image.new('L', (48, 48), 0)
    ImageDraw.Draw(im).text((4, 4), ch, font=f, fill=255)
    a = np.array(im) > 127
    ys, xs = np.nonzero(a)
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return np.kron(a, np.ones((1, STRETCH_X), bool))       # 가로만 정수 배율


def numbered_rom(rom, ntiles=112):
    """풀의 타일마다 (k mod 64) 자리에 점을 찍은 롬."""
    out = bytearray(rom)
    for k in range(ntiles):
        t = np.zeros((8, 8), np.uint8)
        kk = k % 64
        t[kk // 8, kk % 8] = 2
        out[POOL + k * 16:POOL + k * 16 + 16] = pack(t)
    return bytes(out)


def capture(rom_path, presses, core=None):
    from observe import make_harness
    n = make_harness(rom_path, core)
    n.run(1300)
    for _ in range(presses):
        n.press('a', 8)
        n.run(70)
    n.run(200)
    v = TM.dump_vram(n)
    out = []
    for i in range(64):
        o = 0x8800 - 0x8000 + i * 4
        b0, b1, b2, b3 = v[o], v[o + 1], v[o + 2], v[o + 3]
        if not (b1 & 0x18) or b3 > 30:
            continue
        out.append((b0 | ((b1 & 1) << 8), b2, b3))
    return out, v


def compose(vram, sprites):
    tiles = TM.tile_table(vram)
    W = max(x for _, x, _ in sprites) + 8
    H = max(y for _, _, y in sprites) + 8
    canvas = np.zeros((H, W), np.uint8)
    for pat, x, y in sprites:
        canvas[y:y + 8, x:x + 8] = tiles[pat]
    return canvas


def ribbon_band(canvas):
    """열마다 띠의 위아래 끝. **원판 글자 자리도 띠에 포함**시킨다."""
    H, W = canvas.shape
    known = {}
    for x in range(W):
        col = canvas[:, x]
        ys = np.nonzero((col == RIBBON) | (col == LINE) | (col == FILL))[0]
        if len(ys):
            known[x] = (int(ys.min()), int(ys.max()))
    if not known:
        return {}
    full = (min(v[0] for v in known.values()), max(v[1] for v in known.values()))
    return {x: known.get(x, full) for x in range(W)}


def strip_letters(canvas, band):
    """원판 글자를 지우고 그 자리에 띠 색을 되살린다."""
    out = canvas.copy()
    ink = (out == LINE) | (out == FILL)
    for x in range(out.shape[1]):
        col = ink[:, x]
        if not col.any():
            continue
        out[col, x] = 0
        lo, hi = band[x]
        sel = np.zeros(out.shape[0], bool)
        sel[lo:hi + 1] = True
        out[sel & col, x] = RIBBON
    return out


SPACE = 10


def layout(text, font):
    """어절마다 (글자들, 어절 폭). 어절을 따로 움직일 수 있어야 겹친 칸을 피한다."""
    out = []
    for word in text.split(' '):
        gs = [glyph(c, font) for c in word]
        out.append((gs, sum(g.shape[1] for g in gs) + GAP * (len(gs) - 1)))
    return out


def natural(words, W):
    """가운데 정렬했을 때 어절들의 시작 x."""
    total = sum(w for _, w in words) + SPACE * (len(words) - 1)
    x = (W - total) // 2
    starts = []
    for _, w in words:
        starts.append(x)
        x += w + SPACE
    return starts


def text_mask(shape, band, words, starts):
    """어절을 starts 에 놓은 글자 마스크. 캔버스를 벗어나면 None."""
    H, W = shape
    # 세로 중앙은 **띠 본체**(최빈 범위) 기준
    lo, hi = Counter(band.values()).most_common(1)[0][0]
    gh = max(g.shape[0] for gs, _ in words for g in gs)
    y = lo + (hi - lo + 1 - gh) // 2
    if y < 0 or y + gh > H:
        return None
    m = np.zeros((H, W), bool)
    for (gs, _), x in zip(words, starts):
        for g in gs:
            if x < 0 or x + g.shape[1] > W:
                return None
            m[y:y + g.shape[0], x:x + g.shape[1]] |= g
            x += g.shape[1] + GAP
    return m


def paint(base, m):
    out = base.copy()
    d = np.zeros_like(m)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            d |= np.roll(np.roll(m, dy, 0), dx, 1)
    out[d & ~m] = LINE
    out[m] = FILL
    return out


def resolve(orig, vram, sprites, numbers, rng):
    """스프라이트마다 (풀 타일 번호, 우리가 쓸 수 있는 칸인가)."""
    n0, n1 = rng
    plan = []
    for pat, x, y in sprites:
        k = numbers.get((x, y))
        idx = None
        if k is not None:
            tile = TM.tile_raw(vram, pat)
            for b in (0, 64):          # 번호는 k mod 64 — 원판 내용이 맞는 쪽
                if orig[POOL + (k + b) * 16:POOL + (k + b) * 16 + 16] == tile:
                    idx = k + b
                    break
        plan.append((x, y, idx, idx is not None and n0 <= idx <= n1))
    return plan


def alias_groups(plan):
    """한 화면 안에서 **같은 타일을 쓰는 칸들**. 그림이 서로 달라지면 안 된다."""
    by = defaultdict(list)
    for x, y, idx, writable in plan:
        if writable:
            by[idx].append((x, y))
    return [c for c in by.values() if len(c) > 1]


def harmonize(base, alias):
    """겹친 칸의 바탕을 첫 칸 것으로 통일한다.

    원판에서는 같은 타일이라 바탕이 애초에 같았는데, 띠를 열 단위로 되살리면
    열마다 띠 두께가 1px 씩 달라져 어긋날 수 있다. 첫 칸 것으로 맞춰 둔다.
    """
    for cells in alias:
        x0, y0 = cells[0]
        blk = base[y0:y0 + 8, x0:x0 + 8]
        for x, y in cells[1:]:
            base[y:y + 8, x:x + 8] = blk
    return base


def place(base, band, words, plan, name='', slack=20):
    """겹친 칸이 어긋나지 않는 조판을 찾는다.

    어절을 통째로 좌우로 밀어 가며 훑는다. 가운데 정렬에서 가장 덜 어긋나는 것을 고른다.
    겹친 칸 위에서는 **글자 마스크가 서로 같아야** 한다 — 「메인 메뉴」가 되는 이유는
    48px 떨어진 두 겹침 칸에 「메」의 같은 부분이 오게 놓을 수 있어서다.
    """
    import itertools
    W = base.shape[1]
    base = harmonize(base.copy(), alias_groups(plan))
    alias = alias_groups(plan)
    keep = [(x, y) for x, y, idx, writable in plan if not writable]
    nat = natural(words, W)

    # 스프라이트 격자는 빈틈이 있다 (x=24 칸은 y=7~14 만 덮는다).
    # 그 밖에 떨어진 획은 어느 타일에도 안 들어가 화면에서 사라진다.
    covered = np.zeros(base.shape, bool)
    for x, y, idx, writable in plan:
        covered[y:y + 8, x:x + 8] = True

    rng = range(-slack, slack + 1)
    cands = sorted(itertools.product(rng, repeat=len(words)),
                   key=lambda d: (sum(abs(v) for v in d), d))
    best = None
    for deltas in cands:
        starts = [s + d for s, d in zip(nat, deltas)]
        if any(b < a + words[i][1] + 4 for i, (a, b) in
               enumerate(zip(starts, starts[1:]))):
            continue                       # 어절이 붙거나 순서가 뒤집힘
        m = text_mask(base.shape, band, words, starts)
        if m is None:
            continue
        if any(m[y:y + 8, x:x + 8].any() for x, y in keep):
            continue                       # 안 쓰는 공유 끝동강 위의 획은 화면에서 빠진다
        art = paint(base, m)
        # 마스크가 아니라 **그린 결과**로 비교한다. 외곽선은 칸 경계를 넘어 옆 칸의
        # 획에서도 번지므로, 마스크만 같아도 그림이 달라질 수 있다.
        if any(not np.array_equal(art[c[1]:c[1] + 8, c[0]:c[0] + 8],
                                  art[cells[0][1]:cells[0][1] + 8,
                                      cells[0][0]:cells[0][0] + 8])
               for cells in alias for c in cells[1:]):
            continue
        lost = int((((art == LINE) | (art == FILL)) & ~covered).sum())
        if best is None or lost < best[0]:
            best = (lost, deltas, art, starts)
        if lost == 0:
            break
    if best is None:
        raise SystemExit('%s: 겹친 칸을 피하는 조판이 없다 — 문구나 글꼴을 바꿔야 한다' % name)
    lost, deltas, art, starts = best
    if any(deltas):
        print('   %s 어절을 %s 옮겨 겹친 칸을 피함'
              % (name, ', '.join('%+d' % d for d in deltas)))
    if lost:
        print('   %s 스프라이트 빈틈에 획 %d픽셀이 떨어진다 (더 나은 자리가 없다)'
              % (name, lost))
    return art, starts


def main(argv=None):
    ap = argparse.ArgumentParser(description='SVC 메뉴 머리글 한글화')
    ap.add_argument('rom')
    ap.add_argument('out')
    ap.add_argument('--font', default='Galmuri11-Bold.ttf')
    ap.add_argument('--core', default=None)
    ap.add_argument('--ips', default=None)
    ap.add_argument('--shots', default=None)
    a = ap.parse_args(argv)

    with open(a.rom, 'rb') as f:
        orig = f.read()
    rom = bytearray(orig)

    fd, numpath = tempfile.mkstemp(suffix='.ngc')
    os.write(fd, numbered_rom(orig))
    os.close(fd)
    try:
        for en, presses, ko, rng in HEADERS:
            sprites, vram = capture(a.rom, presses, a.core)
            nsp, nvram = capture(numpath, presses, a.core)
            if not sprites:
                print('%-13s 스프라이트를 못 찾았다 — 건너뜀' % en)
                continue
            ntiles = TM.tile_table(nvram)
            numbers = {}
            for pat, x, y in nsp:
                ys, xs = np.nonzero(ntiles[pat] == 2)
                if len(ys):
                    numbers[(x, y)] = int(ys[0] * 8 + xs[0])

            canvas = compose(vram, sprites)
            band = ribbon_band(canvas)
            base = strip_letters(canvas, band)
            plan = resolve(orig, vram, sprites, numbers, rng)
            art, _ = place(base, band, layout(ko, a.font), plan, en)

            wrote = outside = unknown = 0
            for x, y, idx, writable in plan:
                if idx is None:
                    unknown += 1
                elif not writable:
                    outside += 1        # 다른 화면과 공유하는 끝동강 — 안 건드린다
                else:
                    ad = POOL + idx * 16
                    rom[ad:ad + 16] = pack(art[y:y + 8, x:x + 8])
                    wrote += 1
            print('%-13s -> %-9s 타일 %2d장 기록 (공유 끝동강 %d장 보존, 번호 불명 %d)'
                  % (en, ko, wrote, outside, unknown))

            if a.shots:
                os.makedirs(a.shots, exist_ok=True)
                PAL = np.array([(255, 140, 0), (20, 20, 20), (250, 210, 40), (40, 60, 200)],
                               np.uint8)
                Image.fromarray(PAL[art]).resize(
                    (art.shape[1] * 4, art.shape[0] * 4), Image.NEAREST).save(
                    os.path.join(a.shots, '%s.png' % en.replace(' ', '_')))
    finally:
        os.unlink(numpath)

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
