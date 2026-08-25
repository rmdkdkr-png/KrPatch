#!/usr/bin/env python3
"""bake_names_ko.py — SVC 캐릭터 이름판 18종을 한글로 굽는다.

    python3 bake_names_ko.py <입력.ngc> <출력.ngc> [--font Galmuri11-Bold.ttf] [--ips 출력.ips]
    python3 bake_names_ko.py <입력.ngc> --sheet 미리보기.png     # 롬 안 쓰고 도안만

## 포맷

이름판 = 연속 스트립. `[윗줄 W장][아랫줄 W장]`, 타일 8×8 2bpp 16B.
화면에는 타일맵 SCR1 행13~14 × 열5~14 에 뜬다.

## 색

**배경 = 색인 1, 글자 = 색인 2** 만 맞추면 된다.
팔레트는 게임이 입히므로 화면에는 원판 그대로 빨간 판에 흰 글자로 나온다 — 실기 확인 완료.
배색을 따로 맞출 필요가 없다.

## 주소와 폭

타일마다 **번호를 점으로 심은 롬**을 만들어 화면에서 그 번호를 읽는 방법으로 확정했다.
윗줄 첫 칸의 번호가 스트립 시작이고, 아랫줄 첫 칸 번호에서 빼면 폭이 나온다.
근거는 `docs/SVC_이름판.md`.

**인접 스트립은 경계 타일 한 장을 공유하는 경우가 있다.** 앞 스트립의 마지막 칸과
다음 스트립의 첫 칸이 같은 주소인 자리가 여럿 있다(둘 다 빈 판이라 문제가 없다).
그래서 "앞 끝 = 다음 시작" 으로 체인을 계산하면 폭이 0.5칸씩 어긋난 것처럼 보인다.
글자를 가운데 정렬해 가장자리 칸을 배경으로만 두면 공유 칸을 덮어도 안전하다.
"""
import sys, os, argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BG, INK = 1, 2
PPEM = 16          # Galmuri11-Bold 를 ppem 16 으로 — 잉크 약 14~15px, 16px 줄에 들어간다

# (원문, 시작주소, 폭, 한글)
NAMES = [
    ('KYO',      0x32AB30, 6,  '쿄'),
    ('TERRY',    0x32ABF0, 9,  '테리'),
    ('RYO',      0x32AD10, 5,  '료'),
    ('MAI',      0x32ADB0, 6,  '마이'),
    ('LEONA',    0x32AE60, 9,  '레오나'),
    ('ATHENA',   0x32AF80, 9,  '아테나'),
    ('IORI',     0x32B0A0, 6,  '이오리'),
    ('HAOHMARU', 0x32B150, 10, '하오마루'),
    ('NAKORURU', 0x32B290, 10, '나코루루'),
    ('RYU',      0x32B3C0, 6,  '류'),
    ('CHUN-LI',  0x32B480, 9,  '춘리'),
    ('ZANGIEF',  0x32B5A0, 9,  '장기에프'),
    ('KEN',      0x32B6C0, 6,  '켄'),
    ('DAN',      0x32B780, 6,  '단'),
    ('SAKURA',   0x32B830, 9,  '사쿠라'),
    ('MORRIGAN', 0x32B950, 10, '모리건'),
    ('FELICIA',  0x32BA90, 8,  '펠리시아'),
    ('GUILE',    0x32BB90, 8,  '가일'),
]


def glyph(ch, font, ppem=PPEM):
    f = ImageFont.truetype(font, ppem)
    im = Image.new('L', (48, 48), 0)
    ImageDraw.Draw(im).text((6, 6), ch, font=f, fill=255)
    a = np.array(im) > 127
    ys, xs = np.nonzero(a)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def plate_art(text, font, W, h=16, gap=1):
    """W*8 × 16 도안. 배경은 전부 색인 1, 글자만 색인 2."""
    w = W * 8
    gs = [glyph(c, font) for c in text]
    total = sum(g.shape[1] for g in gs) + gap * (len(gs) - 1)
    ppem = PPEM
    while total > w - 2 and ppem > 9:          # 안 들어가면 한 단계씩 줄인다
        ppem -= 1
        gs = [glyph(c, font, ppem) for c in text]
        total = sum(g.shape[1] for g in gs) + gap * (len(gs) - 1)
    if total > w - 2:
        raise SystemExit('%s 가 %dpx 에 안 들어간다 (%dpx 필요)' % (text, w - 2, total))
    gh = max(g.shape[0] for g in gs)
    out = np.full((h, w), BG, np.uint8)
    x = (w - total) // 2
    y = (h - gh) // 2
    for g in gs:
        sub = out[y:y + g.shape[0], x:x + g.shape[1]]
        sub[g] = INK
        x += g.shape[1] + gap
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
    ap = argparse.ArgumentParser(description='SVC 이름판 한글 굽기')
    ap.add_argument('rom')
    ap.add_argument('out', nargs='?', default=None)
    ap.add_argument('--font', default='Galmuri11-Bold.ttf')
    ap.add_argument('--ips', default=None)
    ap.add_argument('--sheet', default=None, help='도안 미리보기 PNG')
    a = ap.parse_args(argv)

    with open(a.rom, 'rb') as f:
        orig = f.read()
    rom = bytearray(orig)

    arts = []
    for en, start, W, ko in NAMES:
        A = plate_art(ko, a.font, W)
        arts.append((en, ko, start, W, A))
        for i in range(W):
            rom[start + i * 16:start + i * 16 + 16] = pack(A[0:8, i * 8:i * 8 + 8])
            b = start + (W + i) * 16
            rom[b:b + 16] = pack(A[8:16, i * 8:i * 8 + 8])

    if a.sheet:
        PAL = np.array([(0, 0, 0), (200, 30, 40), (255, 255, 255), (90, 90, 90)], np.uint8)
        cell = 10 * 8 * 4
        cv = Image.new('RGB', (cell + 200, (16 * 4 + 8) * len(arts)), (25, 25, 25))
        d = ImageDraw.Draw(cv)
        for i, (en, ko, start, W, A) in enumerate(arts):
            cv.paste(Image.fromarray(PAL[A]).resize((A.shape[1] * 4, 64), Image.NEAREST),
                     (200, i * 72 + 4))
            d.text((4, i * 72 + 26), '%-9s %06X W%-2d %s' % (en, start, W, ko),
                   fill=(255, 210, 120))
        cv.save(a.sheet)
        print('도안 -> %s' % a.sheet)

    if a.out:
        with open(a.out, 'wb') as f:
            f.write(bytes(rom))
        print('이름판 %d종 구움 -> %s' % (len(NAMES), a.out))
    if a.ips and a.out:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        '..', '..', 'SS1_SamuraiShodown_NGP', 'tools'))
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
