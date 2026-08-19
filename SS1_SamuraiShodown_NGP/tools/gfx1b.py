# -*- coding: utf-8 -*-
"""gfx1b.py — 기존 ITEMS(화면 그림텍스트)도 압축 회피 렌더로 굽는다

원래 ss1_gfxtext.patch 는 렌더 결과를 그대로 inject 하고, 예산을 넘으면
inject 안에서 닮은 타일을 강제 병합한다. 그러면 획이 무너진다
(실제 사례: 아마쿠사 → 마마쿠사, 카즈키 → 가즈키).
여기서는 예산에 들어갈 때까지 글자를 줄여서 **압축이 아예 안 걸리게** 한다.
"""
import sys; sys.path.insert(0,'/root/ss2_work'); sys.path.insert(0,'/home/claude')
import ss1_gfxtext as X, ss1_logo as L
from gfx3 import fit


def patch(rom, report=True):
    over = []
    for m, ko in X.ITEMS:
        d = X.spec(rom, m, str(ko))
        img, how = fit(ko, d)
        n0 = L.count(img, d)
        if n0 > d['n']:
            over.append((m, ko, n0, d['n']))
        n = X.inject(rom, d, img)
        if report:
            print('  %-16s %2d×%-2d 타일 %d/%d  (%s)' %
                  (ko if isinstance(ko, str) else '/'.join(ko), d['w'], d['h'], n, d['n'], how))
    if report and over:
        print('  ★ 예산 초과로 압축이 걸린 항목:', [(hex(a), k) for a, k, x, y in over])
    return rom
