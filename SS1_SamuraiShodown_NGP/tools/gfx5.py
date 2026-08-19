# -*- coding: utf-8 -*-
"""gfx5.py — 영문 라운드 콜 BATTLE# 한글화

이 그래픽만 구조가 다르다. 'BATTLE' 글자 뒤의 '#' 는 라운드 숫자가 들어가는 자리다.
숫자를 어떻게 끼우는지(타일 데이터를 덮어쓰는지, 맵 셀을 갈아끼우는지)는 코드를 봐야
알 수 있으므로, **어느 쪽이든 깨지지 않도록** 다음 두 가지를 그대로 보존한다.

  · '#' 타일 9장의 **타일 번호** (11,12,13 / 24,25,26 / 37,38,39)
  · '#' 자리 맵 셀 (11~13열)

글자 부분만 「라운드」로 갈면 어순도 맞는다. BATTLE 1 → 라운드 1.
"""
import sys; sys.path.insert(0,'/root/ss2_work'); sys.path.insert(0,'/home/claude')
import numpy as np
import ss1_gfxtext as X, ss1_logo as L
import banner

ADDR = 0x077C13
HASH_COLS = (11, 12, 13)          # 숫자가 들어가는 열
TEXT = '라운드'


def patch(rom, report=True):
    d = X.spec(rom, ADDR)
    W, H = d['w'] * 8, d['h'] * 8
    orig = np.array(X.extract(rom, d), np.uint8)

    # 글자 영역(0~10열)만 새로 그린다. 원본 글자는 1~3행에 있다.
    tw = HASH_COLS[0] * 8
    img = orig.copy()
    img[:, :tw] = 0
    m = None
    for font, size, kmax in (('Galmuri14.ttf', 14, 3), ('Galmuri11-Bold.ttf', 11, 3),
                             ('Galmuri11.ttf', 11, 3), ('Galmuri9.ttf', 9, 2)):
        mm = banner._line(TEXT, font, size)
        for k in range(kmax, 0, -1):
            if mm.shape[0] * k <= 24 and mm.shape[1] * k <= tw - 4:
                m = np.kron(mm, np.ones((k, k), bool)); break
        if m is not None: break
    th, twd = m.shape
    y0 = 8 + (24 - th) // 2                      # 1~3행(=y 8~31) 안에서 가운데
    x0 = max(0, (tw - twd) // 2)
    for y in range(th):
        for x in range(twd):
            if m[y, x]: img[y0 + y, x0 + x] = 3   # 검정 — 흰 바탕에서 대비 확보

    # ── 타일 번호를 고정한 채로 다시 싼다 ──
    def cell(a, cx, cy):
        return tuple(tuple(int(a[cy*8+r][cx*8+k]) for k in range(8)) for r in range(8))
    def flip(t): return tuple(tuple(reversed(r)) for r in t)

    fixed = {}                                   # 타일번호 → 타일
    for cy in range(1, 4):
        for cx in HASH_COLS:
            fixed[d['grid'][cy][cx][0]] = cell(orig, cx, cy)
    blank = cell(orig, 0, 0)
    fixed[d['grid'][0][0][0]] = blank             # 0번 = 빈칸

    tiles = [blank] * d['n']
    for i, t in fixed.items(): tiles[i] = t
    used = set(fixed)
    free = [i for i in range(d['n']) if i not in used]

    index = {t: i for i, t in fixed.items()}
    mp = []
    for cy in range(d['h']):
        row = []
        for cx in range(d['w']):
            if cx in HASH_COLS and 1 <= cy <= 3:
                row.append(d['grid'][cy][cx]); continue     # 숫자 자리는 원본 그대로
            c = cell(img, cx, cy)
            if c in index: row.append((index[c], 0)); continue
            f = flip(c)
            if f in index: row.append((index[f], 1)); continue
            if not free:
                raise RuntimeError('타일 예산 초과')
            i = free.pop(0); tiles[i] = c; index[c] = i
            row.append((i, 0))
        mp.append(row)

    size = L.write(rom, d, tiles, mp)
    assert size == d['mapsize'], '맵 크기 변동 %d→%d' % (d['mapsize'], size)
    if report:
        print('  BATTLE#  → %s + 숫자자리 보존   타일 %d/%d' % (TEXT, d['n'] - len(free), d['n']))
    return rom
