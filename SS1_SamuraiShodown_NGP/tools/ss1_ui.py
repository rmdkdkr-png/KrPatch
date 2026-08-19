#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ss1_ui.py — ASCII 8×8 폰트로 그려지는 UI 문자열 한글화

원리: 이 게임은 타일맵에 ASCII 코드를 그대로 써 넣어 글자를 찍는다.
      폰트 뱅크 0x05291D 의 '타일번호 = 문자코드'.
      코드 0x60 뒤쪽은 전부 0xFF(빈칸)라 한글 음절을 새로 넣을 수 있다.
글리프: Galmuri7 (7×7) 을 8×8 칸에 1px 들여서 배치. 잉크=값3, 배경=값0.
문자열: 원본 길이를 넘지 않게 쓰고 남는 칸은 공백(0x20)으로 채운다(잔상 방지).
"""
import sys
sys.path.insert(0, '/root/ss2_work')
import bdf_render as B

FONT_BANK = 0x05291D
CODE_LO, CODE_HI = 0x60, 0x100        # 쓸 수 있는 코드 범위
BDF = '/root/ss2_work/galmuri_repo/dist/Galmuri7.bdf'

# (주소, 원문, 번역)
UI = [
    (0x009248, 'PRESS A BUTTON',   '버튼을 누르시오'),
    (0x0231E8, '1P MODE',          '1인 대전'),
    (0x0231F0, 'SURVIVAL',         '서바이벌'),
    (0x0231F9, 'VS MODE',          '2인 대전'),
    (0x023201, 'GAME OPTION',      '게임 설정'),
    (0x02320F, 'VS WAIT',          '대전 대기'),
    (0x023217, 'OPTION MODE',      '게임 설정'),
    (0x023223, 'LEVEL',            '난이도'),
    (0x023229, 'POINT',            '선취점'),
    (0x02322F, 'TIME',             '시간'),
    (0x023234, 'VS/POINT',         '대전 점수'),
    (0x02323D, 'VS/TIME',          '대전 시간'),
    (0x023245, 'SE',               '효과'),
    (0x023248, 'BGM',              '음악'),
    (0x02324C, 'EXIT',             '나가기'),
    (0x00C633, ' EASY ',           ' 쉬움 '),
    (0x00C63A, 'NORMAL',           ' 보통 '),
    (0x00C641, ' HARD ',           '어려움'),
    (0x011291, 'SELECTABLE!!',     '선택 가능!!'),
    (0x01129E, 'ENTER THE COMMAND', '캐릭터 무작위 선택'),
    (0x0112B0, 'AT CHARACTER RAN-', '화면에서 커맨드를'),
    (0x0112C2, '-DOM SELECT',      '입력하시오'),
    (0x0234DF, 'CONGRATULATIONS!!', '축하합니다!!'),
    (0x0234F1, 'CLEAR!',           '클리어!'),
]

_gl = None
def glyphs():
    global _gl
    if _gl is None: _gl = B.parse_bdf(BDF)[1]
    return _gl


def cell(ch, off=1):
    """한 글자 → 8×8 (1=잉크)"""
    g = glyphs().get(ord(ch))
    a = [[0] * 8 for _ in range(8)]
    if not g: return a
    pts, (w, h, xo, yo) = B.glyph_pixels(g)
    base = 7 - h - yo
    for rx, ry in pts:
        X, Y = rx + xo, ry + off + base
        if 0 <= Y < 8 and 0 <= X < 8: a[Y][X] = 1
    return a


def write_tile(rom, code, bm):
    a = FONT_BANK + code * 16
    for r in range(8):
        w = 0
        for k in range(8):
            if bm[r][k]: w |= 3 << (14 - 2 * k)
        rom[a + r * 2] = w & 0xFF
        rom[a + r * 2 + 1] = w >> 8


def patch(rom, items=None, report=True):
    items = items or UI
    codes = {}                     # 글자 → 코드
    nxt = CODE_LO
    out = []
    for addr, en, ko in items:
        assert rom[addr:addr + len(en)] == en.encode(), '원문 불일치 %06X' % addr
        assert rom[addr + len(en)] == 0x00, '널 종결 아님 %06X' % addr
        buf = bytearray()
        for ch in ko:
            if ch == ' ': buf.append(0x20); continue
            if ch.isascii(): buf.append(ord(ch)); continue
            if ch not in codes:
                assert nxt < CODE_HI, '코드 자리 부족'
                codes[ch] = nxt; nxt += 1
            buf.append(codes[ch])
        assert len(buf) <= len(en), '길이 초과 %06X: %s (%d>%d)' % (addr, ko, len(buf), len(en))
        buf += b'\x20' * (len(en) - len(buf))          # 남는 칸은 공백
        rom[addr:addr + len(en)] = buf
        out.append((addr, en, ko))
    for ch, c in codes.items():
        write_tile(rom, c, cell(ch))
    if report:
        print('UI 문자열 %d개 / 한글 음절 %d자 → 코드 0x%02X~0x%02X'
              % (len(items), len(codes), CODE_LO, nxt - 1))
    return codes


if __name__ == '__main__':
    rom = bytearray(open('/root/ss2_work/ss1/Samurai Shodown! (JUE) [M][!].ngp', 'rb').read())
    c = patch(rom)
    print(''.join(sorted(c, key=c.get)))
