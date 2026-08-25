# -*- coding: utf-8 -*-
"""
lg.com As-Is 화면 캡처 (UK / DE).
- 쿠키·컨센트 배너는 클릭하지 않고 CSS로 숨김만 함 (동의/거부 어떤 행위도 하지 않음).
- lazy-load 대응: 전체 스크롤로 렌더 유발 후 요소 핸들로 캡처.
"""
import io, json, os, sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots")
os.makedirs(OUT, exist_ok=True)

HIDE = """
[id*="onetrust" i], [class*="onetrust" i], #onetrust-consent-sdk,
[class*="cookie" i][class*="banner" i], [class*="cookie-banner" i],
[id*="truste" i], [class*="chat" i][class*="widget" i],
[class*="floating" i][class*="bar" i]
{ display:none !important; }
"""

FINDERS = {
    # 텍스트로 요소를 찾고, 지정한 단계만큼 부모로 올라감
    "byText": """(args) => {
        const [needle, up, tag] = args;
        const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        let n;
        while ((n = walk.nextNode())) {
            if (n.nodeValue && n.nodeValue.includes(needle)) {
                let e = n.parentElement;
                for (let i = 0; i < up && e && e.parentElement; i++) e = e.parentElement;
                if (e) { e.scrollIntoView({block:'center'}); return e; }
            }
        }
        return null;
    }""",
    "bySel": """(sel) => {
        const e = document.querySelector(sel);
        if (e) e.scrollIntoView({block:'center'});
        return e;
    }""",
}

results = []


def autoscroll(page):
    """lazy-load 유발: 아래까지 훑고 다시 위로."""
    page.evaluate("""async () => {
        const step = 700, pause = ms => new Promise(r => setTimeout(r, ms));
        for (let y = 0; y < document.body.scrollHeight; y += step) {
            window.scrollTo(0, y); await pause(90);
        }
        window.scrollTo(0, 0); await pause(300);
    }""")
    page.wait_for_timeout(800)


def prep(page):
    page.add_style_tag(content=HIDE)
    autoscroll(page)


def shot_el(page, name, note, kind, arg):
    path = os.path.join(OUT, name + ".png")
    try:
        h = page.evaluate_handle(FINDERS[kind], arg)
        el = h.as_element()
        if el is None:
            raise ValueError("element not found")
        page.wait_for_timeout(600)
        box = el.bounding_box()
        if not box or box["width"] < 60 or box["height"] < 24:
            raise ValueError("degenerate box %s" % box)
        el.screenshot(path=path)
        sz = os.path.getsize(path)
        results.append({"name": name, "note": note, "ok": True, "bytes": sz,
                        "w": round(box["width"]), "h": round(box["height"])})
        print("OK   ", name, sz, round(box["width"]), "x", round(box["height"]))
    except Exception as e:
        results.append({"name": name, "note": note, "ok": False, "err": str(e)[:120]})
        print("FAIL ", name, str(e)[:120])


def shot_view(page, name, note):
    path = os.path.join(OUT, name + ".png")
    page.screenshot(path=path)
    results.append({"name": name, "note": note, "ok": True, "bytes": os.path.getsize(path)})
    print("OK   ", name, os.path.getsize(path), "(viewport)")


with sync_playwright() as p:
    br = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
    ctx = br.new_context(viewport={"width": 1280, "height": 900}, device_scale_factor=1,
                         locale="en-GB",
                         user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                     "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"))
    page = ctx.new_page()
    page.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")

    # ── UK PLP ────────────────────────────────────────────────
    page.goto("https://www.lg.com/uk/tvs/", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(3500)
    prep(page)
    shot_view(page, "uk_plp_top", "UK PLP 상단 — 필터 레일 + 카드 그리드")
    shot_el(page, "uk_plp_filter", "UK PLP 필터 — Ultimate Game Experience 그룹",
            "byText", ["Ultimate Game Experience", 3, None])
    shot_el(page, "uk_plp_card", "UK PLP 제품 카드 — 중복 SKU 구간",
            "byText", ["OLED83C64LA", 4, None])

    # ── UK PDP ────────────────────────────────────────────────
    page.goto("https://www.lg.com/uk/tvs-soundbars/oled-evo/oled65c64la/",
              wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(4000)
    prep(page)
    shot_view(page, "uk_pdp_hero", "UK PDP 상단 — Energy Grade : E / 가격 / Buy Now")
    shot_el(page, "uk_pdp_keyfeat", "UK PDP Key Features — 'Up to 165Hz in 4K'",
            "byText", ["Up to 165Hz", 3, None])
    shot_el(page, "uk_pdp_keyspec", "UK PDP Key Spec — '120Hz Native (VRR 165Hz)'",
            "bySel", "#pdp-specs-section")
    shot_el(page, "uk_pdp_dims", "UK PDP 치수 — '1441 x 826 x 45.1' (단위 없음)",
            "byText", ["1441 x 826", 3, None])

    # ── DE ────────────────────────────────────────────────────
    page.goto("https://www.lg.com/de/tv-soundbars/", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(3500)
    prep(page)
    shot_view(page, "de_plp_top", "DE PLP 상단")

    de_url = page.evaluate("""() => {
        const a = [...document.querySelectorAll('a')]
          .map(e => e.getAttribute('href') || '')
          .filter(h => /\\/de\\/.+\\/(oled|qned|nano)[a-z0-9-]*\\/[a-z0-9]{6,}\\/?$/i.test(h));
        return a.length ? a[0] : null;
    }""")
    print("DE PDP URL:", de_url)

    if de_url:
        if not de_url.startswith("http"):
            de_url = "https://www.lg.com" + de_url
        page.goto(de_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(4000)
        prep(page)
        shot_view(page, "de_pdp_hero", "DE PDP 상단 — Energieeffizienzklasse / Preis")
        shot_el(page, "de_pdp_keyspec", "DE PDP Key Spec", "bySel", "#pdp-specs-section")
        results.append({"name": "_de_url", "note": de_url, "ok": True})

    br.close()

print(json.dumps(results, ensure_ascii=False, indent=1))
