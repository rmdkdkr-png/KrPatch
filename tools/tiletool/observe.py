#!/usr/bin/env python3
"""observe.py — 게임을 돌리며 화면별 타일 관측 기록을 남긴다. (에뮬레이터가 필요한 유일한 단계)

    python3 observe.py <롬.ngc> <출력폴더> [화면목록.json] [옵션]

화면목록 항목은 둘 중 하나다.

  콜드부트 경로 (권장 — 저장소에 게임 데이터가 안 남는다)
    {"name":"타이틀메뉴", "route":[["run",2850],["a",60]]}

  세이브스테이트 (경로로 못 가는 화면용)
    {"name":"최종장타이틀", "sav":"pre_00.sav", "route":[["a",120]]}

route 원소: ["run", N] = N프레임 진행 / ["버튼", N] = 8프레임 누르고 N프레임 진행.
버튼 이름: up down left right a b option

    --sav-dir DIR      sav 항목을 찾을 폴더
    --dump-states DIR  화면마다 세이브스테이트를 떨궈 둔다 (로컬 편의용, 저장소에 넣지 말 것)
    --shots DIR        화면마다 실기 캡처 PNG (경로가 맞는지 눈으로 확인할 때)
    --core PATH        beetle-ngp libretro 코어 .so
"""
import sys, os, json, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tilemap as TM

DEFAULT_CORE = os.path.join(HERE, '..', '..', 'SS1_SamuraiShodown_NGP', 'emulator',
                            'beetle-ngp', 'mednafen_ngp_libretro.so')


def make_harness(rom_path, core=None):
    """저장소의 ngp_harness(libretro beetle-ngp 직결). 코어는 트레이싱 패치본이어야 peek 가 산다."""
    sys.path.insert(0, os.path.join(HERE, '..', '..', 'SS1_SamuraiShodown_NGP', 'emulator'))
    import ngp_harness
    core = core or os.environ.get('NGP_CORE') or DEFAULT_CORE
    return ngp_harness.NGP(rom_path, core_path=core)


def walk(n, route):
    for k, a in route:
        if k == 'run':
            n.run(a)
        else:
            n.press(k.lower(), 8)
            n.run(a)


def run(rom_path, outdir, screens, sav_dir='', core=None, dump_states=None, shots=None):
    with open(rom_path, 'rb') as f:
        rom = f.read()
    idx = TM.rom_index(rom)
    for s in screens:
        n = make_harness(rom_path, core)
        if s.get('sav'):
            n.load_state(os.path.join(sav_dir, s['sav']) if sav_dir else s['sav'])
            n.run(2)
        walk(n, s.get('route') or s.get('steps') or [])
        v = TM.dump_vram(n)
        maps, s2r = TM.observe(v, idx)
        TM.save_record(outdir, s['name'], maps, s2r, TM.scroll_of(v))
        if dump_states:
            os.makedirs(dump_states, exist_ok=True)
            n.save_state(os.path.join(dump_states, s['name'] + '.sav'))
        if shots:
            os.makedirs(shots, exist_ok=True)
            n.screenshot(os.path.join(shots, s['name'] + '.png'), scale=2)
        print('%-16s 슬롯 %3d  ROM타일 %3d' % (s['name'], len(s2r), len(set(s2r.values()))))
    # 커버리지는 이번 회차가 아니라 **폴더 전체**의 합집합으로 다시 센다.
    # 롬을 바꿔 가며(기본판/올카드판) 여러 번 돌려도 한 폴더에 누적된다.
    cov = set()
    nrec = 0
    for _, _, s2r in TM.load_records(outdir):
        cov |= set(s2r.values())
        nrec += 1
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, '_coverage.json'), 'w') as f:
        json.dump(sorted(cov), f)
    print('기록 %d화면 · 합집합 고유 ROM 타일 주소 %d개 -> %s/_coverage.json'
          % (nrec, len(cov), outdir))


def main(argv=None):
    ap = argparse.ArgumentParser(description='NGPC 화면 타일 관측 기록')
    ap.add_argument('rom')
    ap.add_argument('outdir')
    ap.add_argument('screens', nargs='?', default=os.path.join(HERE, 'screens_ss2.json'))
    ap.add_argument('--sav-dir', default='')
    ap.add_argument('--dump-states', default=None)
    ap.add_argument('--shots', default=None)
    ap.add_argument('--core', default=None)
    a = ap.parse_args(argv)
    with open(a.screens) as f:
        screens = json.load(f)
    run(a.rom, a.outdir, screens, a.sav_dir, a.core, a.dump_states, a.shots)


if __name__ == '__main__':
    main()
