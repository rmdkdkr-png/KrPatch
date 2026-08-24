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
색은 원판과 같게 — **1 = 검은 외곽선, 2 = 노란 채움** (3 은 파란 그림자로 안 쓴다).
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
PPEM = 16                                  # Galmuri11-Bold 를 ppem 16 으로 — 획이 굵어야 1px 외곽선에 안 먹힌다
LAYOUT = [('메', 1), ('인', 3), ('메', 7), ('뉴', 9)]   # (글자, 시작 열) — 아래 제약 참고


def glyph(ch, font):
    f = ImageFont.truetype(font, PPEM)
    im = Image.new('L', (40, 40), 0)
    ImageDraw.Draw(im).text((0, 0), ch, font=f, fill=255)
    return np.array(im) > 127


def art(font, ncol=NCOL, h=16):
    w = ncol * 8
    m = np.zeros((h, w), bool)
    for ch, col in LAYOUT:
        g = glyph(ch, font)
        ys, xs = np.nonzero(g)
        gh, gw = ys.max() - ys.min() + 1, xs.max() - xs.min() + 1
        sub = g[ys.min():ys.min() + gh, xs.min():xs.min() + gw]
        x0 = col * 8 + (16 - gw) // 2
        y0 = (h - gh) // 2
        m[y0:y0 + gh, x0:x0 + gw] |= sub
    out = np.zeros((h, w), np.uint8)
    d = np.zeros_like(m)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            d |= np.roll(np.roll(m, dy, 0), dx, 1)
    out[d & ~m] = LINE                       # 검은 외곽선
    out[m] = FILL                            # 노란 채움
    return out


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
    a = ap.parse_args(argv)

    with open(a.rom, 'rb') as f:
        orig = f.read()
    rom = bytearray(orig)
    A = art(a.font)

    # 공유 주소는 내용이 같아야 한다 — 어기면 화면이 깨지므로 먼저 검사한다
    want = {}
    for col in range(NCOL):
        for row, pat in ((0, 4 + 2 * col), (1, 5 + 2 * col)):
            tile = A[row * 8:row * 8 + 8, col * 8:col * 8 + 8]
            ad = BANK[pat]
            b = pack(tile)
            if ad in want and want[ad] != b:
                raise SystemExit(
                    '공유 타일 0x%06X 에 서로 다른 내용을 넣으려 한다 (열%d 줄%d). 배치를 고쳐라'
                    % (ad, col, row))
            want[ad] = b
    for ad, b in want.items():
        rom[ad:ad + 16] = b

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
