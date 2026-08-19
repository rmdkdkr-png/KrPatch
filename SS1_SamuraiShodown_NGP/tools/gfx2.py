# -*- coding: utf-8 -*-
"""gfx2.py — 전투 배너/라운드 콜 한글화 (ss1_gfxtext 파이프라인 확장)"""
import sys; sys.path.insert(0,'/root/ss2_work'); sys.path.insert(0,'/home/claude')
import ss1_logo as L, ss1_gfxtext as X, banner

# (맵주소, 원문, 한글)  None = 손대지 않음
ITEMS2 = [
    # ── 일본어판 ──
    (0x0734C5, '最終戦',      '최종전'),
    (0x0737F3, '勝負あり!!',  '결착!!'),
    (0x073999, '一本!!',      '한판!!'),
    (0x073CB7, '勝',          '승'),
    (0x073EB1, '負',          '부'),
    (0x07415D, '相討ち',      '동시타'),
    (0x0743DB, '引き分け',    '무승부'),
    (0x0745F9, '完勝',        '완승'),
    (0x074877, '断末奥義',    '오의'),
    (0x074C0D, '時間切れ',    '시간 끝'),
    # 라운드 콜 = 숫자(3×4) + 本目(6×4) 조립
    (0x074C7B, '一', '1'), (0x074CFD, '二', '2'), (0x074D9F, '三', '3'),
    (0x074E41, '四', '4'), (0x074EF3, '五', '5'), (0x074FA5, '六', '6'),
    (0x075057, '七', '7'), (0x075109, '八', '8'), (0x0751BB, '九', '9'),
    (0x07526D, '百', '100'),
    (0x0753AF, '本目',        '라운드'),
    (0x07575D, 'GAME OVER',   '게임 오버'),
    (0x075B2B, 'CONTINUE?',   '계속할까?'),
    # ── 영어판 ──
    (0x075FD5, 'LAST BATTLE',     '최종전'),
    (0x0761D3, 'CONCLUSION',      '결착!!'),
    (0x0763A1, 'VICTORY!!',       '한판!!'),
    (0x076687, 'ENGA',            '승'),
    (0x0768B1, 'RDE',             '부'),
    (0x076A8D, 'STALEMATE',       '무승부'),
    (0x076D37, 'DOUBLE FATALITY', '동시타'),
    (0x076EB5, 'PERFECT',         '완승'),
    (0x077163, 'SPECIAL COMMAND', '오의'),
    (0x0774A9, 'TIME OVER',       '시간 끝'),
    (0x077FE1, 'GAME OVER',       '게임 오버'),
    (0x0783AF, 'CONTINUE?',       '계속할까?'),
    # 0x077C13 'BATTLE#' — 숫자 치환형이라 보류
    # 0x0749E5 / 0x0772D1 커맨드 표시(↓↓↑→→+A) — 원문 유지
]

DIGITS = {'1','2','3','4','5','6','7','8','9','100'}   # 라운드 콜 숫자 흰색 테마


def _theme(img):
    """검정 획(3) → 흰 본체(1) + 우하 그림자(3).
    라운드 콜 숫자를 붓글씨 아트(밝은 본체) 테마에 맞추는 용도.
    숫자가 작아 전체 윤곽을 두르면 본체가 죽어서, 그림자만 살짝 깐다."""
    H, W = len(img), len(img[0])
    ink = {(x, y) for y in range(H) for x in range(W) if img[y][x] == 3}
    out = [[0]*W for _ in range(H)]
    for x, y in ink:
        nx, ny = x+1, y+1
        if 0 <= nx < W and 0 <= ny < H and (nx, ny) not in ink:
            out[ny][nx] = 3
    for x, y in ink: out[y][x] = 1
    return out


def fit(ko, d):
    """타일 예산 안에 드는 가장 큰 렌더를 고른다.
    예산을 넘긴 채로 inject 하면 닮은 타일이 강제 병합돼 획이 무너진다."""
    import ss1_logo as L
    W, H = d['w']*8, d['h']*8
    themed = ko in DIGITS
    for shrink in range(0, H-7, 2):          # 상자 높이를 조금씩 낮추면 폰트 단계가 내려간다
        img = banner.ko_banner(ko, W, H-shrink)
        pad = H - len(img)
        if pad > 0:
            img = [[0]*W]*(pad//2) + img + [[0]*W]*(pad - pad//2)
        if themed: img = _theme(img)
        if L.count(img, d) <= d['n']:
            return img, ('원크기' if shrink == 0 else '축소 %d' % shrink)
    img = banner.ko_banner(ko, W, H)
    return (_theme(img) if themed else img), '한도 초과'


def patch(rom, report=True):
    for m, ja, ko in ITEMS2:
        d = X.spec(rom, m, ko)
        img, how = fit(ko, d)
        n = X.inject(rom, d, img)
        if report:
            print('  %-16s → %-10s %2d×%-2d 타일 %d/%d  (%s)' % (ja, ko, d['w'], d['h'], n, d['n'], how))
    return rom
