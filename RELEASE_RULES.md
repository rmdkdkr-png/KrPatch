# KrPatch 릴리즈 법칙 (한패 방·더빙 방·SP 방 공용)

> 방 공유 지식(재발 함정·실측 방법론·레포 지도)은
> [thinkbox](https://github.com/rmdkdkr-png/thinkbox) 에 있다 — 일 시작 전에 traps.md 일독.

PocketCore 앱이 이 저장소의 릴리즈를 **자동으로** 읽는다. 아래 규칙만 지키면
IPS 를 올리는 것만으로 모든 유저의 앱에 최신 한패가 들어간다.
규칙을 벗어난 이름은 자동 색인이 **조용히 무시**한다 — 에러가 안 나니 더 위험하다.

## 1. 한글패치 릴리즈

- **태그**: `<게임id>-v<판>` (예: `ms1-v0.1`, `kofr2-v0.2`). 예외(역사적): SS2 는 `v0.99b3` 식,
  SvC 는 고정 태그 `SVC` (DC 글이 이 링크를 가리키므로 유지).
- **IPS 자산 이름(자동 색인 대상)**: `<접두>_Korean_v<판>.ips`
  - 게임별 접두 (앱 색인 정규식과 1:1):

    | 게임 id | 접두 | 예 |
    |---|---|---|
    | svc | `SvC_MotM` | SvC_MotM_Korean_v0.18.ips |
    | ss2 | `SS2` | SS2_Korean_v0.99b3.ips |
    | ss1 | `SS1` | SS1_Korean_v0.19.ips |
    | lb | `LastBlade` | LastBlade_Korean_v2.2.ips |
    | kofr2 | `KOFR2` | KOFR2_Korean_v0.2.ips |
    | ffc | `FatalFuryFC` | FatalFuryFC_Korean_v0.1a.ips |
    | ms1 | `MetalSlug1st` | MetalSlug1st_Korean_v0.1.ips |
    | ms2 | `MetalSlug2nd` | MetalSlug2nd_Korean_v0.1.ips |

  - **판 토큰에는 숫자·영문·점만** (`0.1a` 가능, `0.1_fix` 불가 — `_` 가 들어가면 색인에서 빠진다.
    이는 의도된 것: `_to_` 델타, `_allcards` 파생판을 걸러내는 규칙과 같은 규칙이다).
  - 파일명은 **ASCII 만** (한글 파일명은 GitHub API 업로드가 깨진다).
- **파생판**: allcards·델타(_to_)·특정 덤프용은 `_allcards`, `_to_v0.2`, `_JUE` 같은 **밑줄 접미사**를
  붙인다 — 자동 색인이 안 집고, 사람만 받는다. BPS 는 올려도 되지만 **앱은 IPS 만 쓴다.**
- **판올림**: 배포 후 내용이 바뀌면 반드시 판번호를 올린다. 같은 이름으로 덮어쓰기 금지
  (받은 사람의 파일과 본문 해시가 어긋난 제보 전력 있음).
- **본문**: IPS 해시를 맨 앞에, 결과 해시는 **원본 덤프별로 각각** ([!]/[a1] 세이브 플래시가 달라
  결과 해시가 갈린다 — "어느 덤프든 같은 결과" 라고 쓰지 말 것).
- **롬 업로드 금지.** IPS/BPS 만.
- **스크린샷 1~3장 권장** — 적용 후 화면을 릴리즈에 자산으로 첨부하거나
  `<게임>/images/` 에 커밋하고 본문에서 참조한다. 받기 전에 결과를 보게.

## 2. 앱 반영 절차 (중요)

IPS 를 올린 것만으로는 앱에 **아직 안 간다.** 앱은 **PocketCore 저장소 `app` 태그**의
`patches.json` 색인을 보는데, 이 색인은 SP 방의 배포 스크립트가 이 저장소(KrPatch)의
릴리즈 실태를 훑어 재생성한다.

- **기존 게임의 판올림**: IPS 만 규칙대로 올리면 끝. 다음 patches.json 재배포 때 자동 반영.
- **새 게임 추가**: ①이 문서의 표에 접두를 정해 추가하고 ②SP 방에 알린다 —
  앱 Games 표(롬 헤더 표식)와 색인 정규식 추가가 필요하다. 표식은 롬 헤더 0x24 의 12바이트
  (실측해서 넘겨주면 빠르다).
- 반영 재배포 요청: SP 방(PocketCore 세션)에 "patches.json 재배포" 한 줄이면 된다.

## 3. 레포 배치와 앱 전용 태그 (손대지 말 것)

배포는 레포별로 산다 — 각자의 집에:

| 레포 | 역할 | 고정 태그 |
|---|---|---|
| **PocketCore** | 앱 APK + 색인(version/patches/cores/news .json) + 앱 대문 README | `app` |
| **ss2-sp-core** | 코어 .so(ABI 3벌)·더빙 음성팩 | `core-svc` `core-ss2` `ss2-voice` |
| **KrPatch**(여기) | 한글패치 IPS + 한패 대문 README | 게임별 `<id>-v<판>` |

고정 태그의 자산 추가·삭제·개명 금지 — SP 방 스크립트(pub_pocketcore.py / pub_content.py)만
만진다. KrPatch 의 옛 `pocketcore` 태그는 구버전 앱(v3.48 이하)이 새 APK 로 갈아타는
다리로만 남아 있다 — 지우지 말 것.

- 음성팩 판올림은 SP 방에 파일과 판번호를 넘긴다 (`ss2_voice_ko.pak` 으로 개명·업로드되고,
  cores.json 의 ver 가 바뀌어야 앱이 새 판으로 인식한다).
- 재생 키가 문장 해시이므로 **한패 자막 판과 음성팩 판은 같이** 움직여야 한다.
- README 대문(KrPatch 맨 위 마커 구역·PocketCore README 전체)과 소식(news.json)은
  배포 스크립트가 자동 갱신한다 — 손으로 고치면 다음 배포 때 덮인다.
  (KrPatch README 의 마커 아래 수제 문서는 보존된다.)

## 4. 요약 — 한패 방이 지킬 것 세 줄

1. 태그 `<id>-v<판>`, 자산 `<접두>_Korean_v<판>.ips` (ASCII, 판에 밑줄 금지)
2. 내용이 바뀌면 판을 올린다 (덮어쓰기 금지), 본문 해시는 IPS 먼저·결과는 덤프별
3. 올린 뒤 SP 방에 재배포 한 줄 (새 게임이면 헤더 표식 0x24 실측값도)
