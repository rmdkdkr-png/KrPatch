# -*- coding: utf-8 -*-
"""gfx11.py — 타이틀 인트로 '밝은 로고' 한글화  [사용자 피드백]

인트로 애니메이션에 쓰이는 4벌째 로고 자산. 기존 3벌(일본어 A/B, 영문1벌, 영문2벌)과
별개 레코드라 v0.6까지 일본어 원문이 그대로 나왔다.

실측 (트레이싱):
  맵    file 0x08AA44  (8행 × 16칸 = 128×64px, 맵크기 137B)
  타일  file 0x08A3C4  (104칸, 맵 직전까지)
  VRAM 적재 시 타일 인덱스 +0x20 오프셋 (역추적 때 주의)
  팔레트 역할: 0=배경 1=바깥선 2=몸통 3=안쪽음영
    ※ 본편 로고(어두운 버전)는 3=배경 0=바깥선 2=몸통 1=안쪽음영
      → 배경인접도로 역할을 정량 매칭해 대응표를 뽑았다 (아래 PAL)

방식: 이미 한글화된 본편 로고(블록 A+B, 160×88)를 128×64로 리샘플 →
      팔레트 대응 적용 → 타일 재구성(전역 dedup) → 맵 재작성.
      타일 예산 104칸을 넘으면 ValueError (병합=획 붕괴이므로 절대 안 함).
"""
import sys
sys.path.insert(0, '/root/ss2_work')
import numpy as np
from PIL import Image
import ss1_gfxtext as X
import ss1_logo as L

MAP   = 0x08AA44
TILE  = 0x08A3C4
BUDGET = (MAP - TILE) // 16          # 104
PAL   = {3: 0, 0: 1, 2: 2, 1: 3}     # 어두운 로고 값 → 밝은 로고 값


def composite(rom):
    """본편 로고 블록 A+B 를 160×88 캔버스로 합성 (배경=3)"""
    r = bytearray(rom)
    a = np.array(L.extract(r, L.A))
    b = np.array(L.extract(r, L.B))
    f = np.full((88, 160), 3, np.uint8)
    f[0:48] = a
    f[48:88, 16:152] = b
    return f


def _erode(m):
    p = np.pad(m, 1, constant_values=False)
    return (m & p[:-2,1:-1] & p[2:,1:-1] & p[1:-1,:-2] & p[1:-1,2:])


def build(src, W, H, target=0.56):
    """어두운 로고(배경3) → 밝은 로고 팔레트(0배경/1외곽/2몸통/3안쪽).
    ① 잉크 bbox 크롭 → 캔버스 채우기(비율 유지)  ② 원본 밝은로고의 잉크 비중에
    맞춰 임계값 자동 조정  ③ 침식으로 외곽/몸통/안쪽 3층 구성."""
    ink = (src != 3)
    ys, xs = np.nonzero(ink)
    crop = ink[ys.min():ys.max()+1, xs.min():xs.max()+1].astype(np.uint8) * 255
    ch, cw = crop.shape
    pad = 2
    sc = min((W - 2*pad) / cw, (H - 2*pad) / ch)
    nw, nh = max(1, int(cw*sc)), max(1, int(ch*sc))
    r = np.array(Image.fromarray(crop).resize((nw, nh), Image.BOX))
    canvas = np.zeros((H, W), np.uint8)
    oy, ox = (H - nh)//2, (W - nw)//2
    canvas[oy:oy+nh, ox:ox+nw] = r
    thr = 128
    for t in range(200, 20, -4):
        if (canvas > t).mean() >= target:
            thr = t; break
    m = canvas > thr
    body = _erode(m)
    inner = _erode(_erode(body))
    img = np.zeros((H, W), np.uint8)
    img[m] = 1
    img[body] = 2
    img[inner] = 3
    return img


def tile_bytes(cell):
    bs = bytearray()
    for y in range(8):
        w = 0
        for k in range(8):
            w |= int(cell[y, k]) << (14 - 2 * k)
        bs += bytes((w & 0xFF, w >> 8))
    return bytes(bs)


def patch(rom, report=True):
    grid, mapsize = X.read_map(rom, MAP)
    rows, cols = len(grid), max(len(r) for r in grid)
    H, W = rows * 8, cols * 8

    img = build(composite(rom), W, H)

    alloc, order = {}, []
    cells = []
    for ry in range(rows):
        row = []
        for cx in range(cols):
            bs = tile_bytes(img[ry*8:ry*8+8, cx*8:cx*8+8])
            if bs not in alloc:
                alloc[bs] = len(order)
                order.append(bs)
            row.append(alloc[bs])
        cells.append(row)

    if len(order) > BUDGET:
        raise ValueError(f'타일 {len(order)}개 > 예산 {BUDGET}칸')

    for i, bs in enumerate(order):
        rom[TILE + i*16: TILE + i*16 + 16] = bs
    for i in range(len(order), BUDGET):
        rom[TILE + i*16: TILE + i*16 + 16] = b'\x00' * 16

    p = MAP + 1
    for row in cells:
        for t in row:
            rom[p] = (t << 1) & 0xFF
            p += 1
        rom[p] = 0xFF
        p += 1
    assert p - MAP == mapsize, f'맵 크기 변동 {p-MAP} != {mapsize}'

    if report:
        print(f'  밝은 로고 {cols}x{rows}칸, 고유 타일 {len(order)}/{BUDGET}')
    return rom


if __name__ == '__main__':
    src = sys.argv[1] if len(sys.argv) > 1 else '/root/ss2_work/ss1/SS1_KO_v0.6.ngp'
    dst = sys.argv[2] if len(sys.argv) > 2 else '/tmp/test_gfx11.ngp'
    rom = bytearray(open(src, 'rb').read())
    patch(rom)
    open(dst, 'wb').write(rom)
    print('→', dst)
