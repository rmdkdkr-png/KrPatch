# -*- coding: utf-8 -*-
"""gfx8.py — 시스템(ASCII 8×8) 폰트 탈취 + UI 문자열 한글화  [H 항목]

배경 (이 세션에서 실측 확정):
  · 메뉴·타이틀 ASCII 텍스트의 폰트는 카트리지가 아니라 **콘솔 BIOS 폰트**다.
    게임이 시스콜 VECT_SYSFONTSET(벡터표 슬롯 5)을 부르면 BIOS가 1bpp 폰트
    0x800B를 2bpp로 펼쳐 VRAM 타일 0x00~0x7F(0xA000~0xAFFF)에 올린다.
    1bpp→2bpp 변환 업로드라서 롬·에뮬 어디에도 2bpp 원본이 없었던 것 (= "압축"의 정체).
  · 게임의 시스콜 경로: 디스패처(파일 0x230C8~)가 벡터표 0xFFFE00 + slot*4 를 읽어 CALL.
    디스패처의 벡터표 베이스 즉치값은 파일 0x230D1 (LD Xrr,0x00FFFE00 의 imm32).

패치:
  1. 벡터표 사본을 자유영역에 두고 슬롯5만 우리 스텁으로 교체, 디스패처 베이스만 재지정.
  2. 스텁(TLCS-900h 22바이트, 손 어셈블): 자유영역의 2bpp 폰트 0x1000B를 0xA000에 LDIRW.
  3. 폰트 블록 = BIOS 폰트 복제 + 한글 음절(Galmuri7)을 빈 코드에 배치.
  4. UI 문자열을 그 코드로 재작성 (ss1_ui 의 검증된 방식 재사용).

코드 예산 (50칸 — A~Z·0~9·공백과 미번역 문자열이 쓰는 ! " & ' ( ) - . © 는 불가침):
"""
import sys
sys.path.insert(0, '/root/ss2_work')
import ss1_ui

# ── 배치 (자유영역 0x1CD4B0~0x200000 안) ──
VECTAB = 0x1D0000            # 벡터표 27×4B
STUB   = 0x1D0100            # 스텁 코드
FONT   = 0x1D0200            # 2bpp 폰트 0x1000B (타일 0x00~0x7F)
DISP_IMM = 0x230D1           # 디스패처의 벡터표 베이스 imm32

BIOS_VEC = [0xFF27A2,0xFF1030,0xFF1440,0xFF12B4,0xFF1222,0xFF8D8A,0xFF6FD8,0xFF7042,
            0xFF7082,0xFF149B,0xFF1033,0xFF1487,0xFF731F,0xFF70CA,0xFF17C4,0xFF1032,
            0xFF2BBD,0xFF2C0C,0xFF2C44,0xFF2C86,0xFF2CB4,0xFF2D27,0xFF2D33,0xFF2D3A,
            0xFF2D4E,0xFF2D6C,0xFF2D85]

# ⚠ 미번역 문자열(스태프롤·해금 안내)이 실제로 쓰는 코드는 절대 뺏으면 안 된다.
#    실측: ! " & ' ( ) - .  (예: "NORMAL"LEVEL / LET'S TRY / C.YODA / TSURU-CHANG
#          / SUPERVISER(SNK) / BGM&SE / (SNK R&D DIV.2)) 그리고 0x40 = ©
#    v0.7까지 이걸 몰라서 스태프롤이 'KURARA맨K', '맨NORMAL맨LEVEL' 로 깨졌다.
RESERVED = {0x21, 0x22, 0x26, 0x27, 0x28, 0x29, 0x2D, 0x2E, 0x40}
FREE_CODES = [c for c in (list(range(0x60, 0x80)) + list(range(0x5B, 0x60)) +
                          list(range(0x3A, 0x40)) + list(range(0x21, 0x30)))
              if c not in RESERVED]          # = 50칸

# UI 문구 — ss1_ui.UI 기반, 예산에 맞게 4자 절약형으로 재조정
UI = [
    (0x009248, 'PRESS A BUTTON',    '버튼 누르시오'),
    (0x0231E8, '1P MODE',           '1인 대전'),
    (0x0231F0, 'SURVIVAL',          '서바이벌'),
    (0x0231F9, 'VS MODE',           '2인 대전'),
    (0x023201, 'GAME OPTION',       '게임 설정'),
    (0x02320F, 'VS WAIT',           '대전 대기'),
    (0x023217, 'OPTION MODE',       '게임 설정'),
    (0x023223, 'LEVEL',             '난이도'),
    (0x023229, 'POINT',             '점수'),
    (0x02322F, 'TIME',              '시간'),
    (0x023234, 'VS/POINT',          '대전 점수'),
    (0x02323D, 'VS/TIME',           '대전 시간'),
    (0x023245, 'SE',                '소리'),
    (0x023248, 'BGM',               'BGM'),
    (0x02324C, 'EXIT',              '나가기'),
    (0x00C633, ' EASY ',            '하'),
    (0x00C63A, 'NORMAL',            '중'),
    (0x00C641, ' HARD ',            '상'),
    (0x011291, 'SELECTABLE!!',      '선택 가능!!'),
    (0x01129E, 'ENTER THE COMMAND', '무작위 커맨드'),
    (0x0112B0, 'AT CHARACTER RAN-', '화면에서 커맨드'),
    (0x0112C2, '-DOM SELECT',       '입력하시오'),
    (0x0234DF, 'CONGRATULATIONS!!', '축하합니다!!'),
    (0x0234F1, 'CLEAR!',            '클리어!'),
]


def bios_font_2bpp(ink=3, bg=0):
    """beetle-ngp bios.c 의 1bpp 폰트 → VECT_SYSFONTSET 과 동일한 2bpp 전개"""
    import re
    src = open('/root/ss2_work/beetle-ngp/mednafen/ngp/bios.c').read()
    m = re.search(r'static const uint8_t font\[0x800\] = \{(.*?)\};', src, re.S)
    vals = [int(x, 16) for x in re.findall(r'0x([0-9A-Fa-f]{2})', m.group(1))]
    assert len(vals) == 0x800
    out = bytearray()
    for b in vals:
        w = 0
        for j in range(8):
            w = (w << 2) | (ink if (b << j) & 0x80 else bg)
        out += bytes((w & 0xFF, w >> 8))
    return out                       # 0x1000B = 128타일


STUB_CODE = (bytes([0x3A, 0x3B, 0x29,                    # PUSH XDE / PUSH XHL / PUSH BC
                    0x42, 0x00, 0xA0, 0x00, 0x00,        # LD XDE, 0x0000A000
                    0x43]) + (0x200000 + FONT).to_bytes(4, 'little') +  # LD XHL, font
             bytes([0x31, 0x00, 0x08,                    # LD BC, 0x0800 (워드 수)
                    0x93, 0x11,                          # LDIRW (XDE+),(XHL+)
                    0x49, 0x5B, 0x5A, 0x0E]))            # POP BC/XHL/XDE, RET


CENTERED = {0x009248, 0x011291, 0x01129E, 0x0112B0, 0x0112C2, 0x0234DF, 0x0234F1,
            0x00C633, 0x00C63A, 0x00C641}


def patch(rom, report=True):
    # 1) 벡터표 + 스텁 + 폰트
    for i, v in enumerate(BIOS_VEC):
        rom[VECTAB + 4*i: VECTAB + 4*i + 4] = v.to_bytes(4, 'little')
    rom[VECTAB + 5*4: VECTAB + 5*4 + 4] = (0x200000 + STUB).to_bytes(4, 'little')
    rom[STUB: STUB + len(STUB_CODE)] = STUB_CODE
    font = bios_font_2bpp()

    # 2) 한글 음절 → 빈 코드 배정 + 글리프 굽기 (Galmuri7, 잉크 3)
    codes = {}
    free = list(FREE_CODES)
    def code_of(ch):
        if ch not in codes:
            assert free, '코드 예산 초과'
            codes[ch] = free.pop(0)
            bm = ss1_ui.cell(ch)
            a = codes[ch] * 16
            for r in range(8):
                w = 0
                for k in range(8):
                    if bm[r][k]:
                        w |= 3 << (14 - 2*k)
                font[a + r*2] = w & 0xFF
                font[a + r*2 + 1] = w >> 8
        return codes[ch]

    # 3) 문자열 재작성 (원문 대조 → 길이 보존, 남는 칸 공백)
    for addr, en, ko in UI:
        cur = bytes(rom[addr: addr + len(en)])
        assert cur == en.encode(), f'원문 불일치 {addr:06X}: {cur}'
        assert rom[addr + len(en)] == 0x00, f'널 종결 아님 {addr:06X}'
        buf = bytearray()
        for ch in ko:
            buf.append(ord(ch) if (ch == ' ' or ch.isascii()) else code_of(ch))
        assert len(buf) <= len(en), f'길이 초과 {addr:06X}'
        pad = len(en) - len(buf)
        if addr in CENTERED:
            buf = b'\x20' * (pad // 2) + buf + b'\x20' * (pad - pad // 2)
        else:                                   # 메뉴 항목은 좌정렬 (원본과 동일)
            buf = buf + b'\x20' * pad
        rom[addr: addr + len(en)] = buf

    rom[FONT: FONT + 0x1000] = font

    # 4) 디스패처 벡터표 베이스 재지정
    assert bytes(rom[DISP_IMM - 1: DISP_IMM + 4]).hex() == '4400feff00', \
        '디스패처 시그니처 불일치: ' + bytes(rom[DISP_IMM-1:DISP_IMM+4]).hex()
    rom[DISP_IMM: DISP_IMM + 4] = (0x200000 + VECTAB).to_bytes(4, 'little')

    if report:
        print(f'  음절 {len(codes)}자 / 예산 {len(FREE_CODES)}칸, 문자열 {len(UI)}개')
        print(f'  벡터표 {VECTAB:06X} 스텁 {STUB:06X} 폰트 {FONT:06X}')
    return codes


if __name__ == '__main__':
    src = sys.argv[1] if len(sys.argv) > 1 else '/root/ss2_work/ss1/SS1_KO_v0.4.ngp'
    dst = sys.argv[2] if len(sys.argv) > 2 else '/tmp/test_gfx8.ngp'
    rom = bytearray(open(src, 'rb').read())
    codes = patch(rom)
    open(dst, 'wb').write(rom)
    print('→', dst)
    print('배정:', ''.join(sorted(codes, key=codes.get)))
