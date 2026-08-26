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
    """주소(열) = A + 열*16 의 A 를 **다수결로** 고른다. (A, 지지한 칸 수, 벗어난 칸 수)

    전부 한 직선에 있어야 한다고 요구했더니 판 셋을 통째로 버렸다.
    여백 타일이 우연히 유일 매치가 되는 자리가 있어서, 그런 칸 하나가 끼면
    멀쩡한 판도 못 풀린 것으로 나온다. 가장 많은 칸이 지지하는 A 를 쓰고
    벗어난 칸은 세어서 돌려준다 — 벗어난 칸이 많으면 그건 진짜 이상한 판이다.
    """
    if len(cells) < 2:
        return None, len(cells), 0
    g = defaultdict(list)
    for c, a in cells.items():
        g[a - c * 16].append(c)
    A, cs = max(g.items(), key=lambda t: (len(t[1]), -t[0]))
    if len(cs) < 2:
        return None, len(cells), 0
    return A, len(cs), len(cells) - len(cs)


def groups(cells):
    """A 값별로 열을 묶는다. {A: [열, ...]}

    판 하나가 **한 직선으로 안 풀리는** 경우를 버리지 않고 들여다보기 위한 것이다.
    FELICIA 를 재 보니 한 판 안에서 기준이 중간에 한 타일 어긋나 있었다.
    """
    g = defaultdict(list)
    for c, a in cells.items():
        g[a - c * 16].append(c)
    return {A: sorted(cs) for A, cs in g.items()}


def diagnose(rom, vram):
    """직선으로 안 풀리는 판을 뜯어본다. 어디서 어긋났는지 돌려준다."""
    p = read_plate(rom, vram)
    out = {}
    for r in PLATE_ROWS:
        g = groups(p[r])
        # 유일매치가 하나뿐인 A 는 우연히 유일해진 여백일 수 있으니 표시만 해 둔다
        out[r] = sorted(((A, cs) for A, cs in g.items()),
                        key=lambda t: (-len(t[1]), t[0]))
    return out


def solve(rom, vram, max_outlier=2):
    p = read_plate(rom, vram)
    top, nt, ot = fit(p[PLATE_ROWS[0]])
    bot, nb, ob = fit(p[PLATE_ROWS[1]])
    if top is None or bot is None:
        return None
    if ot + ob > max_outlier:
        return None            # 벗어난 칸이 많다 — 판 안에서 기준이 갈린 진짜 이상한 판
    W, rem = divmod(bot - top, 16)
    if rem or not (1 <= W <= 16):
        return None
    # **시작 주소는 "유일매치가 있는 첫 칸"으로 잡으면 안 된다.** 여백 타일은 여러 이름이
    # 공유해 매치에서 걸러지므로, 그 칸은 판의 왼쪽 끝보다 안쪽이다. 그렇게 재면 시작이
    # 한두 칸씩 밀린 값이 나온다 (13종 전부 +0x10~0x30 씩 밀려 나왔다).
    # 맞춘 직선 A 만 들고 나가고, 시작은 판의 첫 칸을 아는 쪽에서 A + 첫칸*16 로 구한다.
    return {'top': top, 'bot': bot, 'W': W, 'matched': nt + nb,
            'first': min(p[PLATE_ROWS[0]])}


def sweep(rom_path, rom, core, boot, enter, dry=160, cap=3000, verbose=False):
    """커서를 몰고 다니며 이름판을 모은다. **새 판이 안 나올 때까지** 돈다.

    고정 경로(아래 9번 × 오른쪽 …)로는 5종을 못 만났다. 캐릭터 칸이 좌우 두 무리로
    갈려 있고 아래쪽에 따로 한 줄이 더 있어서, 격자 모양을 미리 안다고 가정하면 빠진다.

    그래서 모양을 가정하지 않는다. 네 방향을 길이를 바꿔 가며 훑되,
    **새 판이 `dry` 번 연속으로 안 나오면** 다 돌았다고 보고 멈춘다.
    """
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

    found = {}
    odd = {}
    since = steps = 0

    def look():
        nonlocal since
        v = TM.dump_vram(n)
        r = solve(rom, v)
        if r is None:
            since += 1
            # 직선으로 안 풀린 판은 버리지 않고 모아 둔다 — 여기가 보류 4종의 단서다
            d = diagnose(rom, v)
            best = max((A for row in d.values() for A, cs in row if len(cs) >= 2),
                       default=None)
            if best is not None:
                key = min(A for row in d.values() for A, cs in row if len(cs) >= 2)
                if key not in odd:
                    odd[key] = d
            return
        prev = found.get(r['top'])
        if prev is None:
            since = 0
            found[r['top']] = r
            if verbose:
                print('   %d걸음: 새 판 0x%06X W%d' % (steps, r['top'], r['W']))
        else:
            since += 1
            if r['matched'] > prev['matched']:
                found[r['top']] = r

    look()
    # 길이를 바꿔 가며 네 방향을 도는 결정적 순회. 좌우 무리와 아래 줄을 모두 지난다.
    plan = []
    for run in (1, 2, 3, 5, 8, 13):
        for d in ('down', 'right', 'up', 'right', 'down', 'left', 'up', 'left'):
            plan += [d] * run
    while since < dry and steps < cap:
        for mv in plan:
            n.press(mv, 6)
            n.run(14)
            steps += 1
            look()
            if since >= dry or steps >= cap:
                break
    return found, odd


def main(argv=None):
    ap = argparse.ArgumentParser(description='이름판 주소 측정·대조')
    ap.add_argument('rom')
    ap.add_argument('--core', default=None)
    ap.add_argument('--boot', type=int, default=1300)
    ap.add_argument('--enter', type=int, default=5)
    ap.add_argument('--table', default=os.path.join(HERE, 'names_table.json'))
    ap.add_argument('--dry', type=int, default=160,
                    help='새 판이 이만큼 연속으로 안 나오면 다 돈 것으로 본다')
    ap.add_argument('--cap', type=int, default=3000, help='최대 커서 이동 수')
    ap.add_argument('--verbose', action='store_true')
    ap.add_argument('--dump', action='store_true', help='측정값만 출력하고 대조는 안 한다')
    a = ap.parse_args(argv)

    with open(a.rom, 'rb') as f:
        rom = f.read()
    found, odd = sweep(a.rom, rom, a.core, a.boot, a.enter, a.dry, a.cap, a.verbose)

    print('화면에서 잰 이름판 %d개' % len(found))
    print('  %-10s %-4s %-8s %s' % ('윗줄A', 'W', '유일매치', '가장왼쪽 매치'))
    for A in sorted(found):
        r = found[A]
        print('  0x%06X  %-3d  %-7d  x%d' % (A, r['W'], r['matched'], r['first']))

    if odd:
        print('\n직선 하나로 안 풀린 판 %d개 — **한 판 안에서 기준이 어긋난다**' % len(odd))
        for key in sorted(odd):
            print('  0x%06X 근처' % key)
            for r in PLATE_ROWS:
                for A, cs in odd[key][r]:
                    if len(cs) < 2:
                        continue
                    print('     행%d  A=0x%06X  열 %s' % (r, A, cs))

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
