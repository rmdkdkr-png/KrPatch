# -*- coding: utf-8 -*-
"""gfx4.py — 인정증(서바이벌 랭크) 화면 한글화

화면 문구 구조
  일본어 : [N]人抜き の腕前 / あなたを [등급] と認定します。
  영문   : [N] SLASH / YOUR RANK IS [등급]
일본어 세트가 두 벌(같은 내용) 있고, 영문 세트가 한 벌 있다.
"""
import sys; sys.path.insert(0,'/root/ss2_work'); sys.path.insert(0,'/home/claude')
import ss1_gfxtext as X
from gfx3 import fit

ITEMS4 = [
    # ── 대전 설정 화면 제목 (일/영) ──
    (0x072DFD, '対戦設定',  '대전 설정'),
    (0x072C0A, 'VS setting', '대전 설정'),
    # ── 일본어 1벌 ──
    (0x08F55B, '勝ち抜き無双', '연승 무쌍'),
    (0x08F60A, '人抜き',       '연승'),
    (0x08F6B6, 'あなたを',     '그대의'),
    (0x08F7C4, 'と認定します。', '등급 인정'),
    (0x08F838, '初段',   '초단'),
    (0x08F8A2, '剣客',   '검객'),
    (0x08F90C, '剣豪',   '검호'),
    (0x08F976, '剣聖',   '검성'),
    (0x08FA40, '免許皆伝', '면허개전'),
    (0x08FAD0, 'の腕前',  '실력'),
    # ── 일본어 2벌 (같은 내용) ──
    (0x09105E, '勝ち抜き無双', '연승 무쌍'),
    (0x09110D, '人抜き',       '연승'),
    (0x0911B9, 'あなたを',     '그대의'),
    (0x0912C7, 'と認定します。', '등급 인정'),
    (0x09133B, '初段',   '초단'),
    (0x0913A5, '剣客',   '검객'),
    (0x09140F, '剣豪',   '검호'),
    (0x091479, '剣聖',   '검성'),
    (0x091543, '免許皆伝', '면허개전'),
    (0x0915D3, 'の腕前',  '실력'),
    # ── 영문 ──
    (0x091A3F, 'GREATEST SURVIVOR', '연승 무쌍'),
    (0x091B0E, 'SLASH',           '연승'),
    (0x091C5C, 'YOUR RANK IS',    '그대의 등급'),
    (0x091D54, 'AMATEUR',         '초단'),
    (0x091F2A, 'BEGINNERS CLASS', '검객'),
    (0x09210E, 'MEDIUM GRADE',    '검호'),
    (0x0922AE, 'UPPER GRADE',     '검성'),
    (0x09248A, 'SWORD MASTER',    '면허개전'),
]

def patch(rom, report=True):
    for m, ja, ko in ITEMS4:
        d = X.spec(rom, m)
        img, how = fit(ko, d)
        n = X.inject(rom, d, img)
        if report:
            print('  %-18s → %-8s %2d×%-2d 타일 %d/%d  (%s)' % (ja, ko, d['w'], d['h'], n, d['n'], how))
    return rom
