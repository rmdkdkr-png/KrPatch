#!/usr/bin/env python3
"""hunt.py — 목표 화면이 뜰 때까지 게임을 굴려서 그 지점의 세이브스테이트를 잡는다.

    python3 hunt.py <롬.ngc> <목표기록.json> --out 목표.sav [--frames 200000]

조작 경로로 못 가는 화면(스토리 후반 등)이 있다. 손으로 세이브스테이트를 만드는 대신,
**이미 있는 기록을 정답표로 써서** 자동으로 찾는다.

원리: 목표 기록의 `slot2rom` 값 = 그 화면이 쓰는 ROM 타일 주소다.
게임을 굴리며 주기적으로 VRAM을 떠서, 지금 올라온 타일들의 ROM 주소가
목표 집합과 얼마나 겹치는지 본다. 임계값을 넘으면 그 화면이다.

정답표가 없는 새 게임이라면 `--tiles 주소,주소,...` 로 직접 넣어도 된다
(예: 한글화한 타일 주소를 넣고 "그 타일이 실제로 화면에 뜨는가"를 확인).
"""
import sys, os, json, argparse, random

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tilemap as TM
from observe import make_harness, walk

# 대전 게임에서 진행을 만들어 내는 최소 정책: 공격 섞어 누르며 전진
MASH = [('a', 6), ('b', 6), ('right', 6), ('a', 6), ('down', 4), ('b', 6), ('left', 4), ('a', 10)]


def vram_rom_addrs(vram, rom_idx):
    """지금 VRAM에 올라온 타일들의 ROM 주소 집합."""
    out = set()
    blank = b'\0' * 16
    for s in range(TM.NTILE):
        t = TM.tile_raw(vram, s)
        if t == blank:
            continue
        a = rom_idx.get(t)
        if a is not None:
            out.add(a)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description='목표 화면 자동 추적')
    ap.add_argument('rom')
    ap.add_argument('target', nargs='?', default=None, help='목표 기록 json (slot2rom을 정답표로 쓴다)')
    ap.add_argument('--tiles', default=None, help='정답표를 직접: 16진 ROM 주소 콤마 목록')
    ap.add_argument('--out', required=True, help='찾으면 저장할 세이브스테이트 경로')
    ap.add_argument('--shot', default=None, help='찾은 화면 PNG')
    ap.add_argument('--frames', type=int, default=200000, help='최대 진행 프레임')
    ap.add_argument('--check', type=int, default=120, help='몇 프레임마다 VRAM을 볼지')
    ap.add_argument('--hit', type=float, default=0.5, help='목표 타일 중 몇 할이 떠야 성공인지')
    ap.add_argument('--boot', type=int, default=2850, help='콜드부트 후 타이틀까지 프레임')
    ap.add_argument('--enter', default='a,a,a,a,a,a', help='타이틀에서 게임 시작까지 누를 버튼')
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--core', default=None)
    a = ap.parse_args(argv)

    if a.tiles:
        target = {int(x, 16) for x in a.tiles.replace(' ', '').split(',') if x}
    elif a.target:
        _, _, s2r = TM.load_record(a.target)
        target = set(s2r.values())
    else:
        ap.error('target 기록이나 --tiles 중 하나는 필요하다')

    with open(a.rom, 'rb') as f:
        rom = f.read()
    rom_idx = TM.rom_index(rom)

    rnd = random.Random(a.seed)
    n = make_harness(a.rom, a.core)
    n.run(a.boot)
    walk(n, [[b, 60] for b in a.enter.split(',') if b])

    best = 0.0
    done = 0
    while done < a.frames:
        for btn, hold in MASH:
            if rnd.random() < 0.25:
                btn = rnd.choice(['a', 'b', 'left', 'right', 'up', 'down'])
            n._held[btn] = hold
            n.run(hold + 2)
            done += hold + 2
        if done % a.check < 80:
            got = vram_rom_addrs(TM.dump_vram(n), rom_idx)
            score = len(got & target) / max(1, len(target))
            if score > best:
                best = score
                print('%7d프레임  적중 %.2f' % (done, score), flush=True)
            if score >= a.hit:
                n.save_state(a.out)
                if a.shot:
                    n.screenshot(a.shot, scale=2)
                print('찾음 — %d프레임, 적중 %.2f -> %s' % (done, score, a.out))
                return 0
    print('못 찾음 — %d프레임까지 최고 적중 %.2f' % (done, best))
    return 1


if __name__ == '__main__':
    sys.exit(main())
