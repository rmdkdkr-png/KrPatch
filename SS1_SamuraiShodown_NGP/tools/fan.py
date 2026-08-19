# -*- coding: utf-8 -*-
"""fan.py — 부채 이름판(10×5칸) 한글화

부채가 사다리꼴이라 행마다 쓸 수 있는 가로폭이 다르다.
통짜로 갈면 부채가 지워지므로, 부채 윤곽은 그대로 두고 안쪽 이름만 갈아 끼운다.
  1) 행마다 부채 안쪽 구간(L,R)을 찾는다
  2) 이름이 있던 띠(BAND)만 부채 바탕색으로 지운다
  3) 띠 안에서 가장 좁은 행의 폭에 맞춰 글자 크기를 고른다
"""
import sys; sys.path.insert(0,'/root/ss2_work'); sys.path.insert(0,'/home/claude')
import numpy as np
import ss1_gfxtext as X
import banner

BAND = (2, 19)          # 이름 띠 (행). 부채 위쪽 뾰족한 부분과 아래 살은 건드리지 않는다
EDGE = 2                # 윤곽 보호 여유 px
BG   = 1                # 부채 바탕 = 밝은 회색
INK  = 3                # 글자 = 검정


# 이름이 없는 빈 부채 (80×40, 2bpp). 28장에서 이름 픽셀을 걷어내 복원한 것.
# 6글자짜리 일본어 이름은 부채 밖으로 삐져나오게 그려져 있어서,
# 원본 위에 덧그리면 양끝에 획 찌꺼기가 남는다. 그래서 빈 부채부터 새로 깐다.
_BLANK_B64 = "AAAAAAAAAAAP///wAAAAAAAAAAAAAAAAAAAA//VVVV//AAAAAAAAAAAAAAAAAD1VVVVVVVV8AAAAAAAAAAAAAAABVVVVVVVVVVVAAAAAAAAAAAAAABVVVVVVVVVVVVQAAAAAAAAAAAAAVVVVVVVVVVVVVQAAAAAAAAAAAAVVVVVVVVVVVVVVUAAAAAAAAAAAFVVVVVVVVVVVVVVUAAAAAAAAAAFVVVVVVVVVVVVVVVWAAAAAAAAABVVVVVVVVVVVVVVVVVAAAAAAAAAVVVVVVVVVVVVVVVVVVAAAAAAAAFVVVVVVVVVVVVVVVVVVAAAAAAADVVVVVVVVVVVVVVVVVVVAAAAAAAVVVVVVVVVVVVVVVVVVVWAAAAAANVVVVVVVVVVVVVVVVVVVXAAAAADVVVVVVVVVVVVVVVVVVVVXAAAAANVVVVVVVVVVVVVVVVVVVVcAAAADVVVVVVVVVVVVVVVVVVVVVcAAAA1VVVVVVVVVVVVVVVVVVVVVcAAAD9VVVVVVVVVVVVVVVVVVVVfwAAAAPVVVVVVVVWkZVVVVVVVVXAAAAAAD9VVVVVX86zr/VVVVVV/AAAAAAAAPVVVVX+s7Ouv1VVVV8AAAAAAAAAD9VVX7Ozs77O9VVX8AAAAAAAAAAAPVVzrO+uuvrNVXwAAAAAAAAAAAAD9fz766776/9fwAAAAAAAAAAAAAAPq8777vuv6vAAAAAAAAAAAAAAAAD+v77u7v6/AAAAAAAAAAAAAAAAAAPr7u7vq8AAAAAAAAAAAAAAAAAAAD+7u/r8AAAAAAAAAAAAAAAAAAAAAP++rwAAAAAAAAAAAAAAAAAAAAAAP//wAAAAAAAAAAAAAAAAAAAAAA/r6//wAAAAAAAAAAAAAAAAAAAAOr7//6wAAAAAAAAAAAAAAAAAAAA767+u/AAAAAAAAAAAAAAAAAAAAD6uvuusAAAAAAAAAAAAAAAAAAAAD7ruuvAAAAAAAAAAAAAAAAAAAAAD+66/wAAAAAAAAAAAAAAAAAAAAAAP//AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="

def blank_fan():
    import base64
    raw = base64.b64decode(_BLANK_B64)
    px = []
    for v in raw:
        for j in range(4): px.append((v >> (6 - 2*j)) & 3)
    return np.array(px[:80*40], np.uint8).reshape(40, 80)


def spans(img):
    """행마다 부채가 차지하는 (왼끝, 오른끝). 부채가 없으면 None"""
    out = []
    for row in img:
        nz = [x for x, v in enumerate(row) if v != 0]
        out.append((nz[0], nz[-1]) if nz else None)
    return out


def render(img, ko, d=None):
    """빈 부채 위에 한글 이름을 얹는다.
    d 를 주면 타일 예산 안에 드는 가장 큰 글자를 고른다 (압축에 맡기면 획이 깨진다)."""
    import ss1_logo as LG
    a = blank_fan().copy()
    H, W = a.shape
    y0, y1 = BAND
    inner = {}
    for y in range(y0, min(y1, H - 1) + 1):
        nz = [x for x, v in enumerate(a[y]) if v != 0]
        if not nz: continue
        L, R = nz[0] + EDGE, nz[-1] - EDGE
        if R - L >= 4: inner[y] = (L, R)
    if not inner:
        return a.tolist()

    # 큰 폰트부터. 부채는 아래로 갈수록 넓으니 아래에서 위로 자리를 훑는다.
    FONTS = (('Galmuri14.ttf', 14), ('Galmuri11-Bold.ttf', 11),
             ('Galmuri11.ttf', 11), ('Galmuri9.ttf', 9), ('Galmuri7.ttf', 7))
    def build(m, ty, rows):
        b = a.copy()
        th, tw = m.shape
        lo = max(L for L, R in rows); hi = min(R for L, R in rows)
        x0 = lo + (hi - lo + 1 - tw) // 2
        for yy in range(th):
            for xx in range(tw):
                if m[yy, xx]: b[ty + yy, x0 + xx] = INK
        return b

    place = None
    for font, size in FONTS:
        m = banner._line(ko, font, size)
        th, tw = m.shape
        for ty in range(max(inner) - th + 1, min(inner) - 1, -1):
            rows = [inner.get(ty + k) for k in range(th)]
            if any(r is None for r in rows): continue
            if min(R - L + 1 for L, R in rows) < tw: continue
            cand = build(m, ty, rows)
            if d is not None and LG.count(cand.tolist(), d) > d['n']:
                break                      # 이 크기는 예산 초과 → 한 단계 작은 폰트로
            return cand.tolist()
        else:
            continue
    return a.tolist()


NAMES = [
    # ── 일본어판 ──
    (0x092646, 'シキ',        '시키'),
    (0x09289F, 'ガルフォード',  '갈포드'),
    (0x092A98, 'リムルル',     '리무루루'),
    (0x092C91, 'ナコルル',     '나코루루'),
    (0x092E7A, '覇王丸',       '하오마루'),
    (0x093073, '緋雨閑丸',     '시즈마루'),
    (0x0932CC, '天草四郎時貞', '아마쿠사'),
    (0x0934C5, '橘右京',       '우쿄'),
    (0x0936EE, '柳生十兵衛',   '쥬베이'),
    (0x0938E7, '服部半蔵',     '한조'),
    (0x093B10, '牙神幻十郎',   '겐쥬로'),
    (0x093D09, '風間蒼月',     '소게츠'),
    (0x093F02, '風間火月',     '카즈키'),
    (0x09416B, '壬無月斬紅郎', '잔쿠로'),
    # ── 영어판 ──
    (0x094360, 'SHIKI',            '시키'),
    (0x094569, 'GALFORD',          '갈포드'),
    (0x094782, 'RIMURURU',         '리무루루'),
    (0x09499B, 'NAKORURU',         '나코루루'),
    (0x094BB4, 'HAOHMARU',         '하오마루'),
    (0x094DCD, 'HANZO HATTORI',    '한조'),
    (0x094FE6, 'JYUBEI YAGYU',     '쥬베이'),
    (0x09520F, 'UKYO TACHIBANA',   '우쿄'),
    (0x095448, 'SHIROU AMAKUSA',   '아마쿠사'),
    (0x095691, 'SHIZUMARU HISAME', '시즈마루'),
    (0x0958AA, 'GENJURO KIBAGAMI', '겐쥬로'),
    (0x095AE3, 'SOGETSU KAZAMA',   '소게츠'),
    (0x095CFC, 'KAZUKI KAZAMA',    '카즈키'),
    (0x095F45, 'ZANKURO MINAZUKI', '잔쿠로'),
]


def patch(rom, report=True):
    import ss1_logo as LG
    for m, ja, ko in NAMES:
        d = X.spec(rom, m)
        img = render(X.extract(rom, d), ko, d)
        n = X.inject(rom, d, img)
        if report:
            print('  %-18s → %-6s 타일 %d/%d' % (ja, ko, n, d['n']))
    return rom
