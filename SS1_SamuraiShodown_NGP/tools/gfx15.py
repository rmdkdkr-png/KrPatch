#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gfx15.py — ① 인트로 두루마리 배너 ポケット格闘シリーズ → 포켓격투시리즈
              ② 전투 HUD 한자 闘 → 투

① 배너 (실측)
    타일 33장 연속  롬 0x8AC5E  (VRAM 176~208 로 업로드)
    맵은 코드가 만들며 병합 사용: (행1,열2)=(행1,열12)=193, (행2,열2/12)=207
    펼침 애니 전 프레임이 같은 타일을 클리핑해 쓰므로 이 한 곳만 고치면 된다.
    텍스트는 v3(+v1 안티앨리어스), x33~93 · y1~11. 열 3~11 (x24~95) 은 전부
    비공유 타일이라 이 구역만 지우고 다시 그리면 병합 제약이 안 깨진다.

② HUD 한자 (실측)
    타일 4장(16×16) 연속  롬 0x785E5  (VRAM 31~34, scr1 (열9~10,행0~1))
    v3=검정바탕 v1=흰 획 v2=게이지 체크무늬가 블록 안에 구워져 있음.
    획(v1)을 행 단위 최근접 배경값으로 메꾼 뒤 「투」를 v1 로 얹는다.
"""
import struct, sys
sys.path.insert(0, '/root/ss2_work')

BANNER = 0x8AC5E
BANNER_ROWS = [[176,177,178,179,180,181,182,183,184,185,186,187,188,189,190],
               [191,192,193,194,195,196,197,198,199,200,201,202,193,203,204],
               [205,206,207,205,205,205,205,205,205,205,205,205,207,208,205]]
KANJI = [(0x7859D, '결'),   # 決
         (0x785E5, '투'),   # 闘 (기본)
         (0x7862D, '살'),   # 殺
         (0x78675, '사'),   # 死
         (0x786BD, '노')]   # 怒  — 0x48 간격 사다리, 분노 게이지 상태별 교체 업로드

GAL7 = '/root/ss2_work/galmuri_repo/dist/Galmuri7.bdf'
GAL11 = '/root/ss2_work/galmuri_repo/dist/Galmuri11.bdf'
GAL11B = '/root/ss2_work/galmuri_repo/dist/Galmuri11-Bold.bdf'


def _glyph(bdf, ch):
    from bdf_render import parse_bdf, glyph_pixels
    if bdf not in _glyph.cache:
        _glyph.cache[bdf] = parse_bdf(bdf)[1]
    g = _glyph.cache[bdf][ord(ch)]
    return glyph_pixels(g)
_glyph.cache = {}


def _read_img(rom, base, rows, first):
    img = [[0]*(len(rows[0])*8) for _ in range(len(rows)*8)]
    for ri, row in enumerate(rows):
        for ci, idx in enumerate(row):
            off = base + (idx-first)*16
            for r in range(8):
                w = struct.unpack_from('<H', rom, off + r*2)[0]
                for k in range(8):
                    img[ri*8+r][ci*8+k] = (w >> (14-2*k)) & 3
    return img


def _write_img(rom, base, rows, first, img):
    written = {}
    for ri, row in enumerate(rows):
        for ci, idx in enumerate(row):
            cell = tuple(tuple(img[ri*8+r][ci*8+k] for k in range(8)) for r in range(8))
            if idx in written:
                assert written[idx] == cell, '공유 타일 %d 내용 불일치' % idx
                continue
            written[idx] = cell
            off = base + (idx-first)*16
            for r in range(8):
                w = 0
                for k in range(8): w |= cell[r][k] << (14-2*k)
                struct.pack_into('<H', rom, off + r*2, w)


def patch_banner(rom):
    img = _read_img(rom, BANNER, BANNER_ROWS, 176)
    # 텍스트 소거 (비공유 열 3~11 = x24~95, y1~11)
    for y in range(1, 12):
        for x in range(24, 96):
            if img[y][x] in (1, 3): img[y][x] = 0
    # 잔여 확인: 공유 구역(x96~103)에 텍스트가 남으면 안 됨
    rest = [(x, y) for y in range(1, 12) for x in range(96, 104) if img[y][x] == 3]
    assert not rest, '배너 공유 구역에 텍스트 잔존 %r' % rest
    # 포켓격투시리즈 (Galmuri7, v3) 가운데 정렬
    text = '포켓격투시리즈'
    gs = [_glyph(GAL7, c) for c in text]
    adv = 8
    tw = adv*len(text) - 1
    x0 = 24 + (96-24 - tw)//2
    for i, (pts, (w, h, xo, yo)) in enumerate(gs):
        gy = 2 + (9 - h)//2 + 1
        for (px, py) in pts:
            x, y = x0 + i*adv + px, gy + py
            if 24 <= x < 96 and 1 <= y < 12: img[y][x] = 3
    _write_img(rom, BANNER, BANNER_ROWS, 176, img)
    print('  배너: 포켓격투시리즈 (x%d~, 폭%d)' % (x0, tw))


def patch_kanji(rom):
    rows = [[0, 1], [2, 3]]           # 타일 순서: TL TR BL BR
    done = []
    for base, ch in KANJI:
        img = _read_img(rom, base, rows, 0)
        # 흰 획(v1) 인페인트: 같은 행에서 가장 가까운 비획 값
        for y in range(16):
            for x in range(16):
                if img[y][x] == 1:
                    for d in range(1, 16):
                        l = img[y][x-d] if x-d >= 0 else None
                        r = img[y][x+d] if x+d < 16 else None
                        v = next((u for u in (l, r) if u is not None and u != 1), None)
                        if v is not None: img[y][x] = v; break
                    else: img[y][x] = 3
        # 한글 (Galmuri11, v1 + v3 테두리) — 16×16 가운데
        pts, (w, h, xo, yo) = _glyph(GAL11, ch)
        x0, y0 = (16-w)//2, (16-h)//2
        ink = {(x0+px, y0+py) for px, py in pts}
        for (x, y) in ink:                   # 검정 테두리(halo) 먼저
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nx, ny = x+dx, y+dy
                    if 0 <= nx < 16 and 0 <= ny < 16 and (nx, ny) not in ink:
                        img[ny][nx] = 3
        for (x, y) in ink:
            if 0 <= x < 16 and 0 <= y < 16: img[y][x] = 1
        _write_img(rom, base, rows, 0, img)
        done.append(ch)
    print('  HUD: 闘決殺死怒 → ' + '/'.join(done))


def patch(rom):
    patch_banner(rom)
    # patch_kanji(rom) — v0.14 에서 원복. 분노 게이지 한자(闘決殺死怒)는
    # 게임 시스템 표시라 한글 낱자(투/노…)로 바꾸면 오히려 뜻이 안 통한다는 피드백.
    return rom


if __name__ == '__main__':
    rom = bytearray(open('/root/ss2_work/ss1/Samurai Shodown! (JUE) [M][!].ngp', 'rb').read())
    patch(rom)
    open('/tmp/gfx15_test.ngp', 'wb').write(rom)
    print('→ /tmp/gfx15_test.ngp')
