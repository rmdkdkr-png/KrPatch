# -*- coding: utf-8 -*-
"""gfx13.py — 받침 동시 출력 (L 항목 코드 패치)

대사 렌더러(파일 0x00F7C9~0x00F936, 이 세션에서 전체 손 디스어셈블)의
글자-후처리 구간을 자유영역 스텁으로 돌려, 스트림을 [윗코드][받침코드] 페어
인터리브로 해석하게 한다. 윗글자를 찍은 직후 **같은 틱에** 받침을 찍는다.

엔진 RAM 변수 (실측):
  0x5C69 VRAM 타일 카운터   0x5C6B/6C 기준 col/row   0x5C6D/6E 진행 col/row
  0x5C6F 페이스값(0=즉시)   0x5C70 틱 카운터          0x5C71 페이지 대기
  0x5C73 스트림 포인터(L)   0x5C77 활성 플래그
토글 램 없이 진행 row(0x5C6E)의 0/1을 페어 상태로 쓴다. 페이지=한 줄이므로 안전.
데이터 측은 ss1_build2.encode 가 F8 없이 t,b 페어로 굽는다 (INTERLEAVE=True).
"""

HOOK   = 0x00F86E          # 원본: col++/줄바꿈/스트림++ 구간 시작
STUB   = 0x1D1800          # 자유영역 (파일) — CPU 0x3D1800
F805   = bytes([0x1B, 0x05, 0xF8, 0x20])   # JP 0x20F805 (다음 글리프 즉시)
F893   = bytes([0x1B, 0x93, 0xF8, 0x20])   # JP 0x20F893 (페이스 경로)

STUB_CODE = bytes([
    0xC2,0x6E,0x5C,0x00,0x21,      # LD A,(0x5C6E)      진행 row
    0xC9,0xD8,                     # CP A,#0
    0x66,0x1B,                     # JR Z,+27 → was_top
    # was_bottom: 방금 받침을 찍었다 → 페어 완료
    0xC2,0x6E,0x5C,0x00,0x69,      # DEC #1,(0x5C6E)    row 복귀
    0xC2,0x6D,0x5C,0x00,0x61,      # INC #1,(0x5C6D)    col++
    0xE2,0x73,0x5C,0x00,0x24,      # LD XIX,(0x5C73)
    0xBC,0x01,0x34,                # LDA XIX,(XIX+1)    스트림++
    0xF2,0x73,0x5C,0x00,0x64,      # LDL (0x5C73),XIX
]) + F893 + bytes([
    # was_top: 방금 윗글자를 찍었다 → 받침을 같은 틱에
    0xC2,0x6E,0x5C,0x00,0x61,      # INC #1,(0x5C6E)    받침 줄로
    0xE2,0x73,0x5C,0x00,0x24,      # LD XIX,(0x5C73)
    0xBC,0x01,0x34,                # LDA XIX,(XIX+1)    스트림++
    0xF2,0x73,0x5C,0x00,0x64,      # LDL (0x5C73),XIX
]) + F805

HOOK_CODE = bytes([0x1B, 0x00, 0x18, 0x3D])   # JP 0x3D1800


def patch(rom, report=True):
    assert rom[HOOK:HOOK+5] == bytes.fromhex('c26d5c0020'), '렌더러 원본 불일치'
    assert set(rom[STUB:STUB+len(STUB_CODE)]) == {0xFF}, '스텁 자리 사용 중'
    rom[STUB:STUB+len(STUB_CODE)] = STUB_CODE
    rom[HOOK:HOOK+4] = HOOK_CODE
    if report:
        print('  렌더러 후킹 %06X → 스텁 %06X (%dB) — 받침 동시 출력' % (HOOK, STUB, len(STUB_CODE)))
    return rom
