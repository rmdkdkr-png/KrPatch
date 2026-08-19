# -*- coding: utf-8 -*-
"""gfx9.py — 전투 HUD 캐릭터 이름판 한글화  [I 항목]

실측 (이 세션):
  HUD 이름은 0x015A00 폰트도 BIOS 폰트도 아니고, 표준 그림 타일맵 레코드다.
  형식: [타일수 1B][타일 n×16B][행수 1B][행: 셀…0xFF]  (셀 = 타일번호×2 + 좌우반전)
  로더 PC 0x200501~0x200519, 이름판은 라운드 시작마다 다시 그려짐.
  세트1 0x78880~ / 세트2 0x794B8~ (동일 순서, 용도 추정: 모드별)

패치: 레코드 제자리 재작성 — 타일수·셀수·전체 길이 불변.
  한글(Galmuri7, 8×8/음절)을 앞에서부터 채우고 남는 타일·셀은 공백.
"""
import sys
sys.path.insert(0, '/root/ss2_work')
import ss1_ui

# (세트1 주소, 세트2 주소, 한글) — 원문 순서: KAZUKI HANZO UKYO SHIKI JYUBEI
# SOGETSU GENJURO HAOHMARU NAKORURU RIMURURU GALFORD SHIZUMARU AMAKUSA ZANKURO
NAMES = [
    (0x78880, 0x794B8, '카즈키'),
    (0x788D9, 0x79511, '한조'),
    (0x78931, 0x79569, '우쿄'),
    (0x78978, 0x795B0, '시키'),
    (0x789C0, 0x795F8, '쥬베이'),
    (0x78A29, 0x79661, '소게츠'),
    (0x78A92, 0x796CA, '겐쥬로'),
    (0x78AFB, 0x79733, '하오마루'),
    (0x78B64, 0x7979C, '나코루루'),
    (0x78BCD, 0x79805, '리무루루'),
    (0x78C36, 0x7986E, '갈포드'),
    (0x78C9F, 0x798D7, '시즈마루'),
    (0x78D08, 0x79940, '아마쿠사'),
    (0x78D71, 0x799A9, '잔쿠로'),
]


def parse(rom, rec):
    n = rom[rec]
    tiles = rec + 1
    mp = tiles + n * 16
    rows = rom[mp]
    p = mp + 1
    out = []
    for _ in range(rows):
        row = []
        while rom[p] != 0xFF:
            row.append(rom[p]); p += 1
        p += 1
        out.append(row)
    return n, tiles, mp, out, p - rec


def plate_colors(rom, tiles, n):
    """원본 이름판의 (배경, 잉크) 복원.
    실측: 판은 불투명 — 배경=최빈값(3, 검정), 글자=1(흰), 2=음영.
    0(투명)을 쓰면 뒤 흰 배경이 비쳐서 판이 하얗게 뜬다 (v0.5 사고)."""
    from collections import Counter
    c = Counter()
    for i in range(n * 16):
        b = rom[tiles + i]
        c[b & 3] += 1; c[(b >> 2) & 3] += 1; c[(b >> 4) & 3] += 1; c[(b >> 6) & 3] += 1
    bg = c.most_common(1)[0][0]
    ink = 1 if (1 in c and bg != 1) else next(v for v, _ in c.most_common() if v != bg)
    return bg, ink


def write_syllable_tile(rom, addr, ch, ink, bg):
    bm = ss1_ui.cell(ch, off=0)          # 7px 글리프를 8×8 위쪽 정렬
    for r in range(8):
        w = 0
        for k in range(8):
            w |= (ink if bm[r][k] else bg) << (14 - 2 * k)
        rom[addr + r * 2] = w & 0xFF
        rom[addr + r * 2 + 1] = w >> 8


def write_solid_tile(rom, addr, bg):
    for r in range(8):
        w = 0
        for k in range(8):
            w |= bg << (14 - 2 * k)
        rom[addr + r * 2] = w & 0xFF
        rom[addr + r * 2 + 1] = w >> 8


def patch(rom, report=True):
    done = 0
    for rec_pair in NAMES:
        ko = rec_pair[2]
        for rec in rec_pair[:2]:
            n, tiles, mp, rows, total = parse(rom, rec)
            assert len(rows) == 1, f'{rec:06X}: 1행 아님'
            cells = len(rows[0])
            assert len(ko) <= n, f'{rec:06X}: {ko} 타일 부족 ({n})'
            bg, ink = plate_colors(rom, tiles, n)
            # 타일: 음절 채우고 나머지는 판 배경색으로
            for i in range(n):
                if i < len(ko):
                    write_syllable_tile(rom, tiles + i * 16, ko[i], ink, bg)
                else:
                    write_solid_tile(rom, tiles + i * 16, bg)
            # 맵: 가운데 정렬 — 남는 칸을 좌우로 나눠 공백타일 배치
            # (원본 JP 이름은 셀을 꽉 채워서 정렬 문제가 없었음. 한글은 짧아서
            #  좌정렬하면 2P 판에서 왼쪽으로 쏠려 보인다.)
            blank = len(ko) if len(ko) < n else n - 1
            lpad = (cells - len(ko)) // 2
            rpad = cells - len(ko) - lpad
            newrow = ([blank * 2] * lpad + [i * 2 for i in range(len(ko))]
                      + [blank * 2] * rpad)
            p = mp + 1
            for c in newrow:
                rom[p] = c; p += 1
            done += 1
    if report:
        print(f'  HUD 이름판 {done}개 (14명 × 2세트) 재작성')
    return rom


if __name__ == '__main__':
    src = sys.argv[1] if len(sys.argv) > 1 else '/tmp/test_gfx8.ngp'
    dst = sys.argv[2] if len(sys.argv) > 2 else '/tmp/test_gfx9.ngp'
    rom = bytearray(open(src, 'rb').read())
    patch(rom)
    open(dst, 'wb').write(rom)
    print('→', dst)
