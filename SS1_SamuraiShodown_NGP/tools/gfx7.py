# -*- coding: utf-8 -*-
"""gfx7.py — 어트랙트(오프닝) 캐릭터명 한글화  [K 항목]

구조 (이 세션에서 트레이싱으로 실측):
  마스터 디렉터리   file 0x1BA7CD  (16×u32le, [addr24|meta<<24]) — entry15 = 이름 스크립트 블록
  스크립트 블록     file 0x111521 ~ 0x112709
    이름 레코드     [04 00][0x80|cnt][idxoff][hdr2][ (dx,dy)×cnt ]   dx,dy = 픽셀×2
    엔트리(타일표)   u16le × cnt — 스프라이트별 뱅크 타일번호. 레코드 순서대로 연속 소비,
                    idxoff 하위바이트로 대조 가능 (이름 28레코드 전부 일치 확인)
  타일 뱅크        file 0x1B7389 + 타일번호×16  (2bpp 워드LE)
  복사 루틴        PC 0x2005EE (loadL×4) — 엔트리마다 16B 복사. 잉크값 = 1 (음영 2)

전략: 엔트리·pairs 재작성 + 구 이름 타일(0x7F~0x19F)을 한글 글리프 풀로 재활용.
      압축·병합 없음 — 전 이름이 폰트 크기 선택만으로 예산 안에 들어감.
"""
import sys, json
sys.path.insert(0, '/root/ss2_work'); sys.path.insert(0, '/home/claude')
import numpy as np
from bdf_render import parse_bdf, glyph_pixels

_BDF = {}
def _font(px):
    if px not in _BDF:
        _BDF[px] = parse_bdf(f'/root/ss2_work/galmuri_repo/dist/Galmuri{px}.bdf')[1]
    return _BDF[px]


def _mask(ch, px):
    g = _font(px).get(ord(ch))
    if g is None:
        return np.zeros((1, 1), bool), (0, 0)
    pts, (w, h, xo, yo) = glyph_pixels(g)
    a = np.zeros((max(h, 1), max(w, 1)), bool)
    for x, y in pts:
        a[y, x] = True
    return a, (xo, yo)


def bdf_line(text, W, H):
    """BDF 픽셀 그대로 (TTF는 획이 뭉개짐 — 카→가). 큰 폰트부터 시도, 가운데 정렬."""
    for px, cell in ((14, 16), (11, 12), (9, 10), (7, 8)):
        masks = [_mask(c, px) for c in text]
        adv = [max(cell if px == 14 else m.shape[1] + 1, m.shape[1]) for m, _ in masks]
        total = sum(adv)
        maxh = max(m.shape[0] for m, _ in masks)
        if total <= W and maxh <= H:
            ink = np.zeros((H, W), bool)
            x = (W - total) // 2
            # 기준선: yoff 반영해 바닥 정렬
            base = max(m.shape[0] + yo for (m, (xo, yo)) in masks)
            y0 = (H - base) // 2
            for (m, (xo, yo)), a in zip(masks, adv):
                xx = x + max(0, (a - m.shape[1]) // 2)
                yy = y0 + base - (m.shape[0] + yo)
                hh, ww = m.shape
                y1, x1 = min(H, yy + hh), min(W, xx + ww)
                if y1 > yy and x1 > xx:
                    ink[yy:y1, xx:x1] |= m[:y1-yy, :x1-xx]
                x += a
            return ink
    raise ValueError(f'{text}: {W}×{H} 안에 못 넣음')

BANK   = 0x1B7389
POOL   = (0x7F, 0x1A0)     # [시작, 끝) — 구 이름 글리프 타일. 0x1A0+ 는 SNK/주먹 등 그래픽이라 불가침
BLOCK  = (0x111521, 0x112709)

# (JP레코드주소, EN레코드주소는 순서로) 이름 로스터 — 스크립트 등장 순서 그대로
NAMES = ['시키', '갈포드', '리무루루', '나코루루', '하오마루', '한조', '쥬베이',
         '우쿄', '시즈마루', '겐쥬로', '아마쿠사', '소게츠', '카즈키', '잔쿠로']


def parse_records(rom):
    """이름 28레코드 (JP 14 + EN 14). 엔트리 절대주소는 연속 소비 + 핫조 앵커로 복원."""
    recs = []
    i, end = BLOCK
    while i < end - 6:
        if rom[i] == 0x04 and rom[i+1] == 0x00 and (rom[i+2] & 0x80) and 1 <= (rom[i+2] & 0x3F) <= 32:
            cnt = rom[i+2] & 0x3F
            pairs = [(rom[i+6+2*k], rom[i+7+2*k]) for k in range(cnt)]
            recs.append(dict(addr=i, cnt=cnt, idxoff=rom[i+3], pairs=pairs))
            i += 6 + cnt*2
            continue
        i += 1
    anchor = next(r for r in recs if r['addr'] == 0x111687)   # 服部半蔵 → 0x11208D 실측
    ai = recs.index(anchor)
    recs[ai]['ea'] = 0x11208D
    for j in range(ai+1, len(recs)):
        recs[j]['ea'] = recs[j-1]['ea'] + 2*recs[j-1]['cnt']
    for j in range(ai-1, -1, -1):
        recs[j]['ea'] = recs[j+1]['ea'] - 2*recs[j]['cnt']
    name_recs = [r for r in recs if (r['ea'] & 0xFF) == r['idxoff']]
    assert len(name_recs) == 28, f'이름 레코드 {len(name_recs)}개 (28개여야 함)'
    return name_recs


def cells_of(ink):
    """16px 높이 ink 마스크 → {(row,col): 8×8 uint8} (잉크=1)"""
    H, W = ink.shape
    out = {}
    for r in range(H // 8):
        for c in range(W // 8):
            t = np.zeros((8, 8), np.uint8)
            t[ink[r*8:r*8+8, c*8:c*8+8]] = 1
            out[(r, c)] = t
    return out


def tile_bytes(t):
    bs = bytearray()
    for y in range(8):
        w = 0
        for k in range(8):
            w |= int(t[y, k]) << (14 - 2*k)
        bs += bytes((w & 0xFF, w >> 8))
    return bytes(bs)


def patch(rom, report=True):
    recs = parse_records(rom)
    pool = list(range(*POOL))
    alloc = {}                     # tile_bytes → 타일번호
    blank = tile_bytes(np.zeros((8, 8), np.uint8))

    def get_tile(bs):
        if bs in alloc:
            return alloc[bs]
        assert pool, '타일 풀 고갈'
        t = pool.pop(0)
        alloc[bs] = t
        rom[BANK + t*16: BANK + t*16 + 16] = bs
        return t

    get_tile(blank)                # 풀 첫 타일 = 공백

    used_max = 0
    for i, r in enumerate(recs):
        name = NAMES[i % 14]
        cols = r['cnt'] // 2
        W, H = cols * 8, 16
        ink = bdf_line(name, W, H)
        # 원 그리드 중심 유지 (dx 단위 = 픽셀×2)
        odx = [p[0] for p in r['pairs']]
        center = (min(odx) + max(odx) + 16) // 2
        start = max(0, center - W)          # W px = 2W 하프픽셀
        start -= start % 2
        cell = cells_of(ink)
        new_pairs, new_tiles = [], []
        for rr in range(2):
            for cc in range(cols):
                new_pairs.append((start + cc*16, rr*16))
                new_tiles.append(get_tile(tile_bytes(cell[(rr, cc)])))
        while len(new_pairs) < r['cnt']:    # cnt 홀수분 — 공백을 마지막 칸 옆에
            new_pairs.append((start + cols*16, 0))
            new_tiles.append(alloc[blank])
        # 기록: pairs (레코드 본문), entries (타일표)
        for k, (dx, dy) in enumerate(new_pairs):
            rom[r['addr']+6+2*k] = dx
            rom[r['addr']+7+2*k] = dy
        for k, t in enumerate(new_tiles):
            rom[r['ea']+2*k] = t & 0xFF
            rom[r['ea']+2*k+1] = t >> 8
        used_max = max(used_max, max(new_tiles))
        if report and i % 14 == 0:
            print(('  JP' if i < 14 else '  EN') + ' 세트')
        if report:
            ncell = sum(1 for t in new_tiles if t != alloc[blank])
            print(f'    {name:<5s} 스프라이트 {r["cnt"]:2d}칸 / 글리프 {ncell:2d}칸')
    if report:
        print(f'  고유 타일 {len(alloc)}개 (풀 {POOL[1]-POOL[0]}개 중), 최대 타일 0x{used_max:X}')
    return rom


def verify(rom, out_png='/tmp/gfx7_verify.png'):
    """롬 되읽기 → 레코드 재조립 렌더 (원본 롬 기준 주소 아님 — 구조 자체를 다시 파싱)"""
    recs = parse_records(rom)
    imgs = []
    for r in recs:
        tiles = [rom[r['ea']+2*k] | (rom[r['ea']+2*k+1] << 8) for k in range(r['cnt'])]
        xs = [p[0] for p in r['pairs']]; ys = [p[1] for p in r['pairs']]
        W = (max(xs) - min(xs))//2 + 8; H = (max(ys) - min(ys))//2 + 8
        img = np.zeros((H, W), np.uint8)
        for (dx, dy), t in zip(r['pairs'], tiles):
            b = rom[BANK+t*16: BANK+t*16+16]
            for y in range(8):
                w = b[y*2] | (b[y*2+1] << 8)
                for k in range(8):
                    v = (w >> (14-2*k)) & 3
                    yy, xx = (dy-min(ys))//2+y, (dx-min(xs))//2+k
                    if v: img[yy, xx] = v
        imgs.append(img)
    W = max(im.shape[1] for im in imgs)
    canvas = np.zeros((sum(im.shape[0]+4 for im in imgs), W), np.uint8)
    y = 0
    for im in imgs:
        canvas[y:y+im.shape[0], :im.shape[1]] = im
        y += im.shape[0] + 4
    from PIL import Image
    Image.fromarray((canvas*85).astype('uint8')).resize((W*3, canvas.shape[0]*3), Image.NEAREST).save(out_png)
    return out_png


if __name__ == '__main__':
    src = sys.argv[1] if len(sys.argv) > 1 else '/root/ss2_work/ss1/SS1_KO_rebuild.ngp'
    dst = sys.argv[2] if len(sys.argv) > 2 else '/root/ss2_work/ss1/SS1_KO_attract.ngp'
    rom = bytearray(open(src, 'rb').read())
    patch(rom)
    open(dst, 'wb').write(rom)
    print('→', dst)
    print('검증 렌더:', verify(rom))
