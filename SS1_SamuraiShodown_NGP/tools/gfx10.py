# -*- coding: utf-8 -*-
"""gfx10.py — 난이도 선택 화면 재렌더 (가독성)  [사용자 피드백 반영]

'검객/검호/검성 + 초급자용/중급자용/상급자용' 레코드가 TTF 렌더(획 뭉개짐,
카→가 계열)로 흐릿했다. BDF 픽셀 그대로 다시 굽는다.
맵은 순차 배열(타일 0..n-1)이라 손대지 않고 타일 블록만 재작성.
값: 바탕 0 / 글자 1 / 우하 그림자 2 (기존 ko_image 체계 유지, 7px 라벨은 그림자 생략)
"""
import sys
sys.path.insert(0, '/root/ss2_work')
import numpy as np
from gfx7 import bdf_line

# (맵주소, 타일수, 폭칸, 큰글자, 작은라벨)  ── 작은라벨 None이면 2행 전체가 큰글자
RECS = [
    (0x6B9A5, 12, 4, '검성', '상급자용'),
    (0x6BA76, 12, 4, '검호', '중급자용'),
    (0x6BB47, 12, 4, '검객', '초급자용'),
    (0x6BC80,  8, 4, '상급', None),
    (0x6BD0C,  8, 4, '중급', None),
    (0x6BD98,  8, 4, '초급', None),
]


def compose(cols, rows_px, big, small):
    W = cols * 8
    img = np.zeros((rows_px, W), np.uint8)
    bmask = bdf_line(big, W, 16)
    # 그림자(+1,+1) 먼저, 글자 나중
    sh = np.zeros_like(bmask)
    sh[1:, 1:] = bmask[:-1, :-1]
    img[:16][sh[:16]] = 2
    img[:16][bmask[:16]] = 1
    if small:
        smask = bdf_line(small, W, 8)
        img[16:24][smask] = 1
    return img


def patch(rom, report=True):
    for mp, nt, cols, big, small in RECS:
        tiles = mp - nt * 16
        rows = rom[mp]
        img = compose(cols, rows * 8, big, small)
        assert nt == cols * rows, f'{mp:06X}: 타일수 불일치'
        for t in range(nt):
            r, c = divmod(t, cols)
            cell = img[r*8:r*8+8, c*8:c*8+8]
            for y in range(8):
                w = 0
                for k in range(8):
                    w |= int(cell[y, k]) << (14 - 2*k)
                rom[tiles + t*16 + y*2] = w & 0xFF
                rom[tiles + t*16 + y*2 + 1] = w >> 8
    if report:
        print(f'  난이도 레코드 {len(RECS)}개 BDF 재렌더')
    return rom


if __name__ == '__main__':
    src = sys.argv[1]
    dst = sys.argv[2]
    rom = bytearray(open(src, 'rb').read())
    patch(rom)
    open(dst, 'wb').write(rom)
    print('→', dst)
