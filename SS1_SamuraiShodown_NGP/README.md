# 사무라이 쇼다운! (네오지오 포켓) 한글화 패치

SNK **Samurai Shodown! / サムライスピリッツ!** (Neo Geo Pocket, 1998, JUE판)의
비공식 한글화 패치입니다.

![스크린샷](screenshots/0_스샷모음_v0.19.png)

## 적용 방법

1. 원본 롬을 준비합니다.
   `Samurai Shodown! (JUE) [M][!].ngp` — MD5 `d13f954b2f1c703bdf857837c24e332e`, 2,097,152 B
   **이 저장소는 롬을 포함하지 않으며, 배포하지도 않습니다.**
2. `patches/SS1_Korean_v0.19.ips` 를 IPS 도구(Lunar IPS, Flips 등)로 원본에 적용합니다.
   결과 MD5 `3a9136e3d51c8c3f3f0c296134e64535`
3. 네오지오 포켓 에뮬레이터(mednafen, RetroArch beetle-ngp 등)로 실행합니다.
   확장자는 .ngp / .ngc 어느 쪽이든 동작합니다.

## 한글화 범위 (v0.19)

- 스토리 대사 198문장 — **받침 동시 출력 코드패치**로 타자기 연출에서도
  음절이 한 번에 완성됩니다 (렌더러 후킹 + 58바이트 스텁, 상세는 docs/)
- 타이틀 로고 4벌 + **인트로 두루마리 펼침 애니메이션**(포켓격투시리즈)
- **전투 그래픽 27종 붓글씨 아트** — 정정당당히·승·부·결착!!·한판!!·완승·
  동시타·무승부·오의·시간 끝·최종전·라운드·게임 오버·계속할까? (일/영 슬롯 전부)
- 라운드 콜 숫자 흰색 테마 통일
- 메뉴·옵션 UI 전체 (BIOS 폰트 벡터 하이재킹)
- 전투 HUD: 캐릭터 이름판(가운데 정렬), 검질 라벨 수라/나찰
- 캐릭터 선택·검질·난이도·인정증(서바이벌 랭크)·부채 이름판
- 어트랙트 캐릭터 소개 이름 (일/영 28종)
- 엔딩 컷신·엔딩 대사·스태프롤·클리어 화면

미완(의도적 보류 포함): HITS 미니폰트(4px), 분노 게이지 한자 闘決殺死怒(시스템
표시라 원본 유지 결정).

## 기술 하이라이트

리버스 엔지니어링 상세는 `docs/` 참조:

- **받침 동시 출력**: 대사 렌더러(파일 0xF7C9~)를 손 디스어셈블(tools/t900dis.py,
  beetle 인터프리터 테이블 기반)해 글리프 루프에 4바이트 후킹 + 58바이트 스텁을
  심고, 대사 데이터를 윗타일/받침타일 인터리브로 재인코딩했습니다.
- **메뉴 ASCII 폰트의 정체는 콘솔 BIOS 내장 폰트**. 시스콜 벡터표를 카트리지
  사본으로 재지정해 자체 한글 폰트를 올렸습니다 ("압축"으로 오인됐던 벽).
- **전투 그래픽 아트 파이프라인**: 타일 예산(좌우반전 공유 포함)을 실시간 표시하는
  HTML 픽셀 에디터(editor/)로 외주 제작 → JSON 반입(tools/gfx14_art.py, 예산 초과는
  압축 없이 반려) → 되읽기 픽셀 검증. 아트 정본은 assets/art_all27_v6.json.
- 자료구조 실측은 libretro 코어(beetle-ngp) 포크에 워치포인트·트레이서를 심어
  진행 (emulator/beetle-ngp-tracing.patch, ngp_harness.py).
- 폰트는 [Galmuri](https://github.com/quiple/galmuri) (SIL OFL 1.1).
  픽셀 폰트는 반드시 BDF에서 직접 읽습니다 — TTF 래스터라이즈는 획이 소실됩니다.

## 빌드 (직접 빌드하려면)

```
tools/*.py → /root/ss2_work/          (스크립트가 이 경로를 가정합니다)
원본 롬, assets/SS1_번역표.tsv → /root/ss2_work/ss1/
assets/art_all27_v6.json → /root/ss2_work/ss1/
Galmuri BDF/TTF (npm galmuri 2.40.3) → /root/ss2_work/galmuri_repo/dist/

python3 ss1_release2.py 출력.ngp assets/로고_GPT/SS1_logo_pixel_reinterpret.json ss1/art_all27_v6.json
python3 ss1_verify.py     # 왕복검증: 일치 198 / 불일치 0
```

재빌드 MD5가 배포 패치와 일치하는지 확인하세요 (`3a9136e3…`).

## 법적 고지

- 본 저장소는 게임 롬·저작권 자료를 포함하지 않습니다. IPS 패치는 원본과의
  차분만 담고 있습니다.
- Samurai Shodown! 은 SNK의 저작물입니다. 본 패치는 비영리 팬 번역이며,
  원작의 권리를 침해할 의도가 없습니다.
