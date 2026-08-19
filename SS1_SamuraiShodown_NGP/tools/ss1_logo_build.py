#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ss1_logo_build.py — SS1 타이틀 로고 한글판 빌드
전체 캔버스 160×88 = 블록A(y0~48, x0~160) + 블록B(y48~88, x16~152)
「사무라이 쇼다운!」 2단 배치 + 원본의 칼·느낌표·팻말 틀 보존"""
import sys
sys.path.insert(0, '/root/ss2_work')
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import ss1_logo as L, ss1_logo_ko as K

S = 8                                   # 작업 배율
CW, CH = 160, 88
SERIF = '/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc'
GALMURI = '/root/ss2_work/galmuri_repo/dist/Galmuri11.ttf'


def orig_full():
    rom = bytearray(open(L.ROM, 'rb').read())
    a = np.array(L.extract(rom, L.A)); b = np.array(L.extract(rom, L.B))
    f = np.full((CH, CW), 3, dtype=np.uint8); f[0:48] = a; f[48:88, 16:152] = b
    return f


def shift(m, dy, dx):
    o = np.zeros_like(m)
    o[max(0, dy):m.shape[0] + min(0, dy), max(0, dx):m.shape[1] + min(0, dx)] = \
        m[max(0, -dy):m.shape[0] + min(0, -dy), max(0, -dx):m.shape[1] + min(0, -dx)]
    return o


def brush(m, spread=4, press=3):
    o = K.dil(m, spread)
    for k in range(1, press + 1): o |= shift(K.dil(m, spread), k * 2, k)
    return o


def line_mask(items, rot=3, arc=0.10):
    c = Image.new('L', (CW * S, CH * S), 0); n = len(items)
    for i, (ch, x, y, w, h) in enumerate(items):
        g = K.glyph(ch, 240, SERIF).resize((int(w * S), int(h * S)), Image.LANCZOS)
        if rot: g = g.rotate(rot * (1 if i % 2 == 0 else -0.7), expand=True, resample=Image.BICUBIC)
        t = (i / max(1, n - 1)) * 2 - 1
        dy = int(arc * (t * t - 0.3) * h * S)
        c.paste(g, (int(x * S), int(y * S) + dy - (g.height - int(h * S)) // 2), g)
    return np.array(c) > 110


def one_line(items, rot=3, arc=0.10, spread=5, press=3, thr=118):
    b = brush(line_mask(items, rot, arc), spread, press)
    m = np.array(Image.fromarray((b * 255).astype(np.uint8)).resize((CW, CH), Image.LANCZOS)) > thr
    m[:, 112:] = False; m[62:, :] = False
    return m


def title_lines():
    """2단 배치: 사무라이(위) / 쇼다운(아래) — 줄마다 따로 음영"""
    l1 = [(ch, 15 + i * 24.5, 5, 24, 27) for i, ch in enumerate('사무라이')]
    l2 = [(ch, 34 + i * 26.5, 31, 26, 28) for i, ch in enumerate('쇼다운')]
    return one_line(l1, rot=3, arc=0.10), one_line(l2, rot=-3, arc=0.14)


def shade_lines(lines, outline=1):
    img = np.full((CH, CW), 3, dtype=np.uint8)
    allc = np.zeros((CH, CW), bool)
    for c in lines: allc |= c
    img[K.dil(allc, outline)] = 0
    yy = np.arange(CH)[:, None] * np.ones((1, CW))
    for c in lines:
        ys = np.where(c.any(axis=1))[0]
        cut = ys[0] + (ys[-1] - ys[0]) * 0.40
        img[c & (yy <= cut)] = 1
        img[c & (yy > cut)] = 2
    return img


def plaque(img, orig, text='포켓 격투 시리즈'):
    """팻말 틀은 원본 유지, 안쪽 글자만 한글로"""
    img[62:88, :] = orig[62:88, :]               # 팻말 통째로 원본
    img[65:76, 30:122] = 0                       # 안쪽 흰 바탕으로 비움
    f = ImageFont.truetype(GALMURI, 11)
    im = Image.new('L', (200, 22), 0); d = ImageDraw.Draw(im)
    d.text((2, 2), text, font=f, fill=255)
    bb = im.getbbox(); im = im.crop(bb)
    tw = min(90, im.width); th = min(11, im.height)
    im = im.resize((tw, th), Image.NEAREST)
    a = np.array(im) > 110
    x0 = 30 + (92 - tw) // 2; y0 = 65 + (11 - th) // 2
    sub = img[y0:y0 + th, x0:x0 + tw]
    sub[a] = 3                                    # 흰 바탕 위 검은 글씨
    img[y0:y0 + th, x0:x0 + tw] = sub
    return img


def build():
    orig = orig_full()
    img = shade_lines(title_lines())
    keep = np.zeros((CH, CW), bool)
    X = np.arange(CW)[None, :]; Y = np.arange(CH)[:, None]
    keep |= (X >= 112) & (Y < 62)                 # 느낌표·오른쪽 칼
    keep |= (X < 16) & (Y < 62)                   # 왼쪽 칼날
    img[keep] = orig[keep]
    img = plaque(img, orig)
    return img, orig


if __name__ == '__main__':
    img, orig = build()
    L.save(img.tolist(), '/root/ss2_work/ss1/ko_full.png', scale=4)
    A = img[0:48, 0:160].tolist()
    B = img[48:88, 16:152].tolist()
    print('블록A %d/87   블록B %d/66' % (L.count(A, L.A), L.count(B, L.B)))


def load_json(path):
    """로고편집기(SS1_로고편집기.html)가 내보낸 JSON → 160×88 배열"""
    import json
    j = json.load(open(path, encoding='utf-8'))
    a = np.array(j['canvas'], dtype=np.uint8)
    assert a.shape == (CH, CW), '캔버스 크기가 %dx%d 가 아님: %s' % (CW, CH, a.shape)
    return a & 3


def inject(rom, img=None):
    """한글 로고를 롬에 기록 (타일 예산 초과분은 자동 압축).
    img 를 주면 그걸 쓰고, 없으면 스크립트가 만든 기본안을 쓴다."""
    if img is None:
        img, _ = build()
    for blk, sl in ((L.A, (slice(0, 48), slice(0, 160))), (L.B, (slice(48, 88), slice(16, 152)))):
        sub = img[sl[0], sl[1]].tolist()
        n0 = L.count(sub, blk)
        if n0 > blk['n']:
            sub, a, b = L.compress(sub, blk)
            print('  압축 %d → %d' % (a, b))
        tiles, mp = L.pack(sub, blk)
        size = L.write(rom, blk, tiles, mp)
        print('  타일 %d/%d, 맵 %dB' % (len(tiles), blk['n'], size))
    return rom
