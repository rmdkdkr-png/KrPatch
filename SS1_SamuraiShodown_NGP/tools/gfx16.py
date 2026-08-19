#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gfx16.py — 전투 HUD 체력바 아래 검질 라벨 修羅/羅刹 → 수라/나찰

실측:
    라벨은 16×8 (타일 2장 연속 32B). 양쪽 플레이어가 같은 타일을 공유.
    修羅  롬 0x7852E   (검질 「수라」 선택 시)
    羅刹  롬 0x78553   (검질 「나찰」 선택 시)
    앞의 5바이트 (01 00 02 FF 02) 는 미니 맵 헤더 — 건드리지 않는다.
    픽셀: 3=검정 바탕, 1=흰 획 (2 는 안티앨리어스 소량)
"""
import struct, sys
sys.path.insert(0, '/root/ss2_work')

LABELS = [(0x7852E, '수라'), (0x78553, '나찰')]
GAL7 = '/root/ss2_work/galmuri_repo/dist/Galmuri7.bdf'


def _glyph(ch):
    from bdf_render import parse_bdf, glyph_pixels
    if _glyph.g is None:
        _glyph.g = parse_bdf(GAL7)[1]
    return glyph_pixels(_glyph.g[ord(ch)])
_glyph.g = None


def patch(rom, report=True):
    for base, text in LABELS:
        img = [[3]*16 for _ in range(8)]          # 검정 바탕
        for i, ch in enumerate(text):
            pts, (w, h, xo, yo) = _glyph(ch)
            x0 = i*8 + (8-w)//2
            y0 = (8-h)//2
            for (px, py) in pts:
                x, y = x0+px, y0+py
                if 0 <= x < 16 and 0 <= y < 8: img[y][x] = 1
        for t in range(2):
            for r in range(8):
                w = 0
                for k in range(8): w |= img[r][t*8+k] << (14-2*k)
                struct.pack_into('<H', rom, base + t*16 + r*2, w)
    if report:
        print('  검질 라벨: 修羅→수라 (0x7852E) / 羅刹→나찰 (0x78553)')
    return rom


if __name__ == '__main__':
    rom = bytearray(open('/root/ss2_work/ss1/Samurai Shodown! (JUE) [M][!].ngp', 'rb').read())
    patch(rom)
    open('/tmp/gfx16_test.ngp', 'wb').write(rom)
