"""
최초 1회만 실행하는 스크립트.
실제 브라우저 창이 뜨면 사용자가 직접 네이버 아이디/비밀번호로 로그인한다.
이 스크립트는 비밀번호를 저장하거나 다루지 않는다 — 로그인 후 세션(쿠키)만 저장한다.

실행:
    .venv\\Scripts\\python.exe scripts\\login_setup.py
"""

from pathlib import Path
from playwright.sync_api import sync_playwright

SESSION_FILE = Path(__file__).resolve().parent.parent / "naver_session.json"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://nid.naver.com/nidlogin.login")

        print("\n브라우저 창에서 직접 네이버 아이디/비밀번호로 로그인해주세요.")
        print("2단계 인증(휴대폰 인증 등)이 있다면 그것도 마쳐주세요.")
        print("로그인이 완료되어 네이버 메인/블로그 화면이 보이면, 이 터미널로 돌아와 Enter를 눌러주세요.")
        input("로그인 완료 후 Enter >> ")

        context.storage_state(path=str(SESSION_FILE))
        print(f"\n로그인 세션을 저장했습니다: {SESSION_FILE}")
        print("이제부터는 save_draft.py 실행 시 이 세션을 재사용해서 로그인 없이 바로 임시저장이 가능합니다.")
        print("세션이 만료되면(며칠~몇 주 후) 이 스크립트를 다시 한 번 실행해주세요.")

        browser.close()


if __name__ == "__main__":
    main()
