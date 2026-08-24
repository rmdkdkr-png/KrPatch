#!/usr/bin/env python3
"""build_header_ko.py — SVC 메인메뉴 머리글 `MAIN MENU` -> 「메인 메뉴」

    python3 build_header_ko.py <입력.ngc> <출력.ngc> [--font Galmuri14.ttf] [--ips 출력.ips]

## 구조 (실측)

머리글은 타일맵이 아니라 **스프라이트**다. 13열 × 2줄 = 26칸, `x = 28 + 8*i`,
윗줄 `y=6` / 아랫줄 `y=14`. 즉 **104 × 16px**.
열 i 의 패턴 번호는 윗줄 `4+2i`, 아랫줄 `5+2i` (패턴 4~29).

**타일 뱅크를 재사용한다.** 26칸이 쓰는 고유 타일은 24장뿐이다.
`MAIN` 의 M 과 `MENU` 의 M 이 같은 타일을 쓰기 때문이다.

    패턴 4 == 패턴 16   (0열 윗칸 == 6열 윗칸)   ROM 0x22A830
    패턴26 == 패턴 28   (11열 윗칸 == 12열 윗칸) ROM 0x22A980

한 주소를 고치면 두 칸이 같이 바뀐다. 그래서 **새 문안도 그 자리가 같아야 한다.**
「메인 메뉴」는 「메」가 두 번 나오고 그 두 번이 정확히 0열과 6열에 온다 — 제약에 그대로 맞는다.
11·12열은 둘 다 빈 칸이라 역시 맞는다.

읽히는 사본은 `0x22A830` 자체다 (타이틀과 달리 `+0x150000` 이 아니다 — 마커를 심어 확인).

## 배치

    열   0   1  2   3  4   5  6   7  8   9 10  11 12
        [빈][ 메  ][ 인  ][ 빈  ][ 메  ][ 뉴  ][ 빈 ]

0열·6열 윗칸은 둘 다 빈 칸, 11·12열 윗칸도 둘 다 빈 칸이라 공유 제약을 만족한다.
빌더가 쓰기 전에 이 제약을 직접 검사하고, 어기면 멈춘다.

글자는 16×16 한 칸씩. **Galmuri11-Bold 를 ppem 16** 으로 그린다.
Galmuri14 는 획이 1px 이라 1px 검은 외곽선에 먹혀 속이 안 보인다 — 굵은 획이 필요하다.
색은 원판과 같게 — **1 = 검은 외곽선, 2 = 노란 채움, 3 = 글자 뒤 파란 띠**.

**띠를 같이 그려야 한다.** 이 타일에는 글자만이 아니라 뒤에 깔린 파란 띠도 들어 있다.
글자만 그리고 나머지를 투명으로 두면 띠가 글자 자리마다 끊긴다 — 실제로 한 번 끊어 먹었다.
띠는 8줄 두께로 왼쪽 행1~8 에서 오른쪽 행3~10 으로 기운다.

글자는 원판과 같이 **행 0~11(12px)** 안에 넣는다. 12~15행은 띠 밖이라 거기까지 그리면
글자가 띠 아래로 삐져나온다. 높이를 못 키우는 대신 **가로로 1.5배 늘려** 가독성을 얻는다.
"""
import sys, os, argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'SS1_SamuraiShodown_NGP', 'tools'))

NCOL = 13
BANK = {                                  # 패턴 -> ROM 주소 (중복 패턴은 같은 주소)
    4: 0x22A830, 5: 0x22A840, 6: 0x22A850, 7: 0x22A860, 8: 0x22A870, 9: 0x22A880,
    10: 0x22A890, 11: 0x22A8A0, 12: 0x22A8B0, 13: 0x22A8C0, 14: 0x22A8D0, 15: 0x22A8E0,
    16: 0x22A830, 17: 0x22A8F0, 18: 0x22A900, 19: 0x22A910, 20: 0x22A920, 21: 0x22A930,
    22: 0x22A940, 23: 0x22A950, 24: 0x22A960, 25: 0x22A970, 26: 0x22A980, 27: 0x22A990,
    28: 0x22A980, 29: 0x22A9A0,
}
LINE, FILL, SHADE = 1, 2, 3   # 실측: 1=검은 외곽선, 2=노란 채움, 3=파란 그림자
PPEM = 11                 # Galmuri11-Bold 원래 크기 — 잉크 10px
STRETCH_X = 1.5           # 가로로만 늘린다. 띠가 12px 밖에 안 돼서 세로로는 못 키운다
TEXT_ROWS = (0, 11)       # 원판 글자가 쓰는 줄. 12~15행은 띠 밖이라 비워 둔다
RIBBON_ROWS = (2, 9)      # 띠를 평평하게 깐다 — 기울이면 0열과 6열이 달라져 공유 제약을 못 지킨다
LAYOUT = [('메', 1), ('인', 3), ('메', 7), ('뉴', 9)]   # (글자, 시작 열) — 아래 제약 참고


def glyph(ch, font):
    f = ImageFont.truetype(font, PPEM)
    im = Image.new('L', (48, 48), 0)
    ImageDraw.Draw(im).text((4, 4), ch, font=f, fill=255)
    a = np.array(im) > 127
    ys, xs = np.nonzero(a)
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    if STRETCH_X != 1:
        w = int(round(a.shape[1] * STRETCH_X))
        a = np.array(Image.fromarray(a.astype(np.uint8) * 255).resize(
            (w, a.shape[0]), Image.NEAREST)) > 127
    return a


def unpack(rom, ad):
    t = np.zeros((8, 8), np.uint8)
    for r in range(8):
        w = rom[ad + r * 2] | (rom[ad + r * 2 + 1] << 8)
        for c in range(8):
            t[r, c] = (w >> (14 - 2 * c)) & 3
    return t


def ribbon_mask(rom, ncol=NCOL, h=16):
    """글자 뒤에 깔린 **파란 띠**를 복원한다.

    머리글 스프라이트 타일에는 글자만이 아니라 그 뒤의 파란 띠도 같이 들어 있다.
    글자만 그리고 나머지를 투명으로 두면 띠가 글자 자리마다 끊긴다.
    원판 띠는 왼쪽 행1~8 에서 오른쪽 행3~10 으로 2px 기운다(실측). 그런데 기울이면
    0열과 6열의 띠 높이가 달라져 **공유 타일 제약**을 못 지킨다. 그래서 이 구간만
    행2~9 로 평평하게 깐다 — 양 끝에서 1px 어긋나지만 글자와 띠가 온전한 편이 낫다.
    원판에서 파랑이던 픽셀은 무조건 파랑으로 유지한다.
    """
    w = ncol * 8
    cur = np.zeros((h, w), np.uint8)
    for col in range(ncol):
        cur[0:8, col * 8:col * 8 + 8] = unpack(rom, BANK[4 + 2 * col])
        cur[8:16, col * 8:col * 8 + 8] = unpack(rom, BANK[5 + 2 * col])
    r = np.zeros((h, w), bool)
    r[RIBBON_ROWS[0]:RIBBON_ROWS[1] + 1, :] = True
    return r | (cur == SHADE)


def art(font, rom, ncol=NCOL, h=16):
    w = ncol * 8
    m = np.zeros((h, w), bool)
    for ch, col in LAYOUT:
        g = glyph(ch, font)
        gh, gw = g.shape
        x0 = col * 8 + (16 - gw) // 2
        y0 = TEXT_ROWS[0] + (TEXT_ROWS[1] - TEXT_ROWS[0] + 1 - gh) // 2
        m[y0:y0 + gh, max(x0, 0):max(x0, 0) + gw] |= g
    out = np.zeros((h, w), np.uint8)
    out[ribbon_mask(rom, ncol, h)] = SHADE   # 파란 띠 먼저 깔고
    d = np.zeros_like(m)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            d |= np.roll(np.roll(m, dy, 0), dx, 1)
    out[d & ~m] = LINE                       # 검은 외곽선
    out[m] = FILL                            # 노란 채움
    return out


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
    ap = argparse.ArgumentParser(description='SVC 메인메뉴 머리글 한글화')
    ap.add_argument('rom')
    ap.add_argument('out')
    ap.add_argument('--font', default='Galmuri11-Bold.ttf')
    ap.add_argument('--ips', default=None)
    ap.add_argument('--preview', default=None)
    ap.add_argument('--max-shared-diff', type=int, default=8,
                    help='공유 타일에서 허용할 어긋난 픽셀 수 (기본 8/64)')
    a = ap.parse_args(argv)

    with open(a.rom, 'rb') as f:
        orig = f.read()
    rom = bytearray(orig)
    A = art(a.font, orig)

    # 공유 주소는 한 벌만 쓸 수 있다 — 어긋나는 정도를 재서 허용치 안이면 진행한다
    want = {}
    clash = []
    for col in range(NCOL):
        for row, pat in ((0, 4 + 2 * col), (1, 5 + 2 * col)):
            tile = A[row * 8:row * 8 + 8, col * 8:col * 8 + 8]
            ad = BANK[pat]
            b = pack(tile)
            if ad in want and want[ad] != b:
                # 공유 타일은 한 벌만 쓸 수 있다. 띠가 기울어 있어 완전히 같기는 어려우므로
                # 먼저 계산된 쪽을 쓰고, 얼마나 어긋나는지 숫자로 보고한다.
                nd = sum(1 for y in range(8) for x in range(8)
                         if _px(want[ad], y, x) != _px(b, y, x))
                if nd > a.max_shared_diff:
                    raise SystemExit(
                        '공유 타일 0x%06X 이 %d픽셀 어긋난다 (열%d 줄%d). 배치를 고쳐라'
                        % (ad, nd, col, row))
                clash.append((ad, col, row, nd))
                continue
            want[ad] = b
    for ad, b in want.items():
        rom[ad:ad + 16] = b
    for ad, col, row, nd in clash:
        print('  공유 타일 0x%06X: 열%d 줄%d 이 %d픽셀 양보 (글자가 덮는 자리)' % (ad, col, row, nd))

    with open(a.out, 'wb') as f:
        f.write(bytes(rom))
    print('머리글 타일 %d장(고유 주소) -> %s' % (len(want), a.out))

    if a.preview:
        PAL = np.array([(255, 140, 0), (20, 20, 20), (250, 210, 40), (40, 60, 200)], np.uint8)
        Image.fromarray(PAL[A]).resize((A.shape[1] * 5, A.shape[0] * 5), Image.NEAREST).save(a.preview)

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
