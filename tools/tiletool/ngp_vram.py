#!/usr/bin/env python3
"""ngp_vram.py — NGPC VRAM 해석 + 화면 재현(시뮬레이터) 코어.

VRAM 배치(실측):
  0x8000-0x80FF  레지스터 (0x8032/33 = SCR1 X/Y, 0x8034/35 = SCR2 X/Y)
  0x8200-0x82FF  스프라이트 팔레트
  0x8300-0x83FF  스크롤 팔레트  (팔레트 p = 0x8300 + p*8, 색 4개 × u16 RGB444)
  0x8800-0x8FFF  스프라이트 테이블
  0x9000-0x97FF  SCR1 타일맵 (32×32 × u16)
  0x9800-0x9FFF  SCR2 타일맵 (32×32 × u16)
  0xA000-0xBFFF  타일 패턴 512장 × 16B (2bpp, 행당 u16, 픽셀당 2비트, 상위비트부터)

타일맵 u16 비트필드는 fit_format()으로 실측 프레임버퍼와 맞춰 확정한다.
"""
import struct
import numpy as np

VRAM_BASE = 0x8000
SCR = {1: 0x9000, 2: 0x9800}
PAL_SCROLL = 0x8300
TILE_BASE  = 0xA000
MAPW = MAPH = 32

def rgb444(v):
    r = (v >> 8) & 0xF; g = (v >> 4) & 0xF; b = v & 0xF
    return (r * 17, g * 17, b * 17)

def palettes(vram, base=PAL_SCROLL, n=16):
    out = []
    for p in range(n):
        o = base - VRAM_BASE + p * 8
        out.append([rgb444(struct.unpack_from('<H', vram, o + i * 2)[0]) for i in range(4)])
    return out

def tile_pixels(vram, idx):
    """패턴 idx -> 8x8 색인(0..3) 배열."""
    o = TILE_BASE - VRAM_BASE + idx * 16
    a = np.zeros((8, 8), np.uint8)
    for r in range(8):
        w = vram[o + r * 2] | (vram[o + r * 2 + 1] << 8)
        for c in range(8):
            a[r, c] = (w >> (14 - 2 * c)) & 3
    return a

def tile_bytes(vram, idx):
    o = TILE_BASE - VRAM_BASE + idx * 16
    return bytes(vram[o:o + 16])

def decode_entry(v, fmt):
    pat = v & fmt['pat_mask']
    pal = (v >> fmt['pal_shift']) & fmt['pal_mask']
    hf  = bool(v >> fmt['h_bit'] & 1) if fmt['h_bit'] is not None else False
    vf  = bool(v >> fmt['v_bit'] & 1) if fmt['v_bit'] is not None else False
    return pat, pal, hf, vf

FORMATS = [
    dict(name='pat9/pal9-12/h15/v14', pat_mask=0x1FF, pal_shift=9,  pal_mask=0xF, h_bit=15, v_bit=14),
    dict(name='pat9/pal13-15/h9/v10', pat_mask=0x1FF, pal_shift=13, pal_mask=0x7, h_bit=9,  v_bit=10),
    dict(name='pat9/pal11-14/h15/v10',pat_mask=0x1FF, pal_shift=11, pal_mask=0xF, h_bit=15, v_bit=10),
    dict(name='pat9/pal9-12/h13/v14', pat_mask=0x1FF, pal_shift=9,  pal_mask=0xF, h_bit=13, v_bit=14),
]

def render_plane(vram, plane, fmt, pals):
    """스크롤 무시, 32x32 타일맵을 통째로 렌더 (256x256 RGB + 알파)."""
    base = SCR[plane] - VRAM_BASE
    img = np.zeros((MAPH * 8, MAPW * 8, 3), np.uint8)
    alpha = np.zeros((MAPH * 8, MAPW * 8), bool)
    cache = {}
    for r in range(MAPH):
        for c in range(MAPW):
            v = struct.unpack_from('<H', vram, base + (r * MAPW + c) * 2)[0]
            pat, pal, hf, vf = decode_entry(v, fmt)
            if pat not in cache: cache[pat] = tile_pixels(vram, pat)
            t = cache[pat]
            if hf: t = t[:, ::-1]
            if vf: t = t[::-1, :]
            P = pals[pal % len(pals)]
            for y in range(8):
                for x in range(8):
                    ci = t[y, x]
                    img[r * 8 + y, c * 8 + x] = P[ci]
                    alpha[r * 8 + y, c * 8 + x] = ci != 0
    return img, alpha

def compose(vram, fmt, pals, sx1, sy1, sx2, sy2, w=160, h=152):
    """스크롤 적용해 실제 화면 재구성."""
    p1, a1 = render_plane(vram, 1, fmt, pals)
    p2, a2 = render_plane(vram, 2, fmt, pals)
    out = np.zeros((h, w, 3), np.uint8)
    bg = pals[0][0]
    out[:, :] = bg
    for (p, a, sx, sy) in ((p1, a1, sx1, sy1), (p2, a2, sx2, sy2)):
        ys = (np.arange(h) + sy) % 256
        xs = (np.arange(w) + sx) % 256
        sub = p[np.ix_(ys, xs)]
        sa = a[np.ix_(ys, xs)]
        out[sa] = sub[sa]
    return out

def fb_rgb(frame):
    """RGB565 프레임버퍼 -> RGB888"""
    f = frame.astype(np.uint32)
    r = ((f >> 11) & 0x1F) * 255 // 31
    g = ((f >> 5) & 0x3F) * 255 // 63
    b = (f & 0x1F) * 255 // 31
    return np.dstack([r, g, b]).astype(np.uint8)

def fit_format(vram, frame):
    """포맷·스크롤 조합을 실측 프레임과 맞춰 최적안을 고른다."""
    ref = fb_rgb(frame)
    h, w = ref.shape[:2]
    regs = {a: vram[a - VRAM_BASE] for a in (0x8032, 0x8033, 0x8034, 0x8035)}
    cands = [(regs[0x8032], regs[0x8033], regs[0x8034], regs[0x8035]),
             (regs[0x8034], regs[0x8035], regs[0x8032], regs[0x8033]),
             (0, 0, 0, 0)]
    best = None
    for fmt in FORMATS:
        pals = palettes(vram)
        for sx1, sy1, sx2, sy2 in cands:
            got = compose(vram, fmt, pals, sx1, sy1, sx2, sy2, w, h)
            score = float((np.abs(got.astype(int) - ref.astype(int)).sum(2) < 24).mean())
            if best is None or score > best[0]:
                best = (score, fmt, (sx1, sy1, sx2, sy2))
    return best
