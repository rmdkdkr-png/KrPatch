# -*- coding: utf-8 -*-
"""gfx3.py — 영문 모드 전용 잔여물 (영문 타이틀 로고 + 누락 캐릭터명)"""
import sys, json; sys.path.insert(0,'/root/ss2_work'); sys.path.insert(0,'/home/claude')
import numpy as np
import ss1_gfxtext as X, ss1_logo as L

GPT = '/home/claude/ss1/SS1_인계/로고_GPT/SS1_logo_pixel_reinterpret.json'
# 영문 모드 타이틀 로고는 **두 벌** 있다. 둘 다 갈아야 한다.
EN_LOGO_A = 0x08EA59      # 1벌 본로고  20×6칸 (160×48) — 일본어판과 같은 크기
EN_LOGO_B = 0x08F019      # 1벌 부제팻말 19×5칸 (152×40)
EN2_LOGO_A = 0x08DCB4     # 2벌 본로고  19×6칸 (152×48)
EN2_LOGO_B = 0x08E20E     # 2벌 부제팻말 17×5칸 (136×40) — 일본어판과 같은 크기

# 기존 ss1_gfxtext.ITEMS 에서 빠져 있던 영문판 캐릭터명 3종
MISSING_NAMES = [
    (0x06B2ED, 'GENJURO KIBAGAMI', '겐쥬로'),
    (0x06B3C1, 'SHIROU AMAKUSA',   '아마쿠사'),
    (0x06B495, 'SOGETSU KAZAMA',   '소게츠'),
]

def logo_arrays(path=GPT):
    g = np.array(json.load(open(path, encoding='utf-8'))['canvas'], np.uint8) & 3
    # 각 블록이 화면 어디에 놓이는지는 롬 데이터로 확정했다.
    # 원본 2벌 블록은 1벌 블록의 **가로 8px 지점부터** 잘라낸 것이다(dx=8, 실측).
    # 1벌 A 는 화면 x=0 에 놓이므로 캔버스 x = 화면 x 가 그대로 성립한다.
    # 따라서 각 블록은 자기가 덮는 화면 구간을 캔버스에서 그대로 떠오면 된다.
    #   1벌 A(160폭) → 화면 0~159      1벌 B(152폭) → 화면 8~159
    #   2벌 A(152폭) → 화면 8~159      2벌 B(136폭) → 화면 16~151
    A  = g[0:48,  0:160]
    B  = g[48:88, 8:160]
    A2 = g[0:48,  8:160]
    B2 = g[48:88, 16:152]
    return A, B, A2, B2

def patch(rom, report=True, logo=None):
    A, Bimg, A2, B2 = logo_arrays(logo or GPT)
    for m, img in ((EN_LOGO_A, A), (EN_LOGO_B, Bimg), (EN2_LOGO_A, A2), (EN2_LOGO_B, B2)):
        d = X.spec(rom, m)
        n = X.inject(rom, d, img.tolist())
        if report: print('  영문 타이틀 %06X  %2d×%-2d  타일 %d/%d' % (m, d['w'], d['h'], n, d['n']))
    for m, en, ko in MISSING_NAMES:
        d = X.spec(rom, m)
        img, how = fit(ko, d)
        n = X.inject(rom, d, img)
        if report: print('  %-18s → %-6s %2d×%-2d 타일 %d/%d  (%s)' % (en, ko, d['w'], d['h'], n, d['n'], how))
    return rom


def fit(ko, d):
    """타일 한도 안에 들어가는 렌더를 고른다.
    압축(강제 병합)이 걸리면 획이 무너지므로, 압축이 걸리기 전에 글자를 줄인다."""
    import banner
    W, H = d['w']*8, d['h']*8
    multi = not isinstance(ko, str)
    import numpy as np
    cands = [(X.ko_image(ko, W, H, shadow=True),  '기본'),
             (X.ko_image(ko, W, H, shadow=False), '그림자 없음')]
    # 폰트만 한 단계씩 낮춘다 (칸은 그대로 — 높이를 깎으면 글자가 뭉갠다)
    for font, size in (() if multi else (('Galmuri11-Bold.ttf', 11), ('Galmuri11.ttf', 11),
                       ('Galmuri9.ttf', 9), ('Galmuri7.ttf', 7))):
        m = banner._line(ko, font, size)
        if m.shape[0] > H or m.shape[1] > W: continue
        y0 = (H - m.shape[0])//2; cx = (W - m.shape[1])//2
        for dx in (0, -1, 1, -2, 2, -3, 3, -4, 4):   # 타일 경계에 맞물리는 위치를 고른다
            x0 = cx + dx
            if x0 < 0 or x0 + m.shape[1] > W: continue
            a = np.zeros((H, W), np.uint8)
            a[y0:y0+m.shape[0], x0:x0+m.shape[1]][m] = 1
            cands.append((a.tolist(), '%s%+d' % (font.replace('.ttf',''), dx)))
    for img, how in cands:
        if len(img) != H:                      # 높이 보정(가운데)
            pad = H - len(img)
            img = [[0]*W]*(pad//2) + img + [[0]*W]*(pad - pad//2)
        if L.count(img, d) <= d['n']:
            return img, how
    return cands[0][0], '한도 초과 — 압축됨'
