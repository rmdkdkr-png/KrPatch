#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bdf_render.py — 최소 BDF 파서 (ss1_ui.py / ss1_tool.py 용 재구현)

인계 패키지에 원본이 빠져 있어 같은 인터페이스로 다시 만든 것.
    parse_bdf(path)  -> (props, {encoding: glyph})
    glyph_pixels(g)  -> ([(x, y), ...], (w, h, xoff, yoff))
                        x,y 는 글리프 비트맵 좌상단 기준
"""


def parse_bdf(path):
    props, glyphs = {}, {}
    cur = None
    bitmap = False
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.rstrip('\n').rstrip('\r')
            if bitmap:
                if line.startswith('ENDCHAR'):
                    bitmap = False
                    if cur is not None and cur.get('enc') is not None:
                        glyphs[cur['enc']] = cur
                    cur = None
                else:
                    cur['rows'].append(line.strip())
                continue
            if line.startswith('STARTCHAR'):
                cur = {'enc': None, 'bbx': (0, 0, 0, 0), 'rows': []}
            elif line.startswith('ENCODING') and cur is not None:
                cur['enc'] = int(line.split()[1])
            elif line.startswith('BBX') and cur is not None:
                w, h, xo, yo = (int(v) for v in line.split()[1:5])
                cur['bbx'] = (w, h, xo, yo)
            elif line.startswith('BITMAP') and cur is not None:
                bitmap = True
            elif ' ' in line and cur is None:
                k, _, v = line.partition(' ')
                props[k] = v.strip()
    return props, glyphs


def glyph_pixels(g):
    w, h, xo, yo = g['bbx']
    pts = []
    for y, row in enumerate(g['rows'][:h]):
        if not row:
            continue
        val = int(row, 16)
        nbits = len(row) * 4
        for x in range(w):
            if (val >> (nbits - 1 - x)) & 1:
                pts.append((x, y))
    return pts, (w, h, xo, yo)
