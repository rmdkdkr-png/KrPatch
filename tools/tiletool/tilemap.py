#!/usr/bin/env python3
"""tilemap.py — NGPC 화면 타일 관측기 + 오프라인 시뮬레이터 코어.

용도
  1) 관측: 게임을 돌리며 각 화면의 VRAM을 떠서
     "이 화면에 실제로 뜬 ROM 타일 주소" 를 전부 기록한다.
     → 정적 아이템 스캐너가 놓치는 타일(스캔 창 밖 이주, 아이템 미경유 직접판독)까지 잡힌다.
  2) 시뮬레이터: 기록된 타일맵을 에뮬 없이 임의 ROM으로 다시 그린다.
     → 구판/신판 렌더를 픽셀 비교하면 회귀검사가 한 방에 끝난다.

실측 확정 (SS2, beetle-ngp)
  0x9000 SCR1 타일맵(32x32 u16) / 0x9800 SCR2 타일맵
  0xA000 타일 패턴 512장 x 16B (2bpp, 행당 u16, 상위비트부터)
  타일맵 엔트리: pattern = v & 0x1FF
  팔레트는 화면마다 뱅크가 달라 색 재현은 보조 기능. 회귀 비교는 회색조로 한다
  (같은 타일맵을 두 롬으로 그려 비교하므로 색은 결과에 영향 없음).

확정 방법: 이미 아는 정답(「괴제 강림」 보수용으로 0x1EF9C0에 심은 타일)이
VRAM 어느 슬롯에 올라갔는지 내용 대조로 찾고, 그 슬롯을 참조하는 타일맵
엔트리를 역추적해 비트필드를 역산했다.
"""
import struct, json, os
import numpy as np

SCR = {1: 0x9000, 2: 0x9800}
VRAM_BASE = 0x8000
VRAM_SIZE = 0x4000
TILE_BASE = 0xA000
NTILE = 512
PAT_MASK = 0x1FF
GRAY = np.array([(0, 0, 0), (255, 255, 255), (150, 150, 150), (70, 70, 70)], np.uint8)


def dump_vram(ngp):
    """하네스에서 VRAM 0x8000~0xBFFF 를 읽어 온다.

    ngp_harness.NGP 는 peek(addr, len), 구 ngp_state.NGP5 는 read(addr, len) 을 쓴다.
    """
    for meth in ('read', 'peek'):
        f = getattr(ngp, meth, None)
        if f is None:
            continue
        v = f(VRAM_BASE, VRAM_SIZE)
        if v and len(v) == VRAM_SIZE:
            return bytes(v)
    raise RuntimeError('하네스에 read/peek 가 없다 — 트레이싱 코어로 빌드했는지 확인')


def tile_table(vram):
    """VRAM 타일 패턴 512장 -> (512,8,8) 색인 배열."""
    T = np.zeros((NTILE, 8, 8), np.uint8)
    for s in range(NTILE):
        o = TILE_BASE - VRAM_BASE + s * 16
        for r in range(8):
            w = vram[o + r * 2] | (vram[o + r * 2 + 1] << 8)
            for c in range(8):
                T[s, r, c] = (w >> (14 - 2 * c)) & 3
    return T


def tile_raw(vram, s):
    o = TILE_BASE - VRAM_BASE + s * 16
    return bytes(vram[o:o + 16])


def rom_index(rom):
    """16B 타일 내용 -> ROM 주소. 같은 내용이면 가장 앞 주소를 쓴다."""
    idx = {}
    for a in range(0, len(rom) - 16, 2):
        idx.setdefault(rom[a:a + 16], a)
    return idx


def observe(vram, rom_idx):
    """이 화면이 쓰는 (VRAM슬롯 -> ROM주소) 지도와 평면별 타일맵을 뽑는다."""
    used = set()
    maps = {}
    for p, base in SCR.items():
        m = np.zeros((32, 32), np.uint16)
        for r in range(32):
            for c in range(32):
                v = struct.unpack_from('<H', vram, base - VRAM_BASE + (r * 32 + c) * 2)[0]
                m[r, c] = v
                used.add(v & PAT_MASK)
        maps[p] = m
    slot2rom = {}
    blank = b'\0' * 16
    for s in sorted(used):
        t = tile_raw(vram, s)
        if t == blank:
            continue
        a = rom_idx.get(t)
        if a is not None:            # ROM 원본이 아닌 런타임 생성 타일은 기록하지 않는다
            slot2rom[s] = a
    return maps, slot2rom


def render(maps, tiles, plane=None):
    """타일맵 + 타일표 -> 회색조 이미지(256x256). plane=None이면 두 평면을 가로로 붙인다."""
    def one(m):
        img = np.zeros((256, 256, 3), np.uint8)
        for r in range(32):
            for c in range(32):
                img[r * 8:r * 8 + 8, c * 8:c * 8 + 8] = GRAY[tiles[m[r, c] & PAT_MASK]]
        return img
    if plane:
        return one(maps[plane])
    a, b = one(maps[1]), one(maps[2])
    out = np.zeros((256, 512 + 8, 3), np.uint8)
    out[:, :256] = a
    out[:, 264:] = b
    return out


def tiles_from_rom(rom, slot2rom):
    """기록된 slot->ROM주소로 임의 롬에서 타일표를 재구성 (시뮬레이터의 핵심)."""
    T = np.zeros((NTILE, 8, 8), np.uint8)
    for s, a in slot2rom.items():
        raw = rom[a:a + 16]
        for r in range(8):
            w = raw[r * 2] | (raw[r * 2 + 1] << 8)
            for c in range(8):
                T[s, r, c] = (w >> (14 - 2 * c)) & 3
    return T


def save_record(path, name, maps, slot2rom):
    os.makedirs(path, exist_ok=True)
    rec = {'name': name,
           'scr1': maps[1].tolist(), 'scr2': maps[2].tolist(),
           'slot2rom': {str(k): v for k, v in slot2rom.items()}}
    with open(os.path.join(path, name + '.json'), 'w') as f:
        json.dump(rec, f)


def load_record(fp):
    with open(fp) as f:
        r = json.load(f)
    maps = {1: np.array(r['scr1'], np.uint16), 2: np.array(r['scr2'], np.uint16)}
    slot2rom = {int(k): v for k, v in r['slot2rom'].items()}
    return r['name'], maps, slot2rom


def load_records(recdir):
    """기록 폴더의 모든 화면을 [(name, maps, slot2rom), ...] 로. _coverage.json 은 건너뛴다."""
    import glob
    out = []
    for fp in sorted(glob.glob(os.path.join(recdir, '*.json'))):
        if os.path.basename(fp).startswith('_'):
            continue
        out.append(load_record(fp))
    return out
