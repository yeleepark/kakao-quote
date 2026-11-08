# kakao-quote

매일 아침 9시에 카카오톡 "나에게 보내기"로 좋은 글귀를 보낸다.

## 설정
1. Kakao Developers 앱 생성 → 카카오 로그인 활성화, Redirect URI `http://localhost:8765/callback` 등록, 동의항목 `talk_message` 설정
2. `cp .env.example .env` 후 `KAKAO_REST_API_KEY`, `KAKAO_CLIENT_SECRET`, `CLAUDE_BIN` 입력
3. `python3 kakao_quote.py auth` (최초 1회, 토큰은 `~/.assistant/kakao.json`에 저장)
4. `python3 kakao_quote.py send` 로 테스트

## 스케줄 (macOS launchd)
`launchd/kakao-quote.plist.example`의 `__REPO_DIR__`, `__HOME__`을 바꿔
`~/Library/LaunchAgents/`에 저장하고 `launchctl bootstrap gui/$(id -u) <plist>` 실행.

## GitHub Actions로 실행 (권장: 맥이 꺼져 있어도 동작)
`.github/workflows/daily-quote.yml`이 매일 09:00 KST에 실행된다. Settings → Secrets and variables → Actions에 등록:

| Secret | 설명 |
|---|---|
| `KAKAO_REST_API_KEY` | 카카오 REST API 키 |
| `KAKAO_CLIENT_SECRET` | 클라이언트 시크릿 |
| `KAKAO_REFRESH_TOKEN` | 로컬에서 `auth` 후 `~/.assistant/kakao.json`의 `refresh_token` 값 |
| `ANTHROPIC_API_KEY` | (선택) 없으면 내장 글귀 목록에서 발송 |
| `GH_PAT` | (선택) Secrets 쓰기 권한 PAT. refresh token(약 60일)이 갱신될 때 `KAKAO_REFRESH_TOKEN`을 자동 교체 |

`refresh_token`은 값을 화면에 찍지 않고 바로 등록할 수 있다:
`python3 -c "import json,os;print(json.load(open(os.path.expanduser('~/.assistant/kakao.json')))['refresh_token'],end='')" | gh secret set KAKAO_REFRESH_TOKEN`

주의: 저장소에 60일간 활동이 없으면 GitHub가 스케줄을 자동 중지한다. 로컬 launchd와 동시에 켜두면 중복 발송되므로 하나만 사용한다.
