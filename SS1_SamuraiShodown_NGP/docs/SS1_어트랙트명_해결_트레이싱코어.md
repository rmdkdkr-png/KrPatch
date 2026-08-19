# SS1 — K(어트랙트 캐릭터명) 해결 + 트레이싱 에뮬레이터 확보 (v0.4)

인계 rev0.3을 이어받은 세션의 실측 기록. 추측 없음 — 전부 트레이싱·왕복검증·실기 캡처로 확인.

## 0. 결과 한 줄

K(어트랙트 모드 캐릭터명) **해결**, `SS1_Korean_v0.4.ips` 산출.
읽기 워치포인트 달린 beetle-ngp 코어를 소스 빌드해서 확보.

## 1. 트레이싱 코어

`mednafen/ngp/mem.c`에 훅: loadB/loadW 진입부에서 감시구간 읽기를 (pc, addr)로 기록.
링커 스크립트가 `retro_*`만 내보내므로 함수명은 `retro_dbg_*`로.

- `retro_dbg_watch(lo, hi)` — CPU주소 [lo,hi) 감시 (CPU주소 = 파일오프셋 + 0x200000)
- `retro_dbg_log_count/pc/ad(i)` — 로그 조회
- `retro_dbg_peek(addr)` / `retro_dbg_peek_block` — RAM/VRAM 포함 임의 읽기
- 명령어 페치도 loadB 경유 → 데이터 영역만 감시할 것.

파이썬 하네스 `ngp_harness.py` (ctypes 직결):
- 화면이 원본 해상도 160×152로 바로 나옴
- `watch/watch_log/peek/wwatch/wlog`, 세이브스테이트, `language='japanese'|'english'`

⚠ RTC가 호스트 시각으로 시드됨 → 오프닝 로스터가 실행마다 다름. 재현 실험은 세이브스테이트 기준.

## 2. 어트랙트 캐릭터명 자료구조 (전부 실측)

```
마스터 디렉터리   file 0x1BA7CD  u32le×16  [addr24 | meta<<24]  ← 오프닝 씬 데이터들
                 entry15 = 0x311521 → 이름 스크립트 블록
캐릭터 디렉터리   file 0x1BA80D  u32le×16  entry0~13 = 캐릭터별 데모 블록,
                 entry15 = 0x3B7389 = ★이름 타일뱅크
스크립트 블록     file 0x111521 ~ 0x112709 (자기완결)
  이름 레코드     [04 00][0x80|cnt][idxoff][hdr 2B][ (dx,dy)×cnt ]   dx,dy = 픽셀×2
  엔트리 표       u16le×cnt — 스프라이트별 뱅크 타일번호. 레코드 순서대로 연속 소비.
                 (앵커: 핫조 레코드 @0x111687 → 엔트리 0x11208D 실측)
타일 뱅크        file 0x1B7389 + 타일번호×16 (2bpp 워드LE, 잉크=1, 음영=2)
복사 루틴        PC 0x2005EE~0x200600 — 엔트리당 16B를 VRAM 패턴램으로
```

- 레코드 28개 = JP 14명(色~壬無月斬紅郎) + EN 14명(SIKI~ZANKURO MINAZUKI)
- 같은 블록의 나머지 14레코드는 그래픽(주먹·SNK 등). 타일 ≤0x7E, ≥0x1A0 사용 → 불가침
- 글리프 타일은 빌드타임 전역 dedup → 제자리 교체는 충돌 지뢰

## 3. 패치 방식 (gfx7.py — [11]단계)

엔트리·pairs 재작성: 구 이름 타일 0x7F~0x19F(289칸)를 풀로 재활용, 한글 글리프를
전역 dedup로 굽고(210칸), 레코드의 (dx,dy)·엔트리를 재작성. 스프라이트 수·레코드 길이 불변.
폰트는 예산 안에 드는 최대 크기 자동 선택: GAL14 → 11 → 9 → 7. 병합·압축 없음.

⚠ **PIL로 Galmuri TTF 렌더 금지**: 획이 소실됨 (카→가). 반드시 BDF를 직접 파싱할 것.
