#!/usr/bin/env python3
"""probe_names.py — SVC 캐릭터 이름판 스트립 시작 주소를 **관측으로** 확정한다.

    python3 probe_names.py <SVC.ngc> [--boot 1300] [--enter 5] [--out 결과.json]

## 왜 관측인가

이름풀을 앞에서부터 폭을 세어 걸어가면 빈칸 되짚기가 한 칸 과해져 시작 주소가
`0x10` 씩 밀린다. 화면에 뜬 것을 그대로 읽으면 그 오차가 원천적으로 없다.

## 방법

1. 이름판은 타일맵 SCR1 **행13~14 × 열5~14**(10칸 × 2줄)에 뜬다
2. 그 20칸이 쓰는 VRAM 슬롯 중 **가장 긴 연속 구간**이 이름 스트립이다
   (게임이 스트립을 연속 슬롯에 통째로 올린다)
3. 각 슬롯의 16바이트를 롬에서 찾되 **유일하게 일치할 때만** 인정한다
4. 유일 매치들이 모두 `start + i*16` 을 만족하면(정합 O) 그 start 가 답이다

좁은 이름판은 **가운데 정렬**이라 화면 칸 위치로 역산하면 안 된다 — 슬롯 순서로 푼다.
칸 위치로 풀면 정렬 여백만큼 밀린 값이 나온다 (KYO 가 `0x32AB20` 으로 나오던 이유).

커서 이동은 한 번에 모든 칸에 안 닿는다. 회차마다 닿는 칸이 다르니
**여러 번 돌려 합집합**을 쓴다. `--out` 결과를 모아 병합하면 된다.
"""
import sys, os, json, struct, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tiletool'))
import tilemap as TM
import numpy as np

PLATE_ROWS = (13, 14)
PLATE_COLS = range(5, 15)


def plate_cells(vram):
    out = []
    for r in PLATE_ROWS:
        row = []
        for c in PLATE_COLS:
            v = struct.unpack_from('<H', vram, 0x9000 - 0x8000 + (r * 32 + c) * 2)[0]
            row.append(v & TM.PAT_MASK)
        out.append(row)
    return out


def unique_addr(rom, tile):
    """롬 전체에서 유일하게 일치할 때만 주소를 인정한다."""
    j = rom.find(tile)
    if j < 0 or rom.find(tile, j + 1) >= 0:
        return None
    return j


def solve(rom, vram):
    cells = plate_cells(vram)
    slots = sorted(set(cells[0] + cells[1]))
    runs, cur = [], [slots[0]]
    for s in slots[1:]:
        if s == cur[-1] + 1:
            cur.append(s)
        else:
            runs.append(cur)
            cur = [s]
    runs.append(cur)
    run = max(runs, key=len)
    known = []
    for i, s in enumerate(run):
        a = unique_addr(rom, TM.tile_raw(vram, s))
        if a is not None:
            known.append((i, a))
    if not known:
        return None
    i0, a0 = known[0]
    start = a0 - i0 * 16
    ok = all(a == start + i * 16 for i, a in known)
    return {'start': start, 'slots': len(run), 'width': len(run) // 2,
            'matched': len(known), 'consistent': ok, 'key': tuple(cells[0] + cells[1])}


def main(argv=None):
    ap = argparse.ArgumentParser(description='SVC 이름판 주소 관측')
    ap.add_argument('rom')
    ap.add_argument('--boot', type=int, default=1300, help='콜드부트 후 타이틀까지 프레임')
    ap.add_argument('--enter', type=int, default=5, help='타이틀에서 캐릭터 선택까지 A 누르는 횟수')
    ap.add_argument('--core', default=None)
    ap.add_argument('--out', default=None)
    a = ap.parse_args(argv)

    sys.path.insert(0, os.path.join(HERE, '..', 'tiletool'))
    from observe import make_harness
    with open(a.rom, 'rb') as f:
        rom = f.read()
    n = make_harness(a.rom, a.core)
    n.run(a.boot)
    for _ in range(a.enter):
        n.press('a', 8)
        n.run(70)
    for _ in range(9):
        n.press('up', 6)
        n.run(6)
    for _ in range(9):
        n.press('left', 6)
        n.run(6)
    n.run(30)

    moves = [None]
    for _ in range(10):
        for _ in range(9):
            moves += ['down', None]
        moves += ['right', None]
    for _ in range(6):
        for _ in range(9):
            moves += ['up', None]
        moves += ['left', None]

    seen, res = set(), []
    for mv in moves:
        if mv:
            n.press(mv, 6)
            n.run(14)
            continue
        r = solve(rom, TM.dump_vram(n))
        if r is None or r['key'] in seen:
            continue
        seen.add(r['key'])
        r.pop('key')
        res.append(r)

    print('서로 다른 이름판 %d개' % len(res))
    print('%-10s %-6s %-4s %-8s %s' % ('시작', '슬롯수', '폭', '유일매치', '정합'))
    for r in sorted(res, key=lambda x: x['start']):
        print('  0x%06X  %-5d  %-3d  %-7d  %s'
              % (r['start'], r['slots'], r['width'], r['matched'],
                 'O' if r['consistent'] else 'X'))
    if a.out:
        with open(a.out, 'w') as f:
            json.dump(sorted(res, key=lambda x: x['start']), f, indent=1)
        print('-> %s' % a.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
