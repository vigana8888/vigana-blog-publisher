"""
drafts/ 안의 글 파일 하나를 읽어서 네이버 블로그 글쓰기 에디터에 채워넣고
"저장"(임시저장) 버튼까지 누르는 스크립트.

주의:
- 실제 발행이나 예약발행은 하지 않는다. 임시저장까지만 자동화한다.
- 이미지, 최종 발행/예약 설정은 사람이 네이버 에디터에서 직접 마무리한다.
- login_setup.py를 먼저 실행해서 naver_session.json이 있어야 동작한다.

실행:
    .venv\\Scripts\\python.exe scripts\\save_draft.py drafts\\2026-08-06-어깨받침-1편.md
"""

import sys
import os
import re
from pathlib import Path

import frontmatter
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SESSION_FILE = ROOT / "naver_session.json"

load_dotenv(ROOT / ".env")
BLOG_ID = os.getenv("BLOG_ID", "erumgamsa")


def load_draft(path: Path):
    post = frontmatter.load(path)
    title = post.get("title") or post.metadata.get("title") or path.stem
    body = post.content.strip()
    # 파일 하단의 "## 이미지 프롬프트" 섹션은 참고용이며 실제 글 본문이 아니므로 제외한다.
    body = body.split("## 이미지 프롬프트")[0]
    body = body.strip()
    if body.endswith("---"):
        body = body[: -len("---")].strip()
    return title, body


def main():
    if len(sys.argv) < 2:
        print("사용법: python scripts/save_draft.py drafts/파일명.md")
        sys.exit(1)

    draft_path = Path(sys.argv[1])
    if not draft_path.exists():
        print(f"파일을 찾을 수 없습니다: {draft_path}")
        sys.exit(1)

    if not SESSION_FILE.exists():
        print("로그인 세션이 없습니다. 먼저 scripts/login_setup.py를 실행해주세요.")
        sys.exit(1)

    title, body = load_draft(draft_path)
    paragraphs = [p for p in body.split("\n\n") if p.strip()]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state=str(SESSION_FILE))
        page = context.new_page()

        write_url = f"https://blog.naver.com/{BLOG_ID}?Redirect=Write&"
        print(f"글쓰기 페이지로 이동: {write_url}")
        page.goto(write_url)
        page.wait_for_timeout(3000)

        page.screenshot(path=str(ROOT / "debug_00_after_goto.png"), full_page=True)
        print(f"현재 페이지 프레임 목록: {[f.name for f in page.frames]}")

        # 에디터는 iframe(mainFrame) 안에 있다.
        frame = page.frame(name="mainFrame")
        if frame is None:
            print("에디터 iframe(mainFrame)을 찾지 못했습니다.")
            browser.close()
            sys.exit(1)

        frame.wait_for_timeout(1500)

        # "작성 중인 글이 있습니다 / 이어서 작성하시겠습니까?" 팝업은 mainFrame 안에서 뜬다.
        # 취소를 눌러 이전 임시저장 내용을 버리고 새 글로 시작한다.
        # (역할 기반 검색은 툴바의 "취소선 적용" 버튼과 이름이 겹쳐 strict mode 에러가 나므로
        #  팝업 전용 클래스로 정확히 짚는다.)
        try:
            cancel_btn = frame.locator(".se-popup-button-cancel")
            cancel_btn.wait_for(state="visible", timeout=3000)
            cancel_btn.click()
            print("이어서 작성 팝업 -> 취소 클릭, 새 글로 시작")
            frame.locator(".se-popup-dim").wait_for(state="hidden", timeout=5000)
            frame.wait_for_timeout(500)
        except Exception as e:
            print(f"이어서 작성 팝업 없음 또는 처리 실패: {e}")

        # 우측 "도움말" 패널이 열려 있으면 저장/발행 버튼이 있는 자리를 덮어버리므로 먼저 닫는다.
        # (페이지 레벨 UI라 mainFrame 밖에 있음. 닫기 버튼이 항상 우상단 고정 위치에 뜬다.)
        try:
            help_close = page.get_by_role("button", name="닫기")
            help_close.first.click(timeout=3000)
            page.wait_for_timeout(300)
            print("도움말 패널 닫음")
        except Exception:
            try:
                page.mouse.click(1222, 42)
                page.wait_for_timeout(300)
                print("도움말 패널 닫음 (좌표 클릭)")
            except Exception as e:
                print(f"도움말 패널 닫기 실패(무시하고 진행): {e}")

        page.screenshot(path=str(ROOT / "debug_01_frame_loaded.png"))

        # 제목 입력 — 바깥 컨테이너가 아니라 실제 커서가 들어가는 안쪽 문단 요소를 클릭해야 한다.
        # 이어서 작성 팝업을 취소해도 에디터에 잔존 텍스트가 남아있을 수 있으므로,
        # 커서 위치와 무관하게 항상 전체선택 후 삭제해서 빈 상태로 만들고 입력한다.
        try:
            title_para = frame.locator(".se-title-text .se-text-paragraph").first
            title_para.click(timeout=5000)
            page.wait_for_timeout(300)
            page.keyboard.press("Control+a")
            page.keyboard.press("Delete")
            page.wait_for_timeout(200)
            page.keyboard.type(title, delay=15)
        except Exception as e:
            print(f"제목 입력 중 문제 발생: {e}")
        page.screenshot(path=str(ROOT / "debug_02_after_title.png"))

        # 본문 입력: ".se-main-container"는 이 에디터 버전에 존재하지 않는다(진단 결과 0개).
        # 프레임 전체에서 .se-text-paragraph는 정확히 2개뿐이며(제목 1개 + 본문 1개),
        # 제목이 먼저 나오므로 마지막 요소가 본문 문단이다.
        try:
            body_para = frame.locator(".se-text-paragraph").last
            body_para.wait_for(state="visible", timeout=8000)
            body_para.click(timeout=5000)
            page.wait_for_timeout(300)
            page.keyboard.press("Control+a")
            page.keyboard.press("Delete")
            page.wait_for_timeout(200)
            for para in paragraphs:
                page.keyboard.type(para, delay=15)
                page.keyboard.press("Enter")
                page.keyboard.press("Enter")
                page.wait_for_timeout(100)
        except Exception as e:
            print(f"본문 입력 중 문제 발생: {e}")
        page.screenshot(path=str(ROOT / "debug_03_after_body.png"), full_page=True)

        page.wait_for_timeout(1000)
        page.screenshot(path=str(ROOT / "debug_04_before_save.png"), full_page=True)

        # 저장(임시저장) 버튼 클릭 — 상단 헤더의 "저장" 버튼(발행 버튼과는 다름).
        # 이 버튼은 mainFrame이 아니라 별도의 상단 툴바 iframe 안에 있을 수 있으므로
        # page 레벨과 모든 하위 프레임을 차례로 시도한다.
        saved = False
        candidates = [("page", page)] + [(f"frame[{i}]:{f.url}", f) for i, f in enumerate(page.frames)]
        for label, target in candidates:
            try:
                save_btn = target.get_by_role("button", name=re.compile("^저장"))
                save_btn.first.click(timeout=3000)
                saved = True
                print(f"'저장' 버튼 클릭 성공 ({label})")
                break
            except Exception:
                continue

        if not saved:
            print("'저장' 버튼(role=button) 클릭 실패 — text 셀렉터로 재시도")
            for label, target in candidates:
                try:
                    save_btn = target.locator(".se-toolbar-button:has-text('저장'), button:has-text('저장')").first
                    save_btn.click(timeout=3000)
                    saved = True
                    print(f"'저장' 텍스트 클릭 성공 ({label})")
                    break
                except Exception:
                    continue

        page.wait_for_timeout(1500)
        page.screenshot(path=str(ROOT / "debug_05_after_save.png"), full_page=True)

        if saved:
            print("저장 버튼 클릭 완료 — debug_05_after_save.png로 실제 저장 여부를 확인하세요.")
        else:
            print("저장 버튼을 찾지 못했습니다 — debug_04_before_save.png를 보고 직접 저장해주세요.")

        page.wait_for_timeout(1500)
        browser.close()
        print("완료.")


if __name__ == "__main__":
    main()
