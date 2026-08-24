#!/usr/bin/env python3
"""ladder.py — 한 화면 기록을 여러 판으로 나란히 재렌더한다 (버전 사다리).

    python3 ladder.py <기록.json> <출력.png> <롬1.ngc> <롬2.ngc> ...

파손이 어느 판에서 들어와 어느 판에서 고쳐졌는지 에뮬 없이 한 장으로 본다.
라벨은 롬 파일 이름에서 딴다.
"""
import sys, os, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tilemap as TM


def main(argv=None):
    ap = argparse.ArgumentParser(description='한 화면 × 여러 롬 비교 렌더')
    ap.add_argument('record')
    ap.add_argument('out')
    ap.add_argument('roms', nargs='+')
    ap.add_argument('--plane', type=int, choices=(1, 2), default=1,
                    help='렌더할 평면 (기본 1 = SS2 텍스트 평면)')
    ap.add_argument('--gap', type=int, default=8)
    a = ap.parse_args(argv)

    from PIL import Image
    name, maps, s2r = TM.load_record(a.record)
    imgs = []
    for p in a.roms:
        with open(p, 'rb') as f:
            rom = f.read()
        im = TM.render(maps, TM.tiles_from_rom(rom, s2r), a.plane)
        on = int((im != 0).any(2).sum())
        imgs.append((os.path.splitext(os.path.basename(p))[0], im))
        print('%-24s 켜진픽셀 %6d' % (os.path.basename(p), on))
    w = imgs[0][1].shape[1]
    h = imgs[0][1].shape[0]
    cv = Image.new('RGB', (w * len(imgs) + a.gap * (len(imgs) - 1), h), (20, 20, 20))
    for i, (_, im) in enumerate(imgs):
        cv.paste(Image.fromarray(im), (i * (w + a.gap), 0))
    cv.save(a.out)
    print('%s (%s) -> %s' % (name, ' | '.join(n for n, _ in imgs), a.out))


if __name__ == '__main__':
    main()
