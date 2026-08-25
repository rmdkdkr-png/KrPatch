#!/usr/bin/env python3
"""check_names.py — 이름판 스트립 주소를 **화면에서 역추적해 측정하고** 표와 대조한다.

    python3 check_names.py <롬.ngc> [--core libretro.so] [--table 표.json] [--dump]

## 왜 다시 짰나

예전 판정은 "스트립의 타일이 화면에 다 올라왔는가"를 봤다. 그 기준은 **틀렸다.**
18종 전부 통과를 찍었는데, 실제로는 6종의 주소·폭이 어긋나 있었다.

원인은 이 포맷의 함정이다. **같은 W로 창을 옆으로 밀어도 글자는 똑같이 멀쩡해 보인다.**
윗줄·아랫줄 간격이 W로 고정돼 있어서 시작점을 한두 칸 틀려도 렌더가 깨끗하게 나온다.
여백 타일로 경계를 잡는 것도 안 된다 — 아랫줄 꼬리 여백에 윗줄용 타일이 섞인 자리가 있다.

그래서 "깨끗해 보이는가"를 묻지 않고 **주소를 직접 잰다.**

## 재는 법

캐릭터를 띄운 상태에서 이름판 칸(SCR1 행13·14)마다,

1. 타일맵에서 타일 번호를 읽고
2. VRAM `0xA000 + (번호 & 0x1FF)*16` 에서 패턴 16바이트를 꺼내
3. 그 패턴을 이름풀 `0x32A800~0x32C900` 에서 찾는다 — **유일 매치만 믿는다**
   (여백 타일은 여러 이름이 공유해 매치가 여러 개 나온다. 반드시 버린다)
4. 유일 매치들로 직선을 맞춘다: `주소(열) = A + 열*16`. 윗줄·아랫줄 각각
5. **W = (아랫줄 A − 윗줄 A) / 16**, 시작 = 윗줄 A + 첫칸*16

직선에서 벗어나는 매치가 하나라도 있으면 그 판은 신뢰하지 않는다.

## 무엇이 실패인가

    표에 없는 주소가 나왔다        표가 틀렸다
    직선이 안 맞는다              여백을 유일 매치로 잘못 믿었거나 화면 구조가 다르다
    한 칸도 유일 매치가 없다       커서가 그 판에 안 닿았다 (실패가 아니라 표본 부족)
"""
import sys, os, json, struct, argparse
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tiletool'))
sys.path.insert(0, HERE)
import tilemap as TM

POOL_LO, POOL_HI = 0x32A800, 0x32C900
PLATE_ROWS = (13, 14)
PLATE_COLS = range(3, 17)


def unique_in_pool(rom, tile):
    """이름풀 안에서 **유일하게** 일치할 때만 주소를 인정한다."""
    j = rom.find(tile, POOL_LO, POOL_HI)
    if j < 0 or rom.find(tile, j + 1, POOL_HI) >= 0:
        return None
    return j


def read_plate(rom, vram):
    """이름판 칸 -> ROM 주소 (유일 매치만). {행: {열: 주소}}"""
    out = {r: {} for r in PLATE_ROWS}
    for r in PLATE_ROWS:
        for c in PLATE_COLS:
            s = struct.unpack_from('<H', vram, 0x9000 - 0x8000 + (r * 32 + c) * 2)[0]
            a = unique_in_pool(rom, TM.tile_raw(vram, s & TM.PAT_MASK))
            if a is not None:
                out[r][c] = a
    return out


def fit(cells):
    """주소(열) = A + 열*16 의 A. 어긋나면 None."""
    if len(cells) < 2:
        return None, len(cells)
    As = {a - c * 16 for c, a in cells.items()}
    if len(As) != 1:
        return None, len(cells)
    return As.pop(), len(cells)


def solve(rom, vram):
    p = read_plate(rom, vram)
    top, nt = fit(p[PLATE_ROWS[0]])
    bot, nb = fit(p[PLATE_ROWS[1]])
    if top is None or bot is None:
        return None
    W, rem = divmod(bot - top, 16)
    if rem or not (1 <= W <= 16):
        return None
    # **시작 주소는 "유일매치가 있는 첫 칸"으로 잡으면 안 된다.** 여백 타일은 여러 이름이
    # 공유해 매치에서 걸러지므로, 그 칸은 판의 왼쪽 끝보다 안쪽이다. 그렇게 재면 시작이
    # 한두 칸씩 밀린 값이 나온다 (13종 전부 +0x10~0x30 씩 밀려 나왔다).
    # 맞춘 직선 A 만 들고 나가고, 시작은 판의 첫 칸을 아는 쪽에서 A + 첫칸*16 로 구한다.
    return {'top': top, 'bot': bot, 'W': W, 'matched': nt + nb,
            'first': min(p[PLATE_ROWS[0]])}


def sweep(rom_path, rom, core, boot, enter):
    from observe import make_harness
    n = make_harness(rom_path, core)
    n.run(boot)
    for _ in range(enter):
        n.press('a', 8)
        n.run(70)
    for _ in range(9):
        n.press('up', 6); n.run(6)
    for _ in range(9):
        n.press('left', 6); n.run(6)
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

    found = {}
    for mv in moves:
        if mv:
            n.press(mv, 6); n.run(14)
            continue
        r = solve(rom, TM.dump_vram(n))
        if r is None:
            continue
        prev = found.get(r['top'])
        if prev is None or r['matched'] > prev['matched']:
            found[r['top']] = r
    return found


def main(argv=None):
    ap = argparse.ArgumentParser(description='이름판 주소 측정·대조')
    ap.add_argument('rom')
    ap.add_argument('--core', default=None)
    ap.add_argument('--boot', type=int, default=1300)
    ap.add_argument('--enter', type=int, default=5)
    ap.add_argument('--table', default=os.path.join(HERE, 'names_table.json'))
    ap.add_argument('--dump', action='store_true', help='측정값만 출력하고 대조는 안 한다')
    a = ap.parse_args(argv)

    with open(a.rom, 'rb') as f:
        rom = f.read()
    found = sweep(a.rom, rom, a.core, a.boot, a.enter)

    print('화면에서 잰 이름판 %d개' % len(found))
    print('  %-10s %-4s %-8s %s' % ('윗줄A', 'W', '유일매치', '가장왼쪽 매치'))
    for A in sorted(found):
        r = found[A]
        print('  0x%06X  %-3d  %-7d  x%d' % (A, r['W'], r['matched'], r['first']))

    if a.dump or not os.path.exists(a.table):
        if not a.dump:
            print('\n대조표 %s 가 없다 — 측정만 했다' % a.table)
        return 0

    table = json.load(open(a.table))
    print('\n%-10s %-7s %-14s %s' % ('이름', '한글', '표(시작/W)', '판정'))
    ok = miss = bad = 0
    for e in table:
        st, W, col = int(e['start'], 16), e['W'], e['col']
        # 표의 시작·첫칸이 맞다면 윗줄 직선은 A = 시작 - 첫칸*16 이어야 한다
        A = st - col * 16
        r = found.get(A)
        if r is None:
            near = sorted(found, key=lambda f: abs(f - A))
            if near and abs(near[0] - A) <= 0x60:
                f0 = found[near[0]]
                implied = near[0] + col * 16
                print('  %-10s %-7s 0x%06X/W%-2d **어긋남** — 화면 직선이면 시작 0x%06X '
                      '(첫칸을 x%d 로 보면 표와 맞는다)'
                      % (e['name'], e.get('ko', ''), st, W, implied,
                         (st - near[0]) // 16))
                bad += 1
            else:
                print('  %-10s %-7s 0x%06X/W%-2d 못 만남 (커서 미도달)'
                      % (e['name'], e.get('ko', ''), st, W))
                miss += 1
            continue
        if r['W'] != W:
            print('  %-10s %-7s 0x%06X/W%-2d **폭 어긋남** — 화면은 W%d'
                  % (e['name'], e.get('ko', ''), st, W, r['W']))
            bad += 1
            continue
        print('  %-10s %-7s 0x%06X/W%-2d 일치 (유일매치 %d칸) %s'
              % (e['name'], e.get('ko', ''), st, W, r['matched'],
                 '' if e.get('state') != '보류' else '[보류 — 영문 유지]'))
        ok += 1
    print('-' * 62)
    print('주소·폭 일치 %d / 어긋남 %d / 커서 미도달 %d  (표 %d종)'
          % (ok, bad, miss, len(table)))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
