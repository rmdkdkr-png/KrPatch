#!/usr/bin/env python3
"""bake_names_ko.py — SVC 캐릭터 이름판을 한글로 굽는다 (확인 14종, 보류 4종은 영문 유지).

    python3 bake_names_ko.py <입력.ngc> <출력.ngc> [--font Galmuri7.ttf] [--ips 출력.ips]
    python3 bake_names_ko.py <입력.ngc> --sheet 미리보기.png     # 롬 안 쓰고 도안만

## 포맷

이름판 = 연속 스트립. `[윗줄 W장][아랫줄 W장]`, 타일 8×8 2bpp 16B.
화면에는 타일맵 SCR1 행13~14 에 뜬다. 판의 첫 칸은 이름마다 다르다(x5 또는 x7).

## 색

**배경 = 색인 1, 글자 = 색인 2** 만 맞추면 된다.
팔레트는 게임이 입히므로 화면에는 원판 그대로 빨간 판에 흰 글자로 나온다 — 실기 확인 완료.

## ★ 주소를 눈으로 맞추면 반드시 틀린다

**같은 W로 창을 옆으로 밀어도 글자는 똑같이 멀쩡해 보인다.** 윗줄·아랫줄 간격이 W 로
고정돼 있어서 시작을 한두 칸 틀려도 렌더가 깨끗하게 나온다. 여백 타일로 경계를 잡는 것도
안 된다 — 아랫줄 꼬리 여백에 윗줄용 타일이 섞인 자리가 있다.

이 함정에 두 번 걸렸다. 이 파일에 주소를 박아 뒀을 때 18종 중 6종이 틀려 있었고,
그런데도 옛 대조는 18/18 통과를 찍었다. 나중에 표를 다시 만들었을 때도 TERRY 가
한 타일 밀려 있었다(`0x32AC00` → 실제 `0x32ABF0`, 번호 심기로 확정).

그래서 주소는 여기 두지 않는다. **`names_table.json` 이 유일한 출처**이고,
그 값은 `check_names.py` 가 화면에서 재서(타일맵 → VRAM → ROM 역추적) 대조한다.

## 안전 규칙 — 스트립 밖으로 새지 않게

화면의 판은 스트립보다 넓게 그려지고, 스트립 밖 칸은 **이웃 이름의 타일**을 끌어다 쓴다.
그래서 원판이 비어 있던 칸에 글자를 넣으면 옆 캐릭터 이름판에 조각이 새어 나온다.
글자를 가운데 정렬해 스트립 안에만 두는 이유가 이것이다.

## 보류 4종

마이·이오리·장기에프·펠리시아는 롬에서 렌더하면 멀쩡한데 **실기 화면에서만 깨진다.**
데이터가 아니라 화면이 스트립을 읽는 방식이 그 넷만 다르다. 원판 영문 그대로 둔다.
"""
import sys, os, json, argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BG, INK = 1, 2

# 픽셀 글꼴은 **정수 배율**로만 키워야 획이 안 뭉갠다.
# Galmuri7 은 ppem 8 에서 한글이 정확히 7x7 이므로 2배 = 14x14 로 또렷하다.
# (Galmuri11 을 ppem 16 으로 늘리면 11->16 = 1.45배라 획이 갈라진다)
PPEM, SCALE = 8, 2
GAP = 2

# 주소는 **`names_table.json` 이 유일한 출처**다. 여기 손으로 적어 두지 않는다.
#
# 예전에는 이 파일에 주소를 박아 뒀는데 18종 중 6종이 틀려 있었고, 그런데도
# 대조가 18/18 통과를 찍었다. 이 포맷은 **창이 옆으로 밀려도 글자가 똑같이 멀쩡해 보인다** —
# 윗줄·아랫줄 간격이 W 로 고정이라 시작을 한두 칸 틀려도 렌더가 깨끗하다.
# 그래서 주소는 눈이 아니라 `check_names.py` 로 화면에서 재서 확정한다.
_TABLE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'names_table.json')


def load_names(path=_TABLE, include_hold=False):
    """(원문, 시작주소, 폭, 한글) 목록. 기본으로 **보류 종은 뺀다**.

    보류 4종(마이·이오리·장기에프·펠리시아)은 롬에서 렌더하면 멀쩡한데 실기 화면에서만
    깨진다 — 데이터가 아니라 화면이 스트립을 읽는 방식이 그 넷만 다르다.
    깨진 한글보다 원판 영문이 낫다고 보고 굽지 않는다.
    """
    with open(path, encoding='utf-8') as f:
        rows = json.load(f)
    return [(e['name'], int(e['start'], 16), e['W'], e['ko']) for e in rows
            if include_hold or e.get('state') != '보류']


NAMES = load_names()


def glyph(ch, font, ppem=PPEM, scale=SCALE):
    f = ImageFont.truetype(font, ppem)
    im = Image.new('L', (48, 48), 0)
    ImageDraw.Draw(im).text((6, 6), ch, font=f, fill=255)
    a = np.array(im) > 127
    ys, xs = np.nonzero(a)
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return np.kron(a, np.ones((scale, scale), bool))


def plate_art(text, font, W, h=16, gap=GAP):
    """W*8 × 16 도안. 배경은 전부 색인 1, 글자만 색인 2.

    안 들어가면 자간을 먼저 줄이고, 그래도 안 되면 배율을 낮춘다.
    **비정수 배율은 절대 안 쓴다** — 획이 갈라져 읽기 나빠진다.
    """
    w = W * 8
    for scale in (SCALE, 1):
        for g_ in (gap, 1, 0):
            gs = [glyph(c, font, PPEM, scale) for c in text]
            total = sum(g.shape[1] for g in gs) + g_ * (len(gs) - 1)
            if total <= w:
                gap = g_
                break
        else:
            continue
        break
    else:
        raise SystemExit('%s 가 %dpx 에 안 들어간다' % (text, w))
    gh = max(g.shape[0] for g in gs)
    if gh > h:
        raise SystemExit('%s 높이 %dpx 가 %dpx 를 넘는다' % (text, gh, h))
    out = np.full((h, w), BG, np.uint8)
    x = (w - total) // 2
    y = (h - gh) // 2
    for g in gs:
        out[y:y + g.shape[0], x:x + g.shape[1]][g] = INK
        x += g.shape[1] + gap
    return out


def pack(t):
    raw = bytearray(16)
    for y in range(8):
        v = 0
        for x in range(8):
            v |= int(t[y, x]) << (14 - 2 * x)
        raw[y * 2] = v & 0xFF
        raw[y * 2 + 1] = v >> 8
    return bytes(raw)


def main(argv=None):
    ap = argparse.ArgumentParser(description='SVC 이름판 한글 굽기')
    ap.add_argument('rom')
    ap.add_argument('out', nargs='?', default=None)
    ap.add_argument('--font', default='Galmuri7.ttf', help='픽셀 글꼴 (ppem 8 에서 7x7 인 것)')
    ap.add_argument('--ips', default=None)
    ap.add_argument('--sheet', default=None, help='도안 미리보기 PNG')
    a = ap.parse_args(argv)

    with open(a.rom, 'rb') as f:
        orig = f.read()
    rom = bytearray(orig)

    arts = []
    for en, start, W, ko in NAMES:
        A = plate_art(ko, a.font, W)
        arts.append((en, ko, start, W, A))
        for i in range(W):
            rom[start + i * 16:start + i * 16 + 16] = pack(A[0:8, i * 8:i * 8 + 8])
            b = start + (W + i) * 16
            rom[b:b + 16] = pack(A[8:16, i * 8:i * 8 + 8])

    if a.sheet:
        PAL = np.array([(0, 0, 0), (200, 30, 40), (255, 255, 255), (90, 90, 90)], np.uint8)
        cell = 10 * 8 * 4
        cv = Image.new('RGB', (cell + 200, (16 * 4 + 8) * len(arts)), (25, 25, 25))
        d = ImageDraw.Draw(cv)
        for i, (en, ko, start, W, A) in enumerate(arts):
            cv.paste(Image.fromarray(PAL[A]).resize((A.shape[1] * 4, 64), Image.NEAREST),
                     (200, i * 72 + 4))
            d.text((4, i * 72 + 26), '%-9s %06X W%-2d %s' % (en, start, W, ko),
                   fill=(255, 210, 120))
        cv.save(a.sheet)
        print('도안 -> %s' % a.sheet)

    if a.out:
        with open(a.out, 'wb') as f:
            f.write(bytes(rom))
        print('이름판 %d종 구움 -> %s' % (len(NAMES), a.out))
    if a.ips and a.out:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        '..', '..', 'SS1_SamuraiShodown_NGP', 'tools'))
        from mkips import make
        from ips import apply_ips
        p = make(orig, bytes(rom))
        with open(a.ips, 'wb') as f:
            f.write(p)
        assert apply_ips(orig, p) == bytes(rom), 'IPS 왕복 검증 실패'
        print('IPS %d바이트 -> %s (왕복 검증 통과)' % (len(p), a.ips))
    return 0


if __name__ == '__main__':
    sys.exit(main())
