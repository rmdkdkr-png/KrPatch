#!/usr/bin/env python3
"""build_title_ko.py — SVC MotM 타이틀 화면 한글화 (머리글 + 안내문)

    python3 build_title_ko.py <SVC_kr_v17.2.ngc> <출력.ngc> [--font Galmuri11-Bold.ttf]
                              [--font7 Galmuri7.ttf] [--ips 출력.ips]

무엇을 고치나
  1) 머리글 「頂上決戦」 -> 「정상결전」   타일맵 평면(SCR1) 32타일
  2) 안내문 「Aボタンを おし くださ」 -> 「A버튼을 눌러 주세요」  스프라이트 12타일
     (원판 문구는 v17.2 에서 이미 「ください」의 「い」가 잘려 있다)

조사 근거는 docs/SVC_잔여타일.md, 화면 기록은 tools/tiletool/rec_svc/타이틀.json.

## 알아낸 것 (실측)

**타일 데이터가 롬에 여러 벌 있고, 실제로 읽히는 것은 하나다.**
머리글 타일은 `0x1B6xxx` 와 `0x306xxx` 두 곳에 같은 내용이 있는데, 한쪽만 바꿔 부팅해
화면이 변하는지 보는 방법으로 **`+0x150000` 쪽이 읽히는 사본**임을 확정했다.
그래서 기록에 남은 주소에 DELTA 를 더해 쓴다.

**안내문은 타일맵에 없다 — 스프라이트다.**
VRAM 512슬롯 중 두 타일맵이 참조하지 않는 슬롯을 추려 찾았다. 패턴 0~11번이
x=28,36,44,52,60, 76,84,92,100,108,116,124 / y=115 에 배치된다 (60→76 은 띄어쓰기).
원본 글자는 10자, 빈 칸은 패턴 7·11. 타일 출처는 `0x2E7F70` 부터 16바이트씩 연속이다.
이건 내용이 세 곳에서 일치해 주소 추정이 안 되던 것을, **연속 배치**를 단서로 확정했다.

**쓸 수 있는 칸은 원판이 비어 있지 않던 자리뿐이다.**
타일맵을 못 고치므로 원판이 빈 타일이던 칸에는 새 획을 못 넣는다. 머리글은
행1~3 × 열5~14 = **80×24px** 만 쓸 수 있고, 글자는 그 안에 맞춰 짰다.
"""
import sys, os, argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tiletool'))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'SS1_SamuraiShodown_NGP', 'tools'))
import tilemap as TM

REC = os.path.join(HERE, '..', 'tiletool', 'rec_svc', '타이틀.json')
DELTA = 0x150000                     # 기록된 사본 -> 실제로 읽히는 사본
HEAD_ROWS = list(range(1, 4))        # 쓸 수 있는 칸
HEAD_COLS = list(range(5, 15))
HEAD_TOP_CLEAR = [(0, 5), (0, 14)]   # 원판 頂/戦 꼭지 — 지운다
FILL, SHADE, LINE = 1, 2, 3

CAUTION_BASE = 0x2E7F70              # 스프라이트 패턴 0번 타일
CAUTION = {0: 'A', 1: '버', 2: '튼', 3: '을',
           5: '눌', 6: '러',
           8: '주', 9: '세', 10: '요'}   # 나머지 패턴은 빈 타일로


def mask_of(ch, font, size, scale=1):
    f = ImageFont.truetype(font, size)
    im = Image.new('L', (64, 48), 0)
    ImageDraw.Draw(im).text((8, 8), ch, font=f, fill=255)
    a = np.array(im) > 127
    ys, xs = np.nonzero(a)
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return np.kron(a, np.ones((scale, scale), bool)) if scale > 1 else a


def headline_art(text, font, w, h, gap=2):
    gs = [mask_of(c, font, 11, 2) for c in text]
    total = sum(g.shape[1] for g in gs) + gap * (len(gs) - 1)
    if total > w:
        raise SystemExit('머리글이 %dpx 라 %dpx 칸에 안 들어간다' % (total, w))
    gh = max(g.shape[0] for g in gs)
    m = np.zeros((h, w), bool)
    x, y = (w - total) // 2, (h - gh) // 2
    for g in gs:
        m[y:y + g.shape[0], x:x + g.shape[1]] |= g
        x += g.shape[1] + gap
    out = np.zeros((h, w), np.uint8)
    d = np.zeros_like(m)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            d |= np.roll(np.roll(m, dy, 0), dx, 1)
    out[d & ~m] = LINE                       # 남색 외곽선
    out[m] = FILL                            # 크림 획
    out[m & ~np.roll(m, -1, 0)] = SHADE      # 획 아래 1px 분홍 음영 (원판과 같은 처리)
    return out


CAUTION_PPEM = 9       # Galmuri9 를 ppem 9 로 그리면 한글이 8x8 을 꽉 채운다
CAUTION_DY = -1        # 그 크기에서 잉크가 y1~8 이라 한 줄 올려야 8행에 들어간다


def caution_tile(ch, font7, shadow=False):
    """8x8 한 칸. 글자마다 bbox 로 자르면 기준선이 어긋나므로 **고정 원점**으로 그린다.

    Galmuri7(7x7)은 이 크기에서 「을」이 「슬」로 보일 만큼 뭉갠다. 8x8 을 다 쓰는 편이 낫다.
    """
    t = np.zeros((8, 8), np.uint8)
    if ch is None:
        return t
    f = ImageFont.truetype(font7, CAUTION_PPEM)
    im = Image.new('L', (16, 16), 0)
    ImageDraw.Draw(im).text((0, CAUTION_DY), ch, font=f, fill=255)
    m = np.zeros((8, 8), bool)
    m[:] = (np.array(im) > 127)[:8, :8]
    if shadow:
        sh = np.roll(np.roll(m, 1, 0), 1, 1)
        t[sh & ~m] = 2
    t[m] = 1
    return t


def pack(tile):
    raw = bytearray(16)
    for y in range(8):
        v = 0
        for x in range(8):
            v |= int(tile[y, x]) << (14 - 2 * x)
        raw[y * 2] = v & 0xFF
        raw[y * 2 + 1] = v >> 8
    return bytes(raw)


def main(argv=None):
    ap = argparse.ArgumentParser(description='SVC 타이틀 한글화')
    ap.add_argument('rom')
    ap.add_argument('out')
    ap.add_argument('--font', default='Galmuri11-Bold.ttf', help='머리글용 (11px 픽셀 글꼴)')
    ap.add_argument('--font7', default='Galmuri9.ttf', help='안내문용 (8x8 칸을 채우는 픽셀 글꼴)')
    ap.add_argument('--head', default='정상결전')
    ap.add_argument('--ips', default=None)
    ap.add_argument('--shadow', action='store_true', help='안내문에 원판식 그림자 넣기')
    ap.add_argument('--preview', default=None, help='머리글 도안 PNG')
    a = ap.parse_args(argv)

    with open(a.rom, 'rb') as f:
        orig = f.read()
    rom = bytearray(orig)
    _, maps, s2r = TM.load_record(REC)
    m = maps[1]

    # 1) 머리글
    w, h = len(HEAD_COLS) * 8, len(HEAD_ROWS) * 8
    art = headline_art(a.head, a.font, w, h)
    n = 0
    for r in HEAD_ROWS:
        for c in HEAD_COLS:
            s = int(m[r, c]) & 0x1FF
            if s not in s2r:
                continue
            t = art[(r - HEAD_ROWS[0]) * 8:(r - HEAD_ROWS[0]) * 8 + 8,
                    (c - HEAD_COLS[0]) * 8:(c - HEAD_COLS[0]) * 8 + 8]
            ad = s2r[s] + DELTA
            rom[ad:ad + 16] = pack(t)
            n += 1
    for r, c in HEAD_TOP_CLEAR:
        s = int(m[r, c]) & 0x1FF
        if s in s2r:
            ad = s2r[s] + DELTA
            rom[ad:ad + 16] = b'\0' * 16
            n += 1

    # 2) 안내문 (스프라이트 패턴 0~11)
    k = 0
    for pat in range(12):
        ad = CAUTION_BASE + pat * 16
        rom[ad:ad + 16] = pack(caution_tile(CAUTION.get(pat), a.font7, a.shadow))
        k += 1

    with open(a.out, 'wb') as f:
        f.write(bytes(rom))
    print('머리글 타일 %d개 · 안내문 타일 %d개 -> %s' % (n, k, a.out))

    if a.preview:
        PAL = np.array([(0, 60, 90), (255, 240, 220), (220, 150, 160), (20, 30, 90)], np.uint8)
        Image.fromarray(PAL[art]).resize((w * 5, h * 5), Image.NEAREST).save(a.preview)

    if a.ips:
        from mkips import make
        p = make(orig, bytes(rom))
        with open(a.ips, 'wb') as f:
            f.write(p)
        print('IPS %d바이트 -> %s' % (len(p), a.ips))
        from ips import apply_ips
        assert apply_ips(orig, p) == bytes(rom), 'IPS 왕복 검증 실패'
        print('IPS 왕복 검증 통과')
    return 0


if __name__ == '__main__':
    sys.exit(main())
