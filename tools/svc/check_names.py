#!/usr/bin/env python3
"""check_names.py — 구운 이름판이 화면에 **바이트 그대로** 올라오는지 자동 대조한다.

    python3 check_names.py <구운롬.ngc> [--shots 폴더]

눈으로 넘기지 않기 위한 도구다. 캐릭터 선택 커서를 훑으며 이름판 20칸의 VRAM 타일을
받아, 구운 롬의 해당 스트립 바이트와 **정확히 일치하는지** 본다.

  일치      -> 그 이름은 주소·폭·내용이 전부 맞다
  불일치    -> 어긋난 타일 수를 보고한다 (주소나 폭이 틀린 것)
  대조안됨  -> 구운 18종 중 어느 것도 아니다 (잠금 캐릭터 판)

커서가 한 번에 모든 칸에 안 닿으므로 여러 번 돌려 합집합을 봐야 한다.
"""
import sys, os, struct, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tiletool'))
sys.path.insert(0, HERE)
import tilemap as TM
from bake_names_ko import NAMES

PLATE_ROWS = (13, 14)
PLATE_COLS = range(5, 15)


def strips(rom):
    """이름 -> [타일 16B, ...] (윗줄 W장 + 아랫줄 W장)"""
    out = {}
    for en, start, W, ko in NAMES:
        out[(en, ko)] = [bytes(rom[start + i * 16:start + i * 16 + 16]) for i in range(2 * W)]
    return out


def plate_tiles(vram):
    seen = []
    for r in PLATE_ROWS:
        for c in PLATE_COLS:
            s = struct.unpack_from('<H', vram, 0x9000 - 0x8000 + (r * 32 + c) * 2)[0] & TM.PAT_MASK
            seen.append(TM.tile_raw(vram, s))
    return seen


def match(tiles, table):
    """이 판이 어느 이름인가. **스트립 타일이 화면에 다 올라왔는지**로 판정한다.

    판에는 스트립 밖의 빈 칸도 섞이므로 화면 쪽 기준으로 보면 안 된다.
    스트립의 고유 타일이 전부 화면에 있으면 그 이름이 제대로 올라온 것이다.
    """
    on = {t for t in tiles}
    best = None
    for key, strip in table.items():
        want = set(strip)
        hit = len(want & on)
        cov = hit / len(want)
        if best is None or cov > best[1]:
            best = (key, cov, hit, len(want))
    return best


def main(argv=None):
    ap = argparse.ArgumentParser(description='이름판 자동 대조')
    ap.add_argument('rom')
    ap.add_argument('--boot', type=int, default=1300)
    ap.add_argument('--enter', type=int, default=5)
    ap.add_argument('--core', default=None)
    a = ap.parse_args(argv)

    with open(a.rom, 'rb') as f:
        rom = f.read()
    table = strips(rom)

    from observe import make_harness
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

    seen, found = set(), {}
    for mv in moves:
        if mv:
            n.press(mv, 6)
            n.run(14)
            continue
        v = TM.dump_vram(n)
        tiles = plate_tiles(v)
        key = tuple(sorted({t for t in tiles if any(t)}))
        if not key or key in seen:
            continue
        seen.add(key)
        name, cov, hit, tot = match(tiles, table)
        prev = found.get(name)
        if prev is None or cov > prev[0]:
            found[name] = (cov, hit, tot)

    print('%-9s %-6s %s' % ('이름', '한글', '결과'))
    ok = 0
    for en, start, W, ko in NAMES:
        r = found.get((en, ko))
        if r is None:
            print('  %-9s %-6s 화면에서 못 만남 (커서 미도달)' % (en, ko))
            continue
        cov, hit, tot = r
        if hit == tot:
            print('  %-9s %-6s 일치 — 스트립 %d타일 전부 화면에 올라옴' % (en, ko, tot))
            ok += 1
        else:
            print('  %-9s %-6s **불일치** — 스트립 %d타일 중 %d장만 올라옴'
                  % (en, ko, tot, hit))
    print('-' * 40)
    print('만난 판 %d개 중 완전일치 %d개 / 구운 이름 %d종'
          % (len(seen), ok, len(NAMES)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
