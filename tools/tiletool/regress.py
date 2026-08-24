#!/usr/bin/env python3
"""regress.py — 기록된 화면들을 두 롬으로 오프라인 재렌더해 픽셀 비교.
에뮬레이터를 돌리지 않는다. 기록 1회 -> 이후 무한 회귀검사.

    python3 regress.py <기록폴더> <구판.ngc> <신판.ngc> [차이이미지폴더] [--fail-on-diff]

차이이미지: 위가 구판, 아래가 신판 (회색조, 왼쪽 SCR1 / 오른쪽 SCR2).
"차이 없음"이 기대값인 화면에서 차이가 나면 회귀다. 고친 화면은 당연히 차이가 난다 —
의도한 화면만 바뀌었는지 눈으로 확인하는 것이 이 도구의 쓰임이다.
"""
import sys, os, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tilemap as TM


def main(argv=None):
    ap = argparse.ArgumentParser(description='오프라인 픽셀 회귀검사')
    ap.add_argument('recdir')
    ap.add_argument('old')
    ap.add_argument('new')
    ap.add_argument('imgdir', nargs='?', default=None)
    ap.add_argument('--plane', type=int, choices=(1, 2), default=None,
                    help='한 평면만 비교 (기본: 두 평면 모두)')
    ap.add_argument('--fail-on-diff', action='store_true',
                    help='차이가 하나라도 있으면 종료코드 1 (CI용)')
    a = ap.parse_args(argv)

    with open(a.old, 'rb') as f:
        A = f.read()
    with open(a.new, 'rb') as f:
        B = f.read()
    bad = 0
    for name, maps, s2r in TM.load_records(a.recdir):
        changed = [s for s, ad in s2r.items() if A[ad:ad + 16] != B[ad:ad + 16]]
        ia = TM.render(maps, TM.tiles_from_rom(A, s2r), a.plane)
        ib = TM.render(maps, TM.tiles_from_rom(B, s2r), a.plane)
        nd = int((ia != ib).any(2).sum())
        if nd:
            bad += 1
        print('%-14s 픽셀차 %6d  바뀐타일 %3d%s' % (name, nd, len(changed), '' if nd == 0 else '  <-- 차이'))
        if nd and a.imgdir:
            from PIL import Image
            os.makedirs(a.imgdir, exist_ok=True)
            cv = Image.new('RGB', (ia.shape[1], ia.shape[0] * 2 + 8), (15, 15, 15))
            cv.paste(Image.fromarray(ia), (0, 0))
            cv.paste(Image.fromarray(ib), (0, ia.shape[0] + 8))
            cv.save(os.path.join(a.imgdir, name + '.png'))
    print('차이난 화면 %d개' % bad)
    if bad and a.fail_on_diff:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
