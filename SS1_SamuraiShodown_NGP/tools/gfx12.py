# -*- coding: utf-8 -*-
"""gfx12.py — 라운드 시작 콜 「いざ尋常に」/「FAIR & SQUARE」 한글화  [J 항목]

정체 (이 세션 실측):
  행마다 별도의 10×1 그림 타일맵 레코드 4개가 세로로 쌓인 80×32 그래픽.
  전수조사에서 '미확인 10×1' 로 넘겼던 바로 그 주소들이다.
    JP いざ尋常に   073051 / 0730FE / 0731AB / 073238   (행 예산 6/10/10/8)
    EN FAIR&SQUARE  075C21 / 075CAE / 075D5B / 075E08   (행 예산 8/8/10/10)
  글자가 대각선으로 흘러가는 배치는 런타임이 아니라 **그래픽에 이미 구워져** 있다.
  스프라이트로 그려져 8px 정렬이 안 맞아 과거 화면↔롬 타일 대조가 실패했었다.
  잉크 규약은 HUD 이름판과 동일: 몸통=1, 외곽선=3, 투명=0.
"""
import sys
sys.path.insert(0, '/root/ss2_work'); sys.path.insert(0, '/home/claude')
import numpy as np
import ss1_gfxtext as X, ss1_logo as L
from gfx7 import _mask

JP_ROWS = [0x073051, 0x0730FE, 0x0731AB, 0x073238]
EN_ROWS = [0x075C21, 0x075CAE, 0x075D5B, 0x075E08]
TEXT = '정정당당히'


def compose(text=TEXT, W=80, H=32, px=11, step_x=13, step_y=4, x0=2, y0=3):
    """대각선 배치 80×32 캔버스. 반환 uint8 (0/1/3)"""
    ink = np.zeros((H, W), bool)
    for k, ch in enumerate(text):
        m, (xo, yo) = _mask(ch, px)
        x, y = x0 + k * step_x, y0 + k * step_y
        h, w = m.shape
        y1, x1 = min(H, y + h), min(W, x + w)
        if y1 > y and x1 > x:
            ink[y:y1, x:x1] |= m[:y1 - y, :x1 - x]
    out = np.zeros((H, W), np.uint8)
    o = np.zeros_like(ink)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            o |= np.roll(np.roll(ink, dy, 0), dx, 1)
    out[o & ~ink] = 3          # 외곽선
    out[ink] = 1               # 몸통
    return out


def row_budgets(rom, rows):
    return [X.spec(rom, m)['n'] for m in rows]


def fit(rom, rows, text=TEXT):
    """행별 예산에 들어가는 배치를 찾는다 (x0/y0/px 미세조정)."""
    budgets = row_budgets(rom, rows)
    for px, step in ((11, 13), (14, 14), (9, 11)):
        for x0 in (2, 1, 0, 3, 4):
            for y0 in (3, 2, 1, 0):
                img = compose(text, px=px, x0=x0, y0=y0,
                              step_x=step, step_y=4)
                ok = True
                for r in range(4):
                    sub = img[r*8:(r+1)*8].tolist()
                    n = len({tuple(map(tuple, [ [sub[y][xx*8+k] for k in range(8)] for y in range(8)])) or ()
                             for xx in range(10)}) if False else None
                    # 고유 타일 수 (좌우반전 동일시)
                    s = set()
                    for cx in range(10):
                        t = tuple(tuple(sub[y][cx*8+k] for k in range(8)) for y in range(8))
                        s.add(min(t, tuple(tuple(reversed(rr)) for rr in t)))
                    if len(s) > budgets[r]:
                        ok = False; break
                if ok:
                    return img, 'px=%d x0=%d y0=%d' % (px, x0, y0)
    return None, '실패'


def patch(rom, report=True):
    for name, rows in (('いざ尋常に', JP_ROWS), ('FAIR & SQUARE', EN_ROWS)):
        img, how = fit(rom, rows)
        assert img is not None, name + ' 예산 내 배치 실패'
        for r, m in enumerate(rows):
            d = X.spec(rom, m)
            n = X.inject(rom, d, img[r*8:(r+1)*8].tolist())
            if report and r == 0:
                print('  %-14s → %s  (%s)' % (name, TEXT, how))
    return rom
