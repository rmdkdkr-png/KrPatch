#!/usr/bin/env python3
"""check_headers.py — 구운 머리글이 화면에 **의도한 그림 그대로** 뜨는지 자동 대조한다.

    python3 check_headers.py <원본.ngc> <구운롬.ngc> [--core ...] [--shots 폴더]

눈으로 넘기지 않기 위한 도구다. 두 롬을 각각 부팅해 머리글 스프라이트를 화면대로 합성하고,
빌더가 만들려던 도안과 **픽셀 단위로 비교**한다.

어긋난 픽셀은 셋 중 하나로 분류한다.

  공유 끝동강   다른 화면과 나눠 쓰는 타일이라 일부러 원판을 뒀다 — 정상
  격자 빈틈     어느 스프라이트도 안 덮는 자리에 획이 떨어졌다 — 화면에서 빠진다
  **어긋남**    설명이 안 된다. 주소나 겹침 처리가 틀린 것이다

한 번은 「막혔다」고 접었다가, 검증용 잘라내기가 머리글을 잘라먹고 있었을 뿐임을
이 대조로 알았다. 그래서 잘라내기 없이 스프라이트 좌표 그대로 본다.
"""
import sys, os, argparse, tempfile
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tiletool'))
sys.path.insert(0, HERE)
import tilemap as TM
from build_headers_ko import (HEADERS, LINE, FILL, capture, compose, ribbon_band,
                              strip_letters, layout, place, resolve, numbered_rom)


def main(argv=None):
    ap = argparse.ArgumentParser(description='머리글 자동 대조')
    ap.add_argument('orig', help='빌더에 넣은 입력 롬')
    ap.add_argument('baked', help='구운 롬')
    ap.add_argument('--font', default='Galmuri11-Bold.ttf')
    ap.add_argument('--core', default=None)
    a = ap.parse_args(argv)

    with open(a.orig, 'rb') as f:
        orig = f.read()
    fd, numpath = tempfile.mkstemp(suffix='.ngc')
    os.write(fd, numbered_rom(orig))
    os.close(fd)

    total_bad = 0
    try:
        for en, presses, ko, rng in HEADERS:
            osp, ovr = capture(a.orig, presses, a.core)
            nsp, nvr = capture(numpath, presses, a.core)
            bsp, bvr = capture(a.baked, presses, a.core)

            ntiles = TM.tile_table(nvr)
            numbers = {}
            for pat, x, y in nsp:
                ys, xs = np.nonzero(ntiles[pat] == 2)
                if len(ys):
                    numbers[(x, y)] = int(ys[0] * 8 + xs[0])

            canvas = compose(ovr, osp)
            band = ribbon_band(canvas)
            plan = resolve(orig, ovr, osp, numbers, rng)
            want, _ = place(strip_letters(canvas, band), band, layout(ko, a.font), plan, en)
            got = compose(bvr, bsp)

            keep = [(x, y) for x, y, idx, w in plan if not w]
            covered = np.zeros(want.shape, bool)
            for x, y, idx, w in plan:
                covered[y:y + 8, x:x + 8] = True

            h = min(want.shape[0], got.shape[0])
            w_ = min(want.shape[1], got.shape[1])
            diff = want[:h, :w_] != got[:h, :w_]
            shared = np.zeros_like(diff)
            for x, y in keep:
                shared[y:y + 8, x:x + 8] = True
            gap = ~covered[:h, :w_]

            n_shared = int((diff & shared).sum())
            n_gap = int((diff & ~shared & gap).sum())
            bad = diff & ~shared & ~gap
            n_bad = int(bad.sum())
            total_bad += n_bad

            print('%-13s -> %-9s 칸 %d / 기록 %d'
                  % (en, ko, len(plan), sum(1 for *_, w in plan if w)))
            print('   전체 %d픽셀 중 어긋남 %d — 공유 끝동강 %d, 격자 빈틈 %d, **설명 안 됨 %d**'
                  % (h * w_, int(diff.sum()), n_shared, n_gap, n_bad))
            if n_bad:
                ys, xs = np.nonzero(bad)
                print('   자리: %s' % [(int(y), int(x)) for y, x in zip(ys[:8], xs[:8])])
    finally:
        os.unlink(numpath)

    print('-' * 60)
    if total_bad:
        print('설명 안 되는 어긋남 %d픽셀 — 실패' % total_bad)
        return 1
    print('머리글 %d종 전부 의도한 그림 그대로 화면에 뜬다' % len(HEADERS))
    return 0


if __name__ == '__main__':
    sys.exit(main())
