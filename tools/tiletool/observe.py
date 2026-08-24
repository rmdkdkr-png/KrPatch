#!/usr/bin/env python3
"""observe.py — 게임을 돌리며 화면별 타일 관측 기록을 남긴다. (에뮬레이터가 필요한 유일한 단계)

    python3 observe.py <롬.ngc> <출력폴더> [화면목록.json] [--sav-dir DIR] [--core PATH]

화면목록 형식:
    [{"name":"최종장타이틀", "sav":"pre_00.sav", "steps":[["B",120]]}, ...]
    steps 원소는 ["run", N] (N프레임 진행) 또는 ["버튼", N] (누르고 N프레임 진행).
    버튼: up down left right a b option

세이브스테이트는 저장소에 없다 — 각자 에뮬로 만들어 --sav-dir 에 둔다.
기록 1회면 이후 regress.py / ladder.py 는 에뮬 없이 돈다.
"""
import sys, os, json, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tilemap as TM


def make_harness(rom_path, core=None):
    """저장소의 ngp_harness(libretro beetle-ngp 직결)를 우선 쓰고, 구 ngp_state.NGP5 로 물러선다."""
    sys.path.insert(0, os.path.join(HERE, '..', '..', 'SS1_SamuraiShodown_NGP', 'emulator'))
    try:
        from ngp_harness import NGP, CORE
        return NGP(rom_path, core_path=core or CORE)
    except ImportError:
        from ngp_state import NGP5          # 구 세션 하네스가 PYTHONPATH 에 있을 때
        return NGP5(rom_path)


def run(rom_path, outdir, screens, sav_dir='', core=None):
    with open(rom_path, 'rb') as f:
        rom = f.read()
    idx = TM.rom_index(rom)
    cov = set()
    for s in screens:
        n = make_harness(rom_path, core)
        n.load_state(os.path.join(sav_dir, s['sav']) if sav_dir else s['sav'])
        n.run(2)
        for k, a in s['steps']:
            if k == 'run':
                n.run(a)
            else:
                n.press(k, 8)
                n.run(a)
        v = TM.dump_vram(n)
        maps, s2r = TM.observe(v, idx)
        TM.save_record(outdir, s['name'], maps, s2r)
        cov |= set(s2r.values())
        print('%-14s 슬롯 %3d  ROM타일 %3d' % (s['name'], len(s2r), len(set(s2r.values()))))
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, '_coverage.json'), 'w') as f:
        json.dump(sorted(cov), f)
    print('합집합 고유 ROM 타일 주소 %d개 -> %s/_coverage.json' % (len(cov), outdir))


def main(argv=None):
    ap = argparse.ArgumentParser(description='NGPC 화면 타일 관측 기록')
    ap.add_argument('rom')
    ap.add_argument('outdir')
    ap.add_argument('screens', nargs='?', default=os.path.join(HERE, 'screens_ss2.json'))
    ap.add_argument('--sav-dir', default='', help='세이브스테이트 폴더 (화면목록의 sav 앞에 붙는다)')
    ap.add_argument('--core', default=None, help='beetle-ngp libretro 코어 .so 경로')
    a = ap.parse_args(argv)
    with open(a.screens) as f:
        screens = json.load(f)
    run(a.rom, a.outdir, screens, a.sav_dir, a.core)


if __name__ == '__main__':
    main()
