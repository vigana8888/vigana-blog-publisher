"""
최초 1회만 실행하는 스크립트.
실제 브라우저 창이 뜨면 사용자가 직접 네이버 아이디/비밀번호로 로그인한다.
이 스크립트는 비밀번호를 저장하거나 다루지 않는다 — 로그인 후 세션(쿠키)만 저장한다.

실행:
    .venv\\Scripts\\python.exe scripts\\login_setup.py
"""

import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

SESSION_FILE = Path(__file__).resolve().parent.parent / "naver_session.json"
MAX_WAIT_SECONDS = 240
POLL_SECONDS = 3


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://nid.naver.com/nidlogin.login")

        print("\n브라우저 창에서 직접 네이버 아이디/비밀번호로 로그인해주세요.")
        print("2단계 인증(휴대폰 인증 등)이 있다면 그것도 마쳐주세요.")
        print(f"터미널 입력 없이 자동으로 감지합니다 (최대 {MAX_WAIT_SECONDS}초 대기).")
        sys.stdout.flush()

        waited = 0
        logged_in = False
        while waited < MAX_WAIT_SECONDS:
            page.wait_for_timeout(POLL_SECONDS * 1000)
            waited += POLL_SECONDS
            url = page.url
            if "nidlogin" not in url and "nid.naver.com" not in url:
                logged_in = True
                print(f"[{waited}s] 로그인 완료 감지 (현재 URL: {url})")
                sys.stdout.flush()
                break
            if waited % 15 == 0:
                print(f"[{waited}s] 로그인 대기 중... (현재 URL: {url})")
                sys.stdout.flush()

        if not logged_in:
            print(f"\n{MAX_WAIT_SECONDS}초 동안 로그인 완료를 감지하지 못했습니다. 그래도 현재 세션 상태를 저장합니다.")

        context.storage_state(path=str(SESSION_FILE))
        print(f"\n로그인 세션을 저장했습니다: {SESSION_FILE}")
        print("이제부터는 save_draft.py 실행 시 이 세션을 재사용해서 로그인 없이 바로 임시저장이 가능합니다.")
        print("세션이 만료되면(며칠~몇 주 후) 이 스크립트를 다시 한 번 실행해주세요.")

        browser.close()


if __name__ == "__main__":
    main()
