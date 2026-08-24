#!/usr/bin/env python3
"""diffmap.py — 화면에 뜬 타일 중 **아직 원본 그대로인 것**을 가려낸다.

    python3 diffmap.py <기록폴더> <원본.ngc> <한글판.ngc> [출력폴더] [--csv 목록.csv]

판정은 **내용**으로 한다. 한글판 화면에 뜬 타일의 16바이트가

  원본 롬 어디에도 없다  → 새로 그린 타일 (한글화됨)
  원본 롬에 있다         → 원본 타일 — 그림이거나, **아직 일본어/영문으로 남은 글자**다

주소로 비교하지 않는 이유: 같은 16바이트가 롬 곳곳에 중복되면 기록된 주소가
실제 출처가 아닐 수 있다. 내용 판정은 그 모호함을 안 탄다.

출력 이미지는 한글판 화면을 그리되 **원본 그대로인 타일만 밝게** 칠한다.
번역 잔여물이 그 화면 어디에 남았는지 한 장으로 보인다.
`--csv`로 화면별 잔여 타일 목록을 뽑아 작업 목록으로 쓴다.
"""
import sys, os, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tilemap as TM
import numpy as np

KEEP = np.array([(0, 0, 0), (255, 240, 120), (170, 150, 60), (80, 70, 30)], np.uint8)   # 원본 그대로
DONE = np.array([(0, 0, 0), (60, 60, 60), (40, 40, 40), (25, 25, 25)], np.uint8)        # 새로 그린 타일


def content_set(rom):
    """롬에 존재하는 16바이트 창(2바이트 정렬) 전부를 해시 집합으로."""
    import hashlib
    seen = set()
    for a in range(0, len(rom) - 16, 2):
        seen.add(hash(rom[a:a + 16]))
    return seen


def render_split(maps, tiles, untouched_slots, plane=1):
    """한 평면을 그리되, 원본 그대로인 슬롯만 밝게."""
    m = maps[plane]
    img = np.zeros((256, 256, 3), np.uint8)
    for r in range(32):
        for c in range(32):
            s = int(m[r, c]) & TM.PAT_MASK
            pal = KEEP if s in untouched_slots else DONE
            img[r * 8:r * 8 + 8, c * 8:c * 8 + 8] = pal[tiles[s]]
    return img


def main(argv=None):
    ap = argparse.ArgumentParser(description='원본 잔여 타일 지도')
    ap.add_argument('recdir')
    ap.add_argument('orig')
    ap.add_argument('kr')
    ap.add_argument('outdir', nargs='?', default=None)
    ap.add_argument('--plane', type=int, choices=(0, 1, 2), default=1, help='0이면 두 평면 모두')
    ap.add_argument('--csv', default=None)
    ap.add_argument('--lines', default=None,
                    help='원본 잔여 타일이 **화면에서 가로로 이어진 줄**을 그림으로 뽑는다 (작업 목록)')
    ap.add_argument('--min-run', type=int, default=3, help='줄로 뽑을 최소 타일 수')
    a = ap.parse_args(argv)

    with open(a.orig, 'rb') as f:
        O = f.read()
    with open(a.kr, 'rb') as f:
        K = f.read()
    print('원본 롬 내용 색인 만드는 중 (%.1fMB)...' % (len(O) / 1048576.0), flush=True)
    orig_content = content_set(O)

    rows = []
    tot_keep = set()
    tot_all = set()
    print('%-14s %6s %6s %6s' % ('화면', '타일', '새타일', '원본잔여'))
    for name, maps, s2r in TM.load_records(a.recdir):
        untouched, newly = set(), set()
        for s, ad in s2r.items():
            raw = K[ad:ad + 16]
            (untouched if hash(raw) in orig_content else newly).add(s)
        tot_all |= set(s2r.values())
        tot_keep |= {s2r[s] for s in untouched}
        print('%-14s %6d %6d %6d' % (name, len(s2r), len(newly), len(untouched)))
        for s in sorted(untouched):
            rows.append((name, s, s2r[s]))
        if a.outdir:
            from PIL import Image
            os.makedirs(a.outdir, exist_ok=True)
            tiles = TM.tiles_from_rom(K, s2r)
            Image.fromarray(render_split(maps, tiles, untouched, a.plane)).save(
                os.path.join(a.outdir, name + '.png'))

    print('-' * 36)
    print('%-14s %6d %6d %6d' % ('합계(고유)', len(tot_all), len(tot_all) - len(tot_keep), len(tot_keep)))

    if a.lines:
        from PIL import Image
        os.makedirs(a.lines, exist_ok=True)
        blank = b'\0' * 16
        found = []
        for name, maps, s2r in TM.load_records(a.recdir):
            untouched = {s for s, ad in s2r.items()
                         if hash(K[ad:ad + 16]) in orig_content
                         and K[ad:ad + 16] != blank}
            tiles = TM.tiles_from_rom(K, s2r)
            planes = (1, 2) if a.plane == 0 else (a.plane,)
            for plane in planes:
                m = maps[plane]
                for r in range(32):
                    run = []
                    for c in range(33):
                        s = int(m[r, c]) & TM.PAT_MASK if c < 32 else -1
                        if s in untouched:
                            run.append(s)
                            continue
                        # 32칸 통줄이나 같은 타일 반복은 배경 채움이라 글자가 아니다
                        if a.min_run <= len(run) < 32 and len(set(run)) >= 3:
                            found.append((name, plane, r, c - len(run), run,
                                          tiles, [s2r[x] for x in run]))
                        run = []
        found.sort(key=lambda t: -len(t[4]))
        print('\n화면에서 가로 %d타일 이상 이어진 원본 잔여 줄 %d개 -> %s'
              % (a.min_run, len(found), a.lines))
        for i, (name, plane, r, c0, run, tiles, ads) in enumerate(found):
            img = np.zeros((8, 8 * len(run), 3), np.uint8)
            for j, s in enumerate(run):
                img[:, j * 8:j * 8 + 8] = TM.GRAY[tiles[s]]
            Image.fromarray(img).save(os.path.join(
                a.lines, '%03d_%s_p%d_r%02d_x%d.png' % (i, name, plane, r, len(run))))
        for name, plane, r, c0, run, _, ads in found[:15]:
            print('  %-12s SCR%d 행%2d 열%2d  %2d타일  0x%06X~0x%06X'
                  % (name, plane, r, c0, len(run), min(ads), max(ads)))
    if a.csv:
        with open(a.csv, 'w') as f:
            f.write('screen,slot,rom_addr\n')
            for n, s, ad in rows:
                f.write('%s,%d,0x%06X\n' % (n, s, ad))
        print('잔여 타일 목록 -> %s (%d행)' % (a.csv, len(rows)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
