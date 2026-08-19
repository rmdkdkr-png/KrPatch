#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ss1_logo.py — SS1 타이틀 로고 추출/주입

로고는 SCR2에 두 덩이로 그려진다.
  A 본로고  타일 87개 @ 0x08AEA0 (16B×87) + 맵 @ 0x08B410 (20칸×6행)
  B 부제팻말 타일 66개 @ 0x08B490 (16B×66) + 맵 @ 0x08B8B0 (17칸×5행)
맵 형식: [행수][셀…][0xFF]…   셀 바이트 = 타일번호*2 + (1이면 좌우반전)
타일 형식: 2bpp 8×8, 행마다 u16 리틀엔디안, 픽셀 = (w >> (14-2k)) & 3
"""
import sys, struct
from PIL import Image

ROM = '/root/ss2_work/ss1/Samurai Shodown! (JUE) [M][!].ngp'
A = dict(tile=0x08AEA0, n=87, map=0x08B410, w=20, h=6)
B = dict(tile=0x08B490, n=66, map=0x08B8B0, w=17, h=5)
GRAY = [255, 170, 85, 0]          # 값0=흰 … 값3=검정


def read_map(rom, d):
    a = d['map']; rows = rom[a]; a += 1
    out = []
    for _ in range(rows):
        r = []
        while rom[a] != 0xFF:
            r.append((rom[a] >> 1, rom[a] & 1)); a += 1
        a += 1
        out.append(r)
    return out, a - d['map']


def tile_px(rom, base, i):
    a = base + i * 16
    return [[(struct.unpack_from('<H', rom, a + r * 2)[0] >> (14 - 2 * k)) & 3
             for k in range(8)] for r in range(8)]


def extract(rom, d):
    mp, _ = read_map(rom, d)
    img = [[0] * (d['w'] * 8) for _ in range(d['h'] * 8)]
    for y, row in enumerate(mp):
        for x, (n, hf) in enumerate(row):
            t = tile_px(rom, d['tile'], n)
            for r in range(8):
                for k in range(8):
                    img[y * 8 + r][x * 8 + k] = t[r][7 - k if hf else k]
    return img


def save(img, path, scale=4):
    h, w = len(img), len(img[0])
    im = Image.new('L', (w, h)); px = im.load()
    for y in range(h):
        for x in range(w): px[x, y] = GRAY[img[y][x]]
    im.resize((w * scale, h * scale), Image.NEAREST).save(path)
    return im


def load_img(path, w, h):
    """PNG → 값0~3 배열 (가장 가까운 회색 4단계로 양자화)"""
    im = Image.open(path).convert('L').resize((w, h), Image.NEAREST)
    px = im.load()
    return [[min(range(4), key=lambda v: abs(GRAY[v] - px[x, y])) for x in range(w)]
            for y in range(h)]


def pack(img, d, allow_flip=True):
    """이미지 → (타일목록, 맵). 예산 초과면 예외"""
    tiles = []; index = {}; mp = []
    def cell(x, y):
        return tuple(tuple(img[y * 8 + r][x * 8 + k] for k in range(8)) for r in range(8))
    def flip(t): return tuple(tuple(reversed(r)) for r in t)
    for y in range(d['h']):
        row = []
        for x in range(d['w']):
            c = cell(x, y)
            if c in index: row.append((index[c], 0)); continue
            f = flip(c)
            if allow_flip and f in index: row.append((index[f], 1)); continue
            if len(tiles) >= d['n']:
                raise RuntimeError('타일 예산 초과: %d칸 필요 / %d칸 가능' % (len(tiles) + 1, d['n']))
            index[c] = len(tiles); row.append((len(tiles), 0)); tiles.append(c)
        mp.append(row)
    return tiles, mp


def write(rom, d, tiles, mp):
    for i, t in enumerate(tiles):
        a = d['tile'] + i * 16
        for r in range(8):
            w = 0
            for k in range(8): w |= t[r][k] << (14 - 2 * k)
            struct.pack_into('<H', rom, a + r * 2, w)
    for i in range(len(tiles), d['n']):        # 남는 칸은 빈 타일로
        rom[d['tile'] + i * 16: d['tile'] + i * 16 + 16] = b'\x00' * 16
    a = d['map']; rom[a] = len(mp); a += 1
    for row in mp:
        for n, hf in row: rom[a] = (n << 1) | hf; a += 1
        rom[a] = 0xFF; a += 1
    return a - d['map']


def count(img, d, allow_flip=True):
    """예산 무시하고 실제 필요한 고유 타일 수만 센다"""
    idx = set()
    for y in range(d['h']):
        for x in range(d['w']):
            c = tuple(tuple(img[y * 8 + r][x * 8 + k] for k in range(8)) for r in range(8))
            f = tuple(tuple(reversed(r)) for r in c)
            key = min(c, f) if allow_flip else c
            idx.add(key)
    return len(idx)


def compress(img, d, allow_flip=True):
    """고유 타일이 예산을 넘으면 가장 닮은 타일끼리 병합해 예산 안으로 줄인다.
    반환: (줄인 이미지, 원래 고유수, 최종 고유수)"""
    H, W = d['h'], d['w']
    def cell(x, y):
        return tuple(tuple(img[y * 8 + r][x * 8 + k] for k in range(8)) for r in range(8))
    def flip(t): return tuple(tuple(reversed(r)) for r in t)
    grid = [[cell(x, y) for x in range(W)] for y in range(H)]
    def keyset():
        ks = {}
        for y in range(H):
            for x in range(W):
                c = grid[y][x]; f = flip(c)
                k = min(c, f) if allow_flip else c
                ks.setdefault(k, []).append((x, y))
        return ks
    ks = keyset(); start = len(ks)
    def dist(a, b):
        return sum((a[r][k] - b[r][k]) ** 2 for r in range(8) for k in range(8))
    while len(ks) > d['n']:
        keys = list(ks)
        # 사용 빈도가 낮은 타일을 우선 흡수 대상으로
        keys.sort(key=lambda k: len(ks[k]))
        best = None
        for i, a in enumerate(keys[:max(8, len(keys) // 3)]):
            for b in keys:
                if a is b: continue
                dd = dist(a, b)
                if best is None or dd < best[0]: best = (dd, a, b)
        _, a, b = best
        for (x, y) in ks[a]:
            c = grid[y][x]
            grid[y][x] = b if (min(c, flip(c)) if allow_flip else c) == a and c == a else flip(b)
        ks = keyset()
    out = [[0] * (W * 8) for _ in range(H * 8)]
    for y in range(H):
        for x in range(W):
            t = grid[y][x]
            for r in range(8):
                for k in range(8): out[y * 8 + r][x * 8 + k] = t[r][k]
    return out, start, len(ks)


def cost(img, d):
    return count(img, d)


if __name__ == '__main__':
    rom = bytearray(open(ROM, 'rb').read())
    if sys.argv[1] == 'extract':
        for name, d in (('A_본로고', A), ('B_부제팻말', B)):
            img = extract(rom, d)
            save(img, '/root/ss2_work/ss1/logo_%s.png' % name)
            mp, size = read_map(rom, d)
            used = len({n for r in mp for n, _ in r})
            print('%s  %dx%d칸  타일 %d/%d 사용  맵 %dB  → logo_%s.png'
                  % (name, d['w'], d['h'], used, d['n'], size, name))
