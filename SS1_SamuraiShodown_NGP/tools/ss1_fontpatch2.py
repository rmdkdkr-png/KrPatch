#!/usr/bin/env python3
"""ss1_fontpatch2.py — SS1 대사 폰트 표 확장 (GPT 회신3 레이아웃)

원본 구조 (파일 오프셋):
  표 포인터  0x069968  →  표 베이스 0x08FD2B (CPU 0x28FD2B)
  표 항목    code 0x00~0x98 (153개, u16 상대오프셋) — **0x99 이후는 표가 아님**
  레코드     [u8 tile_cnt][tile_cnt×16B 타일][u8 row_cnt][타일인덱스…0xFF]
             code 0x00~0x94,0x98 = 1타일/1행 = 20B
             code 0x95 = 6타일/4행(182B), 0x96~0x97 = 2타일/2행(38B) → 프레임 예약, 보존
확장 레이아웃:
  새 표     0x1CBE45 (CPU 0x3CBE45), 항목 code 0x00~0xF7 (248개 = 0x1F0B)
  레코드    원본 상대 0x0132~0x0DEC 블록을 새 표 +0x0200 으로 복사 (새 오프셋 = 기존 + 0xCE)
  신규 슬롯 code 0x99~0xF7 → 새 표 +0x0F00 부터 20B 간격
슬롯↔코드 매핑 (예약 0x95~0x98 건너뜀):
  slot   0~122 → code 0x1A~0x94
  slot 123~217 → code 0x99~0xF7      (총 218칸)
"""
import sys, struct

PTR_AT  = 0x069968
OLD_T   = 0x08FD2B
NEW_T   = 0x1CBE45
REC_SRC_LO, REC_SRC_HI = 0x0132, 0x0DEC   # 원본 표 기준 레코드 블록 범위
SHIFT   = 0xCE                            # 새 오프셋 = 기존 + 0xCE (0x132+0xCE = 0x200)
EXT_OFF = 0x0F00                          # 신규 코드 레코드 시작(새 표 기준)
REC     = 20
RESERVED = (0x95, 0x96, 0x97, 0x98)


def code_of(slot):
    """슬롯 번호 → 스크립트 코드
    예약: 0x92(공백 글리프), 0x95~0x98(말풍선 프레임) 은 건너뛴다 → 총 217칸"""
    if slot < 120: return 0x1A + slot            # 0x1A~0x91
    if slot < 122: return 0x93 + (slot - 120)    # 0x93~0x94
    if slot < 217: return 0x99 + (slot - 122)    # 0x99~0xF7
    raise ValueError('슬롯 범위 초과: %d' % slot)


def rec_addr(rom, slot):
    """슬롯의 레코드 주소(파일)"""
    c = code_of(slot)
    if c <= 0x98:
        off = struct.unpack_from('<H', rom, NEW_T + c * 2)[0]
        return NEW_T + off
    return NEW_T + EXT_OFF + (c - 0x99) * REC


def patch(rom: bytearray):
    # 1) 새 표: 기존 항목(0x00~0x98) 오프셋 = 기존 + SHIFT
    for c in range(0x00, 0x99):
        off = struct.unpack_from('<H', rom, OLD_T + c * 2)[0]
        struct.pack_into('<H', rom, NEW_T + c * 2, off + SHIFT)
    # 2) 신규 항목(0x99~0xF7)
    for c in range(0x99, 0xF8):
        struct.pack_into('<H', rom, NEW_T + c * 2, EXT_OFF + (c - 0x99) * REC)
    # 3) 원본 레코드 블록 통째 복사 (가변길이 그대로 보존)
    n = REC_SRC_HI - REC_SRC_LO
    rom[NEW_T + 0x0200: NEW_T + 0x0200 + n] = rom[OLD_T + REC_SRC_LO: OLD_T + REC_SRC_HI]
    # 4) 신규 슬롯 영역을 빈 글리프로 초기화
    blank = _blank_record()
    for c in range(0x99, 0xF8):
        a = NEW_T + EXT_OFF + (c - 0x99) * REC
        rom[a:a + REC] = blank
    # 5) 표 포인터 교체 (상위 1바이트는 원본 유지)
    struct.pack_into('<I', rom, PTR_AT, (0x200000 + NEW_T) | (rom[PTR_AT + 3] << 24))
    return rom


def _blank_record():
    row = 0
    for k in range(8): row |= 3 << (14 - 2 * k)
    tile = bytes([row & 0xFF, row >> 8]) * 8
    return bytes([1]) + tile + bytes([1, 0, 0xFF])


def write_glyph(rom: bytearray, slot: int, bitmap):
    """8×8 비트맵(1=잉크) → 슬롯 레코드에 기록. 잉크=값1, 배경=값3"""
    a = rec_addr(rom, slot)
    rom[a] = 1
    for r in range(8):
        w = 0
        for k in range(8):
            w |= (1 if bitmap[r][k] else 3) << (14 - 2 * k)
        rom[a + 1 + r * 2] = w & 0xFF
        rom[a + 2 + r * 2] = w >> 8
    rom[a + 17] = 1
    rom[a + 18] = 0
    rom[a + 19] = 0xFF


if __name__ == '__main__':
    rom = bytearray(open(sys.argv[1], 'rb').read())
    patch(rom)
    open(sys.argv[2], 'wb').write(rom)
    print('표 확장 완료: 새 표 %s, 텍스트 슬롯 218칸 (예약 0x95~0x98 보존)' % hex(NEW_T))
