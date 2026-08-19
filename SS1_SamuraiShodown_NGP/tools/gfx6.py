# -*- coding: utf-8 -*-
"""gfx6.py — 전투 HUD 히트 카운터 'HITS' 한글화

인계 문서는 전투 HUD 를 `0x0786BD` 등으로 적었으나 그 주소는 타일맵이 아니다.
실제 HUD 폰트 뱅크는 `0x015A00` 이고, 이렇게 배치돼 있다.

    0x0E~0x17 = 0~9        0x18~0x1D = A~F
    0x1E = "HI"            0x1F = "TS"      ← 두 글자가 한 타일에 들어 있다

즉 'HITS' 는 문자열이 아니라 **타일 두 장**이다. 그래서 문자열 치환이 아니라
타일 데이터를 직접 갈아야 한다. 16×8px 에 한글 두 음절이 들어간다.
"""
import sys; sys.path.insert(0,'/root/ss2_work'); sys.path.insert(0,'/home/claude')
import struct
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT_BANK = 0x015A00
SLOT      = (0x1E, 0x1F)
TEXT      = '히트'
GAL = '/root/ss2_work/galmuri_repo/dist/Galmuri7.ttf'


def word16(text):
    """두 음절을 16×8 한 덩어리로 그려 8×8 타일 두 장으로 자른다.
    음절을 따로 8×8 에 넣으면 Galmuri7 밖에 못 써서 획이 깨진다.
    16px 를 통으로 쓰면 Galmuri9 가 들어가 훨씬 낫다."""
    import banner
    best = None
    for font, size in (('Galmuri9.ttf', 9), ('Galmuri7.ttf', 7)):
        for gap in (1, 0):
            m = banner._line(text, font, size, gap=gap)
            if m.shape[0] <= 8 and m.shape[1] <= 16:
                best = m; break
        if best is not None: break
    if best is None:
        best = banner._line(text, 'Galmuri7.ttf', 7, gap=0)[:8, :16]
    out = np.zeros((8, 16), bool)
    h, w = best.shape
    y = (8 - h) // 2
    x = (16 - w) // 2
    out[y:y + h, x:x + w] = best
    return out[:, :8], out[:, 8:]


def write_tile(rom, idx, bm, ink=3, bg=1):
    """원본 타일은 바탕이 값1(밝은회색), 글자가 값3(검정)이다. 바탕을 0으로 쓰면
    HUD 에 흰 사각형이 생긴다."""
    a = FONT_BANK + idx * 16
    for r in range(8):
        w = 0
        for k in range(8):
            w |= (ink if bm[r][k] else bg) << (14 - 2 * k)
        struct.pack_into('<H', rom, a + r * 2, w)


def patch(rom, report=True):
    left, right = word16(TEXT)
    write_tile(rom, SLOT[0], left)
    write_tile(rom, SLOT[1], right)
    if report:
        print("  HUD 'HITS' → %s  (타일 %02X·%02X 직접 교체)" % (TEXT, *SLOT))
    return rom
