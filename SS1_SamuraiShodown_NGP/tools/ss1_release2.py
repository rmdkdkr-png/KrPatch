#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ss1_release2.py — 전체 한 방 빌드 (대사 + 로고 + ASCII UI + 화면그림 + 전투배너)
사용: python3 ss1_release2.py 출력.ngp [로고.json]
"""
import sys
sys.path.insert(0,'/root/ss2_work'); sys.path.insert(0,'/root/ss2_work/ss1'); sys.path.insert(0,'/home/claude')
import ss1_build2 as B, ss1_logo as L, ss1_logo_build as G, ss1_ui as U, ss1_gfxtext as X
import gfx1b, gfx2, gfx3, gfx4, gfx5, gfx6, fan

OUT  = sys.argv[1]
LOGO = sys.argv[2] if len(sys.argv) > 2 else None

print('[1/10] 대사'); B.build(OUT)
rom = bytearray(open(OUT,'rb').read())

print('[2/10] 타이틀 로고')
before = [L.read_map(rom, d)[1] for d in (L.A, L.B)]
G.inject(rom, G.load_json(LOGO) if LOGO else None)
after  = [L.read_map(rom, d)[1] for d in (L.A, L.B)]
assert before == after, '로고 맵 크기 변동 — 뒤 데이터 침범'

# [3] ASCII UI — 보류.
# 메뉴 문자열은 이 카트리지의 폰트 뱅크(0x05291D)로 그려지지 않는다.
# 실기(에뮬) 확인 결과 코드 0x60~ 이 소문자 ASCII 글리프로 찍힌다.
# 즉 화면에 실제로 쓰이는 폰트는 다른 곳(BIOS 또는 압축 블롭)에 있다.
# U.patch(rom) 를 켜면 메뉴가 "19 hi / Jklm" 같은 쓰레기가 된다.
print('[3/10] ASCII UI — 보류 (아래 주석 참조)')
print('[4/10] 화면 그림텍스트'); gfx1b.patch(rom)
print('[5/10] 전투 배너');   gfx2.patch(rom)
print('[6/10] 영문 모드 잔여'); gfx3.patch(rom, logo=LOGO)   # 타이틀과 같은 로고를 쓴다
print('[7/10] 인정증 화면'); gfx4.patch(rom)
print('[8/10] 부채 이름판'); fan.patch(rom)
print('[9/10] 영문 라운드 콜'); gfx5.patch(rom)
# [10] 전투 HUD — 보류.
# 0x015A00 뱅크(숫자·A~F·HITS)도 화면에 쓰이지 않는다.
# 검증: 이 뱅크의 '0' 글리프를 통짜로 막고 돌려도 타이머가 정상적으로 60 을 표시했다.
# gfx6.patch(rom)
print('[10/10] 전투 HUD — 보류 (아래 주석 참조)')

import gfx12, gfx13, gfx7
print('[11] 어트랙트(오프닝) 캐릭터명'); gfx7.patch(rom)

import gfx8
print('[12] 시스템 폰트 탈취 + UI 문자열'); gfx8.patch(rom)

import gfx9
print('[13] 전투 HUD 이름판'); gfx9.patch(rom)

import gfx10
print('[14] 난이도 화면 재렌더'); gfx10.patch(rom)

import gfx11
print('[15] 인트로 밝은 로고'); gfx11.patch(rom)
print('[16/17] 라운드 시작 콜(gfx12)'); gfx12.patch(rom)
print('[17/17] 받침 동시 출력(gfx13)'); gfx13.patch(rom)

# [18] 선택: 아트 외주 반입 — 세 번째 인자로 아트 JSON 을 주면 gfx12 결과 위에 덮는다
if len(sys.argv) > 3:
    import gfx14_art
    print('[18] 아트 외주 반입(gfx14):', sys.argv[3])
    gfx14_art.patch(rom, gfx14_art.load_json(sys.argv[3]))

import gfx15
print('[19] 인트로 배너(gfx15)'); gfx15.patch(rom)

import gfx16
print('[20] 검질 라벨(gfx16)'); gfx16.patch(rom)

open(OUT,'wb').write(rom)
import hashlib; print('→', OUT, len(rom), hashlib.md5(rom).hexdigest())
