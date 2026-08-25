#!/usr/bin/env python3
"""glitchscan.py — 구운 롬을 화면 전체로 훑어 **부순 자리를 기계적으로 잡는다**.

    python3 glitchscan.py <원판.ngc> <구운롬.ngc> [--screens screens_svc.json]
                          [--core libretro.so] [--out 폴더] [--verbose]

## 왜 필요한가

`check_headers.py`·`check_names.py`·`build_player_ko.py --check` 는 전부
**내가 그리려던 도안과 화면이 같은지**만 본다. 도안이 깨져 있으면 그대로 통과하고,
화면의 나머지가 망가져도 안 본다. 실제로 타이틀 큰 로고가 눈에 띄게 깨진 채
세 대조를 다 통과했다. 그래서 이 도구가 따로 있다.

## 어디서 재나 — 색이 아니라 **색인**

처음엔 화면 RGB 로 재려고 배경색·외곽선색을 추론했다. 세 가지 방법을 다 써 봤고 다 틀렸다.

    가장 흔한 색을 배경으로     하늘 그라데이션의 다른 색조를 외곽선으로 뽑았다
    침식 후 살아남는 색을 배경으로  큰 채움(로고 몸통)도 살아남아 배경으로 잡혔다
    행마다 안 바뀐 열의 최빈색   로고가 화면 폭을 거의 다 먹어서, 살아남은 불꽃이 배경이 됐다

로고 뒤는 하늘이 아니라 **폭발 그림**이다. "배경"이라는 게 화면에 존재하지 않는다.

타일 색인 공간에서는 추론이 필요 없다. **색인 0 = 투명**이 정의상 확실하다.
그래서 화면 픽셀이 아니라 **평면별 색인 배열**을 비교한다.

## 무엇을 글리치로 보나

    지워짐   원판이 색인 != 0 이던 자리가 패치에서 0 이 됐다 — 그림을 없앤 것
    더해짐   원판이 0 이던 자리에 패치가 그림을 넣었다 — 새로 그린 것
    파편     패치에만 있는 8픽셀 미만짜리 외딴 덩어리 — 지우다 만 조각

판정은 간단하다. **채워 넣은 것보다 없앤 것이 많으면 부순 것이다.**
글자를 바꾸는 일은 지운 만큼 다시 그리므로 지워짐과 더해짐이 비슷하게 나온다.
유령 지우기가 배경까지 먹으면 지워짐만 튄다 — 큰 로고가 정확히 그 모양이었다.

## 한계

원판을 기준으로 하므로 원판에 없던 종류의 잘못은 못 잡는다.
글자가 틀렸는지(오타·오역)도 못 본다. 여기서 통과했다는 것은
"원판이 갖고 있던 그림을 부수지 않았다"는 뜻이지 "잘 그렸다"는 뜻이 아니다.
"""
import sys, os, json, struct, argparse
from collections import deque
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tiletool'))
import tilemap as TM

FRAG_MAX = 8
SCR = {1: 0x9000, 2: 0x9800}
SCREEN_W, SCREEN_H = 160, 152


def planes(n):
    """화면에 실제로 보이는 범위를 평면별 **색인 배열**로 뜬다."""
    v = TM.dump_vram(n)
    tiles = TM.tile_table(v)
    scroll = TM.scroll_of(v)
    out = {}
    for pl, base in SCR.items():
        sx, sy = scroll[pl]
        A = np.zeros((SCREEN_H, SCREEN_W), np.uint8)
        for y in range(SCREEN_H):
            ty = ((y + sy) % 256) // 8
            oy = ((y + sy) % 256) % 8
            for x in range(SCREEN_W):
                tx = ((x + sx) % 256) // 8
                ox = ((x + sx) % 256) % 8
                s = struct.unpack_from('<H', v, base - 0x8000 + (ty * 32 + tx) * 2)[0]
                A[y, x] = tiles[s & TM.PAT_MASK][oy, ox]
        out[pl] = A
    S = np.zeros((SCREEN_H, SCREEN_W), np.uint8)
    for i in range(64):
        o = 0x8800 - 0x8000 + i * 4
        b0, b1, b2, b3 = v[o], v[o + 1], v[o + 2], v[o + 3]
        if not (b1 & 0x18):
            continue
        pat = b0 | ((b1 & 1) << 8)
        x, y = b2, b3
        if x >= SCREEN_W or y >= SCREEN_H:
            continue
        t = tiles[pat]
        h = min(8, SCREEN_H - y)
        w = min(8, SCREEN_W - x)
        blk = S[y:y + h, x:x + w]
        S[y:y + h, x:x + w] = np.where(t[:h, :w] > 0, t[:h, :w], blk)
    out['스프라이트'] = S
    return out


def components(mask):
    H, W = mask.shape
    seen = np.zeros((H, W), bool)
    out = []
    ys, xs = np.nonzero(mask)
    for sy, sx in zip(ys, xs):
        if seen[sy, sx]:
            continue
        q = deque([(sy, sx)])
        seen[sy, sx] = True
        cells = []
        while q:
            y, x = q.popleft()
            cells.append((y, x))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < H and 0 <= nx < W and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    q.append((ny, nx))
        out.append(cells)
    return out


def compare(A, B):
    """평면 하나의 지표. 색인 0 = 투명이라 배경 추론이 필요 없다."""
    erased = int(((A != 0) & (B == 0)).sum())
    added = int(((A == 0) & (B != 0)).sum())
    recol = int(((A != 0) & (B != 0) & (A != B)).sum())
    fresh = (B != 0) & (A == 0)
    frag = sum(1 for c in components(fresh) if len(c) < FRAG_MAX)
    changed = int((A != B).sum())
    return {'바뀜': changed, '지워짐': erased, '더해짐': added,
            '색바뀜': recol, '파편': frag}


def verdict(m):
    """채워 넣은 것보다 없앤 것이 많으면 부순 것이다."""
    if m['바뀜'] == 0:
        return None
    if m['지워짐'] > 60 and m['지워짐'] > 2 * (m['더해짐'] + m['색바뀜']):
        return '**그림을 부숨**'
    if m['파편'] > 4:
        return '**파편**'
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description='구운 롬 글리치 훑기')
    ap.add_argument('orig')
    ap.add_argument('baked')
    ap.add_argument('--screens', default=os.path.join(HERE, '..', 'tiletool', 'screens_svc.json'))
    ap.add_argument('--core', default=None)
    ap.add_argument('--out', default=None)
    ap.add_argument('--settle', type=int, default=60)
    ap.add_argument('--verbose', action='store_true')
    a = ap.parse_args(argv)

    from observe import make_harness, walk
    screens = json.load(open(a.screens))

    bad = 0
    print('%-12s %-10s %6s %6s %6s %6s %5s  %s'
          % ('화면', '평면', '바뀜', '지워짐', '더해짐', '색바뀜', '파편', '판정'))
    for s in screens:
        got = []
        for rom in (a.orig, a.baked):
            n = make_harness(rom, a.core)
            walk(n, s['route'])
            n.run(a.settle)
            got.append(planes(n))
        any_row = False
        for pl in (1, 2, '스프라이트'):
            m = compare(got[0][pl], got[1][pl])
            v = verdict(m)
            if m['바뀜'] == 0 and not a.verbose:
                continue
            any_row = True
            bad += v is not None
            print('  %-10s %-10s %6d %6d %6d %6d %5d  %s'
                  % (s['name'], 'SCR%s' % pl if pl != '스프라이트' else pl,
                     m['바뀜'], m['지워짐'], m['더해짐'], m['색바뀜'], m['파편'],
                     v or '정상'))
        if not any_row:
            print('  %-10s %s' % (s['name'], '안 바뀜'))

        if a.out:
            os.makedirs(a.out, exist_ok=True)
            from PIL import Image
            PAL = np.array([(0, 0, 0), (230, 90, 30), (200, 30, 50), (60, 70, 170)], np.uint8)
            rows = []
            for pl in (1, 2, '스프라이트'):
                rows += [PAL[got[0][pl]], PAL[got[1][pl]]]
            im = np.concatenate(rows, 0)
            Image.fromarray(im).resize((SCREEN_W * 2, im.shape[0] * 2),
                                       Image.NEAREST).save(
                os.path.join(a.out, '%s.png' % s['name']))

    print('-' * 72)
    if bad:
        print('부순 자리 %d곳 — 실패' % bad)
        return 1
    print('원판 그림을 부순 자리 없음')
    return 0


if __name__ == '__main__':
    sys.exit(main())
