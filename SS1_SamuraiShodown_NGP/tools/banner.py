# -*- coding: utf-8 -*-
"""banner.py — 큰 그림텍스트(전투 배너)용 한글 렌더

원칙
  · 픽셀폰트를 정수배로만 확대한다 (보간 없음 → 획이 흐려지지 않음)
  · 팽창 외곽선은 쓰지 않는다. 8×8 타일 4색에서는 1px 속공간을 메워 글자를 뭉갠다.
    대신 굵은 획 + 우하 그림자로 원본의 입체감을 낸다.
  · 글자를 폰트 어드밴스가 아니라 실제 잉크 폭으로 붙인다 (한 칸이라도 더 크게)
  · 같은 높이면 원본이 큰 폰트를 고른다 (7px을 4배 키우면 뭉개진다)
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont

D = '/root/ss2_work/galmuri_repo/dist/'
CAND = [('Galmuri14.ttf', 14, 3), ('Galmuri11-Bold.ttf', 11, 3),
        ('Galmuri11.ttf', 11, 3), ('Galmuri9.ttf', 9, 2), ('Galmuri7.ttf', 7, 2)]


def _glyph(ch, font, size):
    f = ImageFont.truetype(D + font, size)
    im = Image.new('L', (size * 3 + 20, size * 3 + 20), 0)
    ImageDraw.Draw(im).text((10, 10), ch, font=f, fill=255)
    bb = im.getbbox()
    if not bb:
        return None, 0
    a = np.array(im.crop(bb)) > 110
    return a, bb[1]                       # 잉크, 윗변 위치(기준선 정렬용)


def _line(text, font, size, gap=1):
    """한 줄을 실제 잉크 폭으로 붙여 하나의 마스크로"""
    gs = []
    for ch in text:
        if ch == ' ':
            gs.append(None); continue
        gs.append(_glyph(ch, font, size))
    tops = [t for g, t in (x for x in gs if x) if g is not None]
    if not tops:
        return np.zeros((1, 1), bool)
    top0 = min(tops)
    bot = max(t - top0 + g.shape[0] for g, t in (x for x in gs if x) if g is not None)
    W = 0
    for x in gs:
        W += (size // 2 if x is None else x[0].shape[1] + gap)
    m = np.zeros((bot, max(1, W)), bool)
    cx = 0
    for x in gs:
        if x is None:
            cx += size // 2; continue
        g, t = x
        y = t - top0
        m[y:y + g.shape[0], cx:cx + g.shape[1]] |= g
        cx += g.shape[1] + gap
    cols = np.where(m.any(0))[0]
    return m[:, cols[0]:cols[-1] + 1] if len(cols) else m


def ko_banner(text, W, H, lines=None):
    """W×H 안에 최대한 크게. 반환값 0=배경 2=그림자 3=획"""
    if lines is None:
        lines = [text] if isinstance(text, str) else list(text)
    best = None
    for font, size, kmax in CAND:
        masks = [_line(t, font, size) for t in lines]
        bh = max(m.shape[0] for m in masks)
        bw = max(m.shape[1] for m in masks)
        th = bh * len(masks) + (len(masks) - 1)          # 줄 간격 1px
        for k in range(kmax, 0, -1):
            if th * k <= H - 2 * k and bw * k <= W - 2 * k:
                score = (th * k, size)
                if best is None or score > best[0]:
                    best = (score, masks, k, bh)
                break
    if best is None:
        masks = [_line(t, 'Galmuri7.ttf', 7) for t in lines]
        best = ((0, 0), masks, 1, max(m.shape[0] for m in masks))
    _, masks, k, bh = best

    can = np.zeros((H, W), bool)
    th = (bh * len(masks) + (len(masks) - 1)) * k
    y = max(0, (H - th) // 2)
    for m in masks:
        big = np.kron(m, np.ones((k, k), bool))
        x = max(0, (W - big.shape[1]) // 2)
        hh = min(big.shape[0], H - y)
        ww = min(big.shape[1], W - x)
        if hh > 0 and ww > 0:
            can[y:y + hh, x:x + ww] |= big[:hh, :ww]
        y += (bh + 1) * k

    img = np.zeros((H, W), np.uint8)
    sh = np.zeros_like(can)
    sh[k:, k:] = can[:-k or None, :-k or None]
    img[sh & ~can] = 2
    img[can] = 3
    return img.tolist()
