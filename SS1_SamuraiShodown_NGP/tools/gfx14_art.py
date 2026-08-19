#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gfx14_art.py — GPT 아트 외주 반입 (전투 그래픽 27종)

편집기(SS1_전투그래픽_편집기.html)에서 내보낸 JSON 을 롬에 주입한다.
    받는 형식:  {"items": {id: [[픽셀행], ...]}}   (개별 파일 {"id":..,"canvas":..} 도 됨)
    픽셀 값:    0=투명  1=본체  2=그림자  3=윤곽
규칙:
  - 타일 주소는 **원본 롬 실측값**을 박아 둔다. spec() 재유도 금지
    (앞 단계 패치로 맵의 타일 수가 줄면 map-n*16 유도가 어긋난다).
  - 예산 초과 항목은 **주입하지 않고 반려 목록으로 보고**한다. 강제 압축 없음.
  - call_* 는 행 4개가 별도 레코드라서 8px 밴드로 잘라 넣는다.
"""
import sys, json, struct
sys.path.insert(0, '/root/ss2_work')
import ss1_logo as L

SPEC = {
 "call_jp": {
  "name": "라운드 시작 콜 (일본어판 슬롯)",
  "recs": [
   {
    "map": 471121,
    "tile": 471025,
    "n": 6,
    "w": 10,
    "h": 1,
    "mapsize": 12
   },
   {
    "map": 471294,
    "tile": 471134,
    "n": 10,
    "w": 10,
    "h": 1,
    "mapsize": 12
   },
   {
    "map": 471467,
    "tile": 471307,
    "n": 10,
    "w": 10,
    "h": 1,
    "mapsize": 12
   },
   {
    "map": 471608,
    "tile": 471480,
    "n": 8,
    "w": 10,
    "h": 1,
    "mapsize": 12
   }
  ]
 },
 "call_en": {
  "name": "라운드 시작 콜 (영문판 슬롯)",
  "recs": [
   {
    "map": 482337,
    "tile": 482209,
    "n": 8,
    "w": 10,
    "h": 1,
    "mapsize": 12
   },
   {
    "map": 482478,
    "tile": 482350,
    "n": 8,
    "w": 10,
    "h": 1,
    "mapsize": 12
   },
   {
    "map": 482651,
    "tile": 482491,
    "n": 10,
    "w": 10,
    "h": 1,
    "mapsize": 12
   },
   {
    "map": 482824,
    "tile": 482664,
    "n": 10,
    "w": 10,
    "h": 1,
    "mapsize": 12
   }
  ]
 },
 "seung_jp": {
  "name": "승 (일)",
  "recs": [
   {
    "map": 474295,
    "tile": 473543,
    "n": 47,
    "w": 7,
    "h": 7,
    "mapsize": 57
   }
  ]
 },
 "bu_jp": {
  "name": "부 (일)",
  "recs": [
   {
    "map": 474801,
    "tile": 474353,
    "n": 28,
    "w": 5,
    "h": 7,
    "mapsize": 43
   }
  ]
 },
 "seung_en": {
  "name": "승 (영)",
  "recs": [
   {
    "map": 484999,
    "tile": 484311,
    "n": 43,
    "w": 7,
    "h": 7,
    "mapsize": 57
   }
  ]
 },
 "bu_en": {
  "name": "부 (영)",
  "recs": [
   {
    "map": 485553,
    "tile": 485057,
    "n": 31,
    "w": 5,
    "h": 7,
    "mapsize": 43
   }
  ]
 },
 "gyeolchak_jp": {
  "name": "결착!! (일)",
  "recs": [
   {
    "map": 473075,
    "tile": 472307,
    "n": 48,
    "w": 12,
    "h": 4,
    "mapsize": 53
   }
  ]
 },
 "gyeolchak_en": {
  "name": "결착!! (영)",
  "recs": [
   {
    "map": 483795,
    "tile": 483331,
    "n": 29,
    "w": 14,
    "h": 4,
    "mapsize": 61
   }
  ]
 },
 "hanpan_jp": {
  "name": "한판!! (일)",
  "recs": [
   {
    "map": 473497,
    "tile": 473129,
    "n": 23,
    "w": 10,
    "h": 4,
    "mapsize": 45
   }
  ]
 },
 "hanpan_en": {
  "name": "한판!! (영)",
  "recs": [
   {
    "map": 484257,
    "tile": 483857,
    "n": 25,
    "w": 12,
    "h": 4,
    "mapsize": 53
   }
  ]
 },
 "choejong_jp": {
  "name": "최종전 (일)",
  "recs": [
   {
    "map": 472261,
    "tile": 471621,
    "n": 40,
    "w": 10,
    "h": 4,
    "mapsize": 45
   }
  ]
 },
 "choejong_en": {
  "name": "최종전 (영)",
  "recs": [
   {
    "map": 483285,
    "tile": 482837,
    "n": 28,
    "w": 10,
    "h": 4,
    "mapsize": 45
   }
  ]
 },
 "dongsita_jp": {
  "name": "동시타 (일)",
  "recs": [
   {
    "map": 475485,
    "tile": 474845,
    "n": 40,
    "w": 10,
    "h": 4,
    "mapsize": 45
   }
  ]
 },
 "dongsita_en": {
  "name": "동시타 (영)",
  "recs": [
   {
    "map": 486711,
    "tile": 486087,
    "n": 39,
    "w": 10,
    "h": 4,
    "mapsize": 45
   }
  ]
 },
 "museungbu_jp": {
  "name": "무승부 (일)",
  "recs": [
   {
    "map": 476123,
    "tile": 475531,
    "n": 37,
    "w": 10,
    "h": 4,
    "mapsize": 45
   }
  ]
 },
 "museungbu_en": {
  "name": "무승부 (영)",
  "recs": [
   {
    "map": 486029,
    "tile": 485597,
    "n": 27,
    "w": 13,
    "h": 4,
    "mapsize": 57
   }
  ]
 },
 "wanseung_jp": {
  "name": "완승 (일)",
  "recs": [
   {
    "map": 476665,
    "tile": 476169,
    "n": 31,
    "w": 10,
    "h": 4,
    "mapsize": 45
   }
  ]
 },
 "wanseung_en": {
  "name": "완승 (영)",
  "recs": [
   {
    "map": 487093,
    "tile": 486757,
    "n": 21,
    "w": 10,
    "h": 4,
    "mapsize": 45
   }
  ]
 },
 "oui_jp": {
  "name": "오의 (일)",
  "recs": [
   {
    "map": 477303,
    "tile": 476711,
    "n": 37,
    "w": 10,
    "h": 4,
    "mapsize": 45
   }
  ]
 },
 "oui_en": {
  "name": "오의 (영)",
  "recs": [
   {
    "map": 487779,
    "tile": 487139,
    "n": 40,
    "w": 10,
    "h": 4,
    "mapsize": 45
   }
  ]
 },
 "sigan_jp": {
  "name": "시간 끝 (일)",
  "recs": [
   {
    "map": 478221,
    "tile": 477693,
    "n": 33,
    "w": 10,
    "h": 4,
    "mapsize": 45
   }
  ]
 },
 "sigan_en": {
  "name": "시간 끝 (영)",
  "recs": [
   {
    "map": 488617,
    "tile": 488169,
    "n": 28,
    "w": 10,
    "h": 4,
    "mapsize": 45
   }
  ]
 },
 "round_jp": {
  "name": "라운드 (일: 숫자 뒤에 붙음)",
  "recs": [
   {
    "map": 480175,
    "tile": 479871,
    "n": 19,
    "w": 6,
    "h": 4,
    "mapsize": 29
   }
  ]
 },
 "gameover_jp": {
  "name": "게임 오버 (일)",
  "recs": [
   {
    "map": 481117,
    "tile": 480205,
    "n": 57,
    "w": 19,
    "h": 3,
    "mapsize": 61
   }
  ]
 },
 "gameover_en": {
  "name": "게임 오버 (영)",
  "recs": [
   {
    "map": 491489,
    "tile": 490577,
    "n": 57,
    "w": 19,
    "h": 3,
    "mapsize": 61
   }
  ]
 },
 "continue_jp": {
  "name": "계속할까? (일)",
  "recs": [
   {
    "map": 482091,
    "tile": 481179,
    "n": 57,
    "w": 19,
    "h": 3,
    "mapsize": 61
   }
  ]
 },
 "continue_en": {
  "name": "계속할까? (영)",
  "recs": [
   {
    "map": 492463,
    "tile": 491551,
    "n": 57,
    "w": 19,
    "h": 3,
    "mapsize": 61
   }
  ]
 }
}


def _pack(img, w, h, n):
    """img: h*8 x w*8 픽셀 → (타일들, 맵). 초과 시 RuntimeError"""
    tiles, index, mp = [], {}, []
    for y in range(h):
        row = []
        for x in range(w):
            c = tuple(tuple(img[y*8+r][x*8+k] for k in range(8)) for r in range(8))
            if c in index: row.append((index[c], 0)); continue
            f = tuple(tuple(reversed(r)) for r in c)
            if f in index: row.append((index[f], 1)); continue
            if len(tiles) >= n:
                raise RuntimeError('%d/%d' % (len(tiles)+1, n))
            index[c] = len(tiles); row.append((len(tiles), 0)); tiles.append(c)
        mp.append(row)
    return tiles, mp


def _write(rom, rec, tiles, mp):
    for i, t in enumerate(tiles):
        a = rec['tile'] + i*16
        for r in range(8):
            w = 0
            for k in range(8): w |= t[r][k] << (14 - 2*k)
            struct.pack_into('<H', rom, a + r*2, w)
    for i in range(len(tiles), rec['n']):
        rom[rec['tile']+i*16: rec['tile']+i*16+16] = b'\x00'*16
    a = rec['map']; rom[a] = len(mp); a += 1
    for row in mp:
        for t, hf in row: rom[a] = (t << 1) | hf; a += 1
        rom[a] = 0xFF; a += 1
    assert a - rec['map'] == rec['mapsize'], '맵 크기 변동'


def load_json(path):
    j = json.load(open(path))
    if 'items' in j: return j['items']
    if 'canvas' in j: return {j['id']: j['canvas']}
    raise SystemExit('알 수 없는 JSON 형식: ' + path)


def patch(rom, items, report=True):
    """items: {id: canvas}. 반환: (성공 id 목록, 반려 [(id, 밴드라벨, 사유)])"""
    ok, rejected = [], []
    for iid, canvas in items.items():
        if iid not in SPEC:
            rejected.append((iid, '', '모르는 id')); continue
        recs = SPEC[iid]['recs']
        W = recs[0]['w']*8; H = sum(r['h'] for r in recs)*8
        if len(canvas) != H or any(len(r) != W for r in canvas):
            rejected.append((iid, '', '크기 불일치: %dx%d 필요' % (W, H))); continue
        if any(p not in (0,1,2,3) for row in canvas for p in row):
            rejected.append((iid, '', '픽셀 값은 0~3만')); continue
        # 밴드 분할 → 전 밴드 예산 검사 먼저, 전부 통과할 때만 주입
        packed, bad = [], None
        y = 0
        for bi, rec in enumerate(recs):
            band = canvas[y:y+rec['h']*8]; y += rec['h']*8
            try:
                packed.append(_pack(band, rec['w'], rec['h'], rec['n']))
            except RuntimeError as e:
                bad = ('행%d' % (bi+1) if len(recs) > 1 else '', '타일 초과 ' + str(e))
                break
        if bad:
            rejected.append((iid, bad[0], bad[1])); continue
        for rec, (tiles, mp) in zip(recs, packed):
            _write(rom, rec, tiles, mp)
        ok.append(iid)
        if report:
            use = '+'.join(str(len(t)) for t, _ in packed)
            cap = '+'.join(str(r['n']) for r in recs)
            print('  %-14s %-24s 타일 %s / %s' % (iid, SPEC[iid]['name'][:24], use, cap))
    if report and rejected:
        print('  ── 반려 %d건 (원본 유지) ──' % len(rejected))
        for iid, band, why in rejected:
            print('  ✗ %-14s %s %s' % (iid, band, why))
    return ok, rejected


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('사용: gfx14_art.py <입력롬(패치본)> <아트.json> [출력롬]'); sys.exit(1)
    rom = bytearray(open(sys.argv[1], 'rb').read())
    items = load_json(sys.argv[2])
    ok, rej = patch(rom, items)
    out = sys.argv[3] if len(sys.argv) > 3 else sys.argv[1]
    open(out, 'wb').write(rom)
    print('주입 %d / 반려 %d → %s' % (len(ok), len(rej), out))
