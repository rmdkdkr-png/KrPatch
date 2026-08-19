#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ss1_gfxtext.py — 그림으로 박힌 화면 텍스트(한자·가타카나) 추출/교체

이 게임의 텍스트 그래픽은 전부 같은 구조다.
    [타일 데이터 n×16B][맵]
    맵 = [행수 1B] { 셀바이트 … 0xFF } × 행수
    셀바이트 = 타일번호×2 + (1이면 좌우반전)
맵 주소만 주면 행·열과 타일 수가 결정되고, 타일 블록은 맵 바로 앞이다.
"""
import sys, struct
sys.path.insert(0, '/root/ss2_work')
from PIL import Image
import ss1_logo as L

ROM = L.ROM
GRAY = L.GRAY


def read_map(rom, map_addr):
    a = map_addr; rows = rom[a]; a += 1
    mp = []
    for _ in range(rows):
        r = []
        while rom[a] != 0xFF:
            r.append((rom[a] >> 1, rom[a] & 1)); a += 1
        a += 1
        mp.append(r)
    return mp, a - map_addr


def spec(rom, map_addr, name=''):
    mp, size = read_map(rom, map_addr)
    n = max(t for r in mp for t, _ in r) + 1
    w = max(len(r) for r in mp); h = len(mp)
    return dict(name=name, map=map_addr, tile=map_addr - n * 16, n=n,
                w=w, h=h, mapsize=size, grid=mp)


def extract(rom, d):
    img = [[0] * (d['w'] * 8) for _ in range(d['h'] * 8)]
    for y, row in enumerate(d['grid']):
        for x, (n, hf) in enumerate(row):
            t = L.tile_px(rom, d['tile'], n)
            for r in range(8):
                for k in range(8):
                    img[y * 8 + r][x * 8 + k] = t[r][7 - k if hf else k]
    return img


def inject(rom, d, img):
    n0 = L.count(img, d)
    if n0 > d['n']:
        img, a, b = L.compress(img, d)
        print('    압축 %d → %d' % (a, b))
    tiles, mp = L.pack(img, d)
    size = L.write(rom, d, tiles, mp)
    assert size == d['mapsize'], '맵 크기 변동 %d→%d' % (d['mapsize'], size)
    return len(tiles)


ITEMS = [
    # ── 화면 UI (일본어판) ──
    (0x06A90B, '검질선택'), (0x06A99F, '수라'), (0x06AA2B, '나찰'), (0x06B8D5, '난이도'),
    (0x06B9A5, ['검성', '상급자용']), (0x06BA76, ['검호', '중급자용']), (0x06BB47, ['검객', '초급자용']),
    # ── 화면 UI (영어판) ──
    (0x06B6F1, '검질선택'), (0x06B785, '수라'), (0x06B811, '나찰'), (0x06BBF0, '난이도'),
    (0x06BC80, '상급'), (0x06BD0C, '중급'), (0x06BD98, '초급'),
    # ── 캐릭터 이름 (일본어판) — 표기는 SS2 한글패치와 통일(이름만) ──
    (0x069BF3, '시키'), (0x069CB7, '갈포드'), (0x069D9B, '리무루루'), (0x069E7F, '나코루루'),
    (0x069F63, '하오마루'), (0x06A047, '한조'), (0x06A15B, '쥬베이'),
    (0x06A23F, '우쿄'), (0x06A323, '시즈마루'), (0x06A437, '겐쥬로'),
    (0x06A54B, '아마쿠사'), (0x06A62F, '소게츠'), (0x06A713, '카즈키'),
    (0x06A827, '잔쿠로'),
    # ── 캐릭터 이름 (영어판) ──
    (0x06AAE9, '시키'), (0x06ABCD, '갈포드'), (0x06ACB1, '리무루루'), (0x06ADB5, '나코루루'),
    (0x06AEC9, '하오마루'), (0x06AF8D, '한조'), (0x06B051, '쥬베이'),
    (0x06B125, '우쿄'), (0x06B209, '시즈마루'), (0x06B549, '카즈키'),
    (0x06B62D, '잔쿠로'),
]



if __name__ == '__main__':
    rom = bytearray(open(ROM, 'rb').read())
    for m, name in ITEMS:
        d = spec(rom, m, str(name))
        print('%-10s 맵 %06X  타일 %06X ×%-3d  %d×%d칸  맵%dB'
              % (str(name), d['map'], d['tile'], d['n'], d['w'], d['h'], d['mapsize']))
        L.save(extract(rom, d), '/root/ss2_work/ss1/gfx_%06X.png' % m, scale=4)


# ---------- 한글 렌더 ----------
from PIL import ImageFont, ImageDraw
import numpy as np
GAL14 = '/root/ss2_work/galmuri_repo/dist/Galmuri14.ttf'
GAL11B = '/root/ss2_work/galmuri_repo/dist/Galmuri11-Bold.ttf'


GAL11 = '/root/ss2_work/galmuri_repo/dist/Galmuri11.ttf'
GAL7  = '/root/ss2_work/galmuri_repo/dist/Galmuri7.ttf'


def _glyph(ch, font, size):
    im = Image.new('L', (size * 3, size * 3), 0)
    ImageDraw.Draw(im).text((size, size // 2), ch, font=ImageFont.truetype(font, size), fill=255)
    bb = im.getbbox()
    return im.crop(bb) if bb else Image.new('L', (1, 1), 0)


def _adv(text, font, size):
    f = ImageFont.truetype(font, size)
    im = Image.new('L', (10, 10)); d = ImageDraw.Draw(im)
    return sum(d.textlength(c, font=f) for c in text)


FONTS = ((GAL14, 14), (GAL11, 11), (GAL7, 7))


def ko_line(text, W, H, shadow=True):
    """폭 W 안에 들어가는 가장 큰 픽셀폰트를 골라 가운데 정렬. 확대/축소 없음.
    한 글자를 16px 칸(=타일 2칸)에 딱 맞춰 놓을 수 있으면 그렇게 한다.
    글자가 타일 경계에 정렬되면 고유 타일이 확 줄어 압축 손실이 없다."""
    t2 = text.replace(' ', '')
    if H >= 14 and len(t2) * 16 <= W:
        ink = np.zeros((H, W), bool)
        x0 = ((W - len(t2) * 16) // 2 // 8) * 8
        for i, ch in enumerate(t2):
            g = _glyph(ch, GAL14, 14)
            a = np.array(g) > 110
            xx = x0 + i * 16 + max(0, (16 - g.width) // 2)
            yy = max(0, (H - g.height) // 2)
            y1, x1 = min(H, yy + a.shape[0]), min(W, xx + a.shape[1])
            if y1 > yy and x1 > xx:
                ink[yy:y1, xx:x1] |= a[:y1 - yy, :x1 - xx]
        return ink

    font, size = FONTS[-1]
    for fp, sz in FONTS:
        if _adv(text, fp, sz) <= W and sz <= H:
            font, size = fp, sz; break
    cells = [_glyph(c, font, size) if c != ' ' else Image.new('L', (max(2, size // 2), 1), 0)
             for c in text]
    adv = int(_adv(text, font, size))
    x = max(0, (W - adv) // 2)
    ph = max(c.height for c in cells)
    y0 = max(0, (H - ph) // 2)
    ink = np.zeros((H, W), bool)
    f = ImageFont.truetype(font, size)
    dd = ImageDraw.Draw(Image.new('L', (10, 10)))
    for ch, c in zip(text, cells):
        w = int(dd.textlength(ch, font=f))
        if ch != ' ':
            a = np.array(c) > 110
            xx = x + max(0, (w - c.width) // 2)
            y1, x1 = min(H, y0 + a.shape[0]), min(W, xx + a.shape[1])
            if y1 > y0 and x1 > xx:
                ink[y0:y1, xx:x1] |= a[:y1 - y0, :x1 - xx]
        x += w
    return ink


def ko_image(lines, W, H, shadow=True):
    """lines: 문자열 하나 또는 여러 줄. 흰 바탕(0)/밝은회색(1)/우하 그림자(2)"""
    if isinstance(lines, str): lines = [lines]
    n = len(lines); bh = H // n
    ink = np.zeros((H, W), bool)
    for i, t in enumerate(lines):
        ink[i * bh:(i + 1) * bh] |= ko_line(t, W, bh, shadow)
    img = np.zeros((H, W), np.uint8)
    if shadow:
        sh = np.zeros_like(ink); sh[1:, 1:] = ink[:-1, :-1]
        img[sh & ~ink] = 2
    img[ink] = 1
    return img.tolist()


def patch(rom, report=True):
    for m, ko in ITEMS:
        d = spec(rom, m, str(ko))
        img = ko_image(ko, d['w'] * 8, d['h'] * 8)
        n = inject(rom, d, img)
        if report:
            print('  %-16s %d×%d칸  타일 %d/%d' % (ko if isinstance(ko, str) else '/'.join(ko),
                                                 d['w'], d['h'], n, d['n']))
    return rom
