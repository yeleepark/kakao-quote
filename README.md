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
