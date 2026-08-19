#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ss1_verify.py — 빌드된 롬에서 한글 대사를 역디코드해 원문과 대조"""
import sys
sys.path.insert(0,'/root/ss2_work'); sys.path.insert(0,'/root/ss2_work/ss1')
import ss1_build2 as B, ss1_fontpatch2 as F, ss1_tool as T, ss1_ko

plans, pool = B.build('/tmp/_verify.ngp', report=False)
rom = open('/tmp/_verify.ngp','rb').read()

# 코드 → 비트맵 역인덱스
code2bm = {F.code_of(i): bm for i, bm in enumerate(pool.order)}
PLAN = B.glyph_plan()
pair2ch = {g: c for c, g in PLAN.items()}
assert len(pair2ch) == len(PLAN), '글리프 충돌 남아있음'

ok = bad = 0
for p, ko in zip(plans, ss1_ko.KO):
    body = rom[p['new']:p['new']+len(p['body'])]
    if bytes(body) != p['body']:
        print('주입 불일치 %06X' % p['new']); bad += 1; continue
    # 페이지 복원
    core = body[:-1]
    if core.endswith(b'\xfa\xf9'): core = core[:-2]
    out = []
    for page in core.split(b'\xfa\xf9'):
        if b'\xf8' in page:
            tops, bots = page.split(b'\xf8')
        else:
            tops, bots = page[0::2], page[1::2]
        s = ''
        for tc, bc in zip(tops, bots):
            if tc == B.SPACE and bc == B.SPACE: s += ' '; continue
            top, bot = code2bm.get(tc), code2bm.get(bc)
            s += pair2ch.get((top, bot), '?')
        out.append(s)
    got = '/'.join(out)
    exp = '/'.join(x.strip() for x in ko.split('/') if x.strip())
    if got == exp: ok += 1
    else:
        bad += 1
        print('불일치 %06X\n  기대 %s\n  실제 %s' % (p['new'], exp, got))
print('왕복검증: 일치 %d / 불일치 %d' % (ok, bad))
tot_pages = sum(len(p['body']) for p in plans)
print('슬롯 %d/217, 주입 %d B' % (len(pool.order), tot_pages))
