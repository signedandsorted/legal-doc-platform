"""UI refresh: top stepper and mobile layout.

The stepper is a pure function in static/app.js, so it is run under Node with a sample
flow (skipped if Node is not installed). A headless-browser check for horizontal overflow
at 375 px runs when Playwright and Chrome/Chromium are available, and is skipped otherwise.
"""
import json
import re
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path

import pytest

APP_JS = Path("static/app.js")
CSS = Path("static/styles.css")


def _function_source(name: str) -> str:
    text = APP_JS.read_text(encoding="utf-8")
    start = text.index(f"function {name}(")
    depth, i = 0, text.index("{", start)
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[start:j + 1]
    raise AssertionError(f"unterminated {name}")


def _esc_source() -> str:
    m = re.search(r"^(const|function) esc\b.*$", APP_JS.read_text(encoding="utf-8"), re.M)
    assert m, "esc() helper not found in app.js"
    if m.group(1) == "function":
        return _function_source("esc")
    return m.group(0)


SERVICE = {"title": "Will", "steps": [{"id": "start", "title": "Before you start"}, {"id": "about", "title": "About you"},
                                      {"id": "children", "title": "Children & guardians"}, {"id": "executors", "title": "Your executors"},
                                      {"id": "gifts", "title": "Gifts"}]}
DRAFT = {"id": "abc123", "answers": {"start": {"ok": True}, "about": {"name": "A"}}}


def _render(index: int) -> str:
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    script = "\n".join([_esc_source(), _function_source("topStepHtml"),
                        f"process.stdout.write(topStepHtml({json.dumps(SERVICE)}, {json.dumps(DRAFT)}, {index}));"])
    out = subprocess.run([node, "-e", script], capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    return out.stdout


def test_top_stepper_shows_the_current_step_number():
    html = _render(2)
    assert "<b>Step 3 of 5</b>" in html
    assert "Children &amp; guardians" in html and "Children & guardians" not in html
    segments = re.findall(r'<li class="([^"]*)"><a href="([^"]+)"([^>]*)>', html)
    assert len(segments) == 6  # five steps plus "Check and send"
    assert [s[1] for s in segments] == [f"#/d/abc123/{i}" for i in range(5)] + ["#/d/abc123/review"]
    current = [i for i, s in enumerate(segments) if 'aria-current="step"' in s[2]]
    assert current == [2]
    assert "on" in segments[2][0].split()
    assert "done" in segments[0][0].split() and "done" in segments[1][0].split()
    assert "done" not in segments[3][0].split()
    assert 'aria-label="Your progress"' in html


def test_top_stepper_on_check_and_send():
    html = _render(-1)
    assert "<b>Check and send</b>" in html and "Step " not in html
    assert html.count('aria-current="step"') == 1
    assert re.search(r'<li class="on"><a href="#/d/abc123/review" aria-current="step">', html)


def test_step_and_review_pages_use_the_top_stepper():
    text = APP_JS.read_text(encoding="utf-8")
    assert "'<section>' + topStepHtml(s, draft, index)" in text
    assert "'<section>' + topStepHtml(s, draft, -1)" in text


def test_mobile_css_keeps_questions_first_and_touch_targets_large():
    css = CSS.read_text(encoding="utf-8")
    assert ".topstep-bar" in css
    assert ".btn{min-height:44px" in css and "input,select{min-height:44px}" in css
    assert "input,select,textarea{font-size:16px}" in css  # stops iOS zooming into fields
    assert ":focus-visible" in css and "#ffdd00" in css
    mobile = css[css.rindex("@media (max-width:900px)"):]
    assert ".layout>section{order:1" in mobile and ".layout>.side{order:2}" in mobile
    assert "overflow-x:auto" in mobile  # the nav scrolls inside itself, not the page


# --- Headless check: no horizontal overflow at 375 px ---------------------------------

def _chrome():
    for name in ("google-chrome", "chromium", "chromium-browser"):
        path = shutil.which(name)
        if path:
            return path
    return None


@pytest.fixture(scope="module")
def live_server():
    uvicorn = pytest.importorskip("uvicorn")
    from app.main import app
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=10)


def test_no_horizontal_overflow_at_375px(live_server):
    sync_api = pytest.importorskip("playwright.sync_api")
    chrome = _chrome()
    if not chrome:
        pytest.skip("no Chrome/Chromium for the headless check")
    from tests.helpers import reset_limits
    reset_limits()
    with sync_api.sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chrome, args=["--no-sandbox"])
        page = browser.new_context(viewport={"width": 375, "height": 800}).new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(live_server + "/")
        page.wait_for_load_state("networkidle")
        draft_id = page.evaluate("""async () => {
            const tok = () => decodeURIComponent((document.cookie.match(/sas_csrf=([^;]+)/) || [])[1] || "");
            const post = (u, b) => fetch(u, {method: "POST", headers: {"Content-Type": "application/json", "X-CSRF-Token": tok()}, body: JSON.stringify(b)});
            const email = "ui-" + Math.random().toString(36).slice(2) + "@example.com";
            await post("/api/auth/register", {email, password: "correct horse battery"});
            await fetch("/api/auth/me");
            return (await (await post("/api/drafts", {service: "will"})).json()).id;
        }""")
        assert draft_id
        for hash_ in ("#/", "#/pricing", f"#/d/{draft_id}/0", f"#/d/{draft_id}/2", f"#/d/{draft_id}/review"):
            page.goto(live_server + "/" + hash_)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(300)
            width = page.evaluate("document.documentElement.scrollWidth")
            assert width <= 375, f"{hash_} overflows: {width}px"
            if "/d/" in hash_ and not hash_.endswith("review"):
                n = int(hash_.rsplit("/", 1)[1]) + 1
                assert page.locator(".topstep-label b").inner_text().startswith(f"Step {n} of ")
        browser.close()
    assert not errors, errors
