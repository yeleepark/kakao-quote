#!/usr/bin/env python3
"""매일 아침 카카오톡 '나에게 보내기'로 좋은 글귀를 발송한다.

사용법:
  python3 kakao_quote.py auth   # 최초 1회: 브라우저로 카카오 로그인 → 토큰 저장
  python3 kakao_quote.py send   # 글귀 생성 후 발송 (launchd가 매일 호출)
  python3 kakao_quote.py test   # 글귀를 생성만 하고 출력
"""
import http.server
import json
import os
import random
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))


def load_env(path):
    """간단한 .env 로더 (KEY=VALUE). 이미 설정된 환경변수는 덮어쓰지 않는다."""
    if not os.path.exists(path):
        return
    for line in open(path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))


load_env(os.path.join(HERE, ".env"))

# 토큰 저장 위치 (키는 저장하지 않는다)
CONF = os.path.expanduser(os.environ.get("KAKAO_TOKEN_FILE", "~/.assistant/kakao.json"))
REDIRECT = os.environ.get("KAKAO_REDIRECT_URI", "http://localhost:8765/callback")
CLAUDE = os.environ.get("CLAUDE_BIN") or shutil.which("claude") or "claude"


def api_key():
    key = os.environ.get("KAKAO_REST_API_KEY")
    if not key:
        sys.exit("KAKAO_REST_API_KEY 환경변수가 없습니다. .env.example을 참고하세요.")
    return key

FALLBACK = [
    "천 리 길도 한 걸음부터.",
    "오늘 할 수 있는 작은 일 하나가 내일을 바꾼다.",
    "완벽보다 시작이 먼저다.",
    "꾸준함은 재능을 이긴다.",
    "어제보다 조금 나은 오늘이면 충분하다.",
]


def load():
    if not os.path.exists(CONF):
        sys.exit(f"토큰 파일이 없습니다. 먼저 `python3 kakao_quote.py auth`를 실행하세요: {CONF}")
    with open(CONF) as f:
        return json.load(f)


def save(d):
    os.makedirs(os.path.dirname(CONF), exist_ok=True)
    with open(CONF, "w") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    os.chmod(CONF, 0o600)


def post(url, data, headers=None):
    req = urllib.request.Request(
        url, data=urllib.parse.urlencode(data).encode(), headers=headers or {}
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode()}")


def token_request(**fields):
    body = {"client_id": api_key(), **fields}
    if os.environ.get("KAKAO_CLIENT_SECRET"):
        body["client_secret"] = os.environ["KAKAO_CLIENT_SECRET"]
    return post("https://kauth.kakao.com/oauth/token", body)


def auth():
    conf = {}
    code_box = {}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            code_box["code"] = q.get("code", [None])[0]
            if not code_box["code"]:
                print("콜백 수신(코드 없음):", self.path, flush=True)
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write("인증 완료. 이 창은 닫아도 됩니다.".encode())

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("localhost", 8765), H)
    url = "https://kauth.kakao.com/oauth/authorize?" + urllib.parse.urlencode(
        {
            "client_id": api_key(),
            "redirect_uri": REDIRECT,
            "response_type": "code",
            "scope": "talk_message",
        }
    )
    print("브라우저에서 카카오 로그인/동의를 진행하세요:\n", url)
    webbrowser.open(url)
    while "code" not in code_box:
        srv.handle_request()
    if not code_box["code"]:
        sys.exit("인증 코드를 받지 못했습니다.")

    t = token_request(
        grant_type="authorization_code",
        redirect_uri=REDIRECT,
        code=code_box["code"],
    )
    conf["access_token"] = t["access_token"]
    conf["refresh_token"] = t["refresh_token"]
    conf["access_expires_at"] = int(time.time()) + int(t["expires_in"]) - 60
    save(conf)
    print("토큰 저장 완료:", CONF)


def fresh_token():
    conf = load()
    if time.time() >= conf.get("access_expires_at", 0):
        t = token_request(grant_type="refresh_token", refresh_token=conf["refresh_token"])
        conf["access_token"] = t["access_token"]
        conf["access_expires_at"] = int(time.time()) + int(t["expires_in"]) - 60
        if t.get("refresh_token"):  # 만료 임박 시에만 새로 내려옴
            conf["refresh_token"] = t["refresh_token"]
        save(conf)
    return conf["access_token"]


def make_quote():
    prompt = (
        "아침에 읽기 좋은 짧은 한국어 글귀를 한 개만 써줘. "
        "격려가 되는 담백한 톤, 80자 이내, 따옴표·이모지·설명·출처 없이 글귀 본문만. "
        f"(변주용 숫자: {random.randint(1, 10**6)})"
    )
    try:
        out = subprocess.run(
            [CLAUDE, "-p", "--model", "haiku", prompt],
            capture_output=True,
            text=True,
            timeout=90,
        ).stdout.strip()
        if out and len(out) <= 150:
            return out
    except Exception:
        pass
    return random.choice(FALLBACK)


def send():
    quote = make_quote()
    token = fresh_token()
    tpl = {
        "object_type": "text",
        "text": f"☀️ 좋은 아침이에요\n\n{quote}",
        "link": {"web_url": "https://calendar.google.com"},
    }
    r = post(
        "https://kapi.kakao.com/v2/api/talk/memo/default/send",
        {"template_object": json.dumps(tpl, ensure_ascii=False)},
        {"Authorization": f"Bearer {token}"},
    )
    print(time.strftime("%F %T"), "sent:", r, "|", quote)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"auth": auth, "send": send, "test": lambda: print(make_quote())}.get(
        cmd, lambda: sys.exit(__doc__)
    )()
