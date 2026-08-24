#!/usr/bin/env python3
"""coverage.py — 관측 커버리지(화면에 실제로 뜬 ROM 타일 주소)를 요약한다.

    python3 coverage.py <기록폴더> [--window LO:HI] [--list]

--window 는 정적 아이템 스캐너가 훑는 구간(SS2에서는 0x1D0000:0x200000).
그 밖에 있는 타일이 곧 스캐너의 사각지대다 — 화면에는 떴는데 스캐너는 못 본 타일.
"""
import sys, os, json, argparse, collections


def main(argv=None):
    ap = argparse.ArgumentParser(description='관측 커버리지 요약')
    ap.add_argument('recdir')
    ap.add_argument('--window', default=None, help='정적 스캔 창 LO:HI (16진, 예 1D0000:200000)')
    ap.add_argument('--list', action='store_true', help='창 밖 주소를 전부 출력')
    a = ap.parse_args(argv)

    with open(os.path.join(a.recdir, '_coverage.json')) as f:
        cov = sorted(json.load(f))
    print('화면에 실제로 뜬 고유 ROM 타일 주소: %d개  (0x%06X ~ 0x%06X)'
          % (len(cov), cov[0], cov[-1]))

    per = collections.Counter(ad >> 16 for ad in cov)
    print('\n64KB 뱅크별 분포')
    for b in sorted(per):
        print('  0x%02X0000  %4d' % (b, per[b]))

    if a.window:
        lo, hi = (int(x, 16) for x in a.window.split(':'))
        out = [ad for ad in cov if not (lo <= ad < hi)]
        print('\n정적 스캔 창 0x%06X~0x%06X 밖: %d개 / %d개 (%.1f%%)'
              % (lo, hi, len(out), len(cov), 100.0 * len(out) / len(cov)))
        print('→ 이만큼이 정적 스캐너로는 원리적으로 안 보이는 타일이다.')
        if a.list:
            for i in range(0, len(out), 8):
                print('  ' + ' '.join('%06X' % ad for ad in out[i:i + 8]))

    print('\n화면별')
    for fn in sorted(os.listdir(a.recdir)):
        if not fn.endswith('.json') or fn.startswith('_'):
            continue
        with open(os.path.join(a.recdir, fn)) as f:
            r = json.load(f)
        v = set(r['slot2rom'].values())
        print('  %-14s 슬롯 %3d  고유 ROM 타일 %3d' % (r['name'], len(r['slot2rom']), len(v)))


if __name__ == '__main__':
    main()
