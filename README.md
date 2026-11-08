# kakao-quote

매일 아침 9시에 카카오톡 **"나와의 채팅"** 으로 좋은 글귀를 보내 주는 작은 비서.
카카오 "나에게 보내기" API를 사용하며, 의존성 없이 Python 3 표준 라이브러리만 쓴다.

```
스케줄(GitHub Actions 또는 launchd)
  └─ kakao_quote.py send
       ├─ 글귀 생성  Anthropic API → claude CLI → 내장 목록 (순서대로 시도)
       ├─ 토큰 갱신  refresh token → access token
       └─ 카카오톡 "나에게 보내기" 발송
```

## 1. 카카오 앱 준비 (최초 1회)

[Kakao Developers](https://developers.kakao.com)에서 앱을 만들고 아래를 설정한다.

1. **플랫폼 키 → REST API 키**: 키를 복사한다. **클라이언트 시크릿**이 켜져 있으면 함께 복사한다.
2. **카카오 로그인**: 활성화 ON, Redirect URI에 `http://localhost:8765/callback` 등록.
3. **동의항목**: `카카오톡 메시지 전송(talk_message)`을 **선택 동의**로 설정.

## 2. 로컬 설정

```bash
cp .env.example .env      # 값을 채운다 (.env는 git에 올라가지 않는다)
python3 kakao_quote.py auth   # 브라우저에서 로그인/동의 → 토큰 저장 (~/.assistant/kakao.json)
python3 kakao_quote.py send   # 테스트 발송
```

| 명령 | 설명 |
|---|---|
| `auth` | OAuth 인증 후 토큰 저장 (최초 1회) |
| `send` | 글귀를 만들어 발송 |
| `test` | 글귀만 생성해서 출력 (발송 안 함) |

### 환경변수

| 이름 | 필수 | 설명 |
|---|---|---|
| `KAKAO_REST_API_KEY` | ✅ | 카카오 REST API 키 |
| `KAKAO_CLIENT_SECRET` | 시크릿 사용 시 | 클라이언트 시크릿 |
| `KAKAO_REFRESH_TOKEN` | 토큰 파일이 없을 때 | CI에서 사용. 파일이 있으면 무시 |
| `ANTHROPIC_API_KEY` | 선택 | 있으면 Claude API로 글귀 생성 |
| `CLAUDE_BIN` | 선택 | 로컬 `claude` CLI 절대경로 (launchd는 PATH가 최소라 권장) |
| `QUOTE_MODEL` | 선택 | 글귀 생성 모델 (기본 `claude-haiku-5-5`) |
| `KAKAO_TOKEN_FILE` | 선택 | 토큰 저장 경로 (기본 `~/.assistant/kakao.json`) |
| `KAKAO_REDIRECT_URI` | 선택 | 기본 `http://localhost:8765/callback` |
| `NEW_REFRESH_TOKEN_FILE` | 선택 | refresh token이 새로 발급되면 이 파일에 기록 (CI용) |

## 3. 매일 실행하기

둘 중 **하나만** 쓴다. 동시에 켜면 중복 발송된다.

### A. GitHub Actions (권장 — 내 컴퓨터가 꺼져 있어도 동작)

`.github/workflows/daily-quote.yml`이 매일 09:00 KST에 실행된다.
**Settings → Secrets and variables → Actions**에 등록:

| Secret | 필수 | 값 |
|---|---|---|
| `KAKAO_REST_API_KEY` | ✅ | REST API 키 |
| `KAKAO_CLIENT_SECRET` | ✅ | 클라이언트 시크릿 |
| `KAKAO_REFRESH_TOKEN` | ✅ | 로컬 `auth` 후 `kakao.json`의 `refresh_token` |
| `ANTHROPIC_API_KEY` | 선택 | 없으면 내장 목록에서 발송 |
| `GH_PAT` | 선택 | `Secrets: write` 권한의 PAT. refresh token 갱신 시 Secret을 자동 교체 |

refresh token을 화면에 찍지 않고 바로 등록하려면:

```bash
python3 -c "import json,os;print(json.load(open(os.path.expanduser('~/.assistant/kakao.json')))['refresh_token'],end='')" | gh secret set KAKAO_REFRESH_TOKEN
```

- **Actions 탭 → daily-quote → Run workflow**로 즉시 테스트할 수 있다.
- 시간 변경: 워크플로우의 `cron`을 UTC 기준으로 수정한다 (KST = UTC+9).
- GitHub 스케줄은 수 분~수십 분 지연될 수 있고, 저장소에 60일간 활동이 없으면 자동 중지된다.

### B. macOS launchd

`launchd/kakao-quote.plist.example`의 `__REPO_DIR__`, `__HOME__`을 바꿔 `~/Library/LaunchAgents/`에 저장한다.

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/<파일>.plist   # 등록
launchctl bootout   gui/$(id -u)/<Label>                              # 해제
```

로그는 `~/.assistant/send.log`. 맥이 9시에 잠들어 있었다면 깨어날 때 실행된다.

## 4. 토큰 수명

- access token: 약 6시간 → 실행할 때마다 자동 갱신
- refresh token: 약 60일 → 만료 1개월 전부터 갱신 시 새 값이 발급된다.
  Actions에서는 `GH_PAT`이 있으면 Secret이 자동 교체되고, 없으면 경고만 남는다.
  갱신에 실패하면 `auth`를 다시 실행하고 `KAKAO_REFRESH_TOKEN`을 새로 등록한다.

## 5. 문제 해결

| 증상 | 원인 / 해결 |
|---|---|
| `KOE205` | 동의항목에 `talk_message`가 없음 → 1-3 설정 |
| `KOE010 Bad client credentials` | 클라이언트 시크릿이 켜져 있음 → `KAKAO_CLIENT_SECRET` 설정 |
| `KOE006` | Redirect URI 불일치 → 1-2의 URI를 정확히 등록 |
| `KOE320` / 인증 코드 재사용 | 인증 코드는 1회용 → `auth`를 처음부터 다시 실행 |
| 메시지가 안 옴 | 본인 카톡의 "나와의 채팅" 확인. `send.log` 또는 Actions 로그 확인 |

## 6. 보안

- 키·토큰은 코드에 넣지 않는다. 로컬은 `.env`(gitignored), CI는 GitHub Secrets를 쓴다.
- `~/.assistant/kakao.json`에는 토큰만 저장되며 권한은 `600`이다.
- 키가 외부에 노출됐다면 Kakao Developers에서 재발급하고 `.env`와 Secrets를 갱신한다.

## 7. 개발

브랜치 규칙은 [`CLAUDE.md`](CLAUDE.md) 참고: `main`은 최종 릴리즈만, 작업은 `release/<버전>` → `release/<버전>-<기능명>`.

```
kakao_quote.py                       # 인증 / 글귀 생성 / 발송
.env.example                         # 환경변수 템플릿
.github/workflows/daily-quote.yml    # 매일 09:00 KST 실행
launchd/kakao-quote.plist.example    # macOS 스케줄 템플릿
```
