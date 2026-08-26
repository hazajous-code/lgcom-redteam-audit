# -*- coding: utf-8 -*-
"""삼성 PDP 재캡처 — 컨센트 오버레이를 클릭하지 않고 제거한 상태로."""
import json, os, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8")

OUT = "shots"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
URL = "https://www.samsung.com/uk/tvs/oled-tv/s95h-77-inch-4k-smart-tv-qe77s99hatxxu/"

# 동의/거부 어떤 버튼도 누르지 않는다. 화면을 덮는 레이어만 제거한다.
# 동의/거부 버튼은 절대 클릭하지 않는다. 컨센트 DOM 노드 자체를 제거한다.
KILL_OVERLAY = """() => {
  let n = 0;
  const nuke = el => { el.style.setProperty('display','none','important'); n++; };

  // 1) 'Accept All' + 'Decline All' 을 함께 품은 가장 바깥 컨테이너를 찾아 제거
  const all = [...document.querySelectorAll('div,section,aside,dialog')];
  for (const el of all) {
    const t = el.innerText || '';
    if (t.length > 3000) continue;
    if (/Accept All/i.test(t) && /Decline All/i.test(t)) {
      let top = el;
      while (top.parentElement && top.parentElement !== document.body) {
        const pt = top.parentElement.innerText || '';
        if (pt.length > 4000) break;
        top = top.parentElement;
      }
      nuke(top);
    }
  }

  // 2) 화면을 덮는 고정 레이어 · 백드롭
  document.querySelectorAll('body *').forEach(el => {
    const cs = getComputedStyle(el);
    if (cs.display === 'none') return;
    const r = el.getBoundingClientRect();
    const covers = r.width > innerWidth * 0.5 && r.height > innerHeight * 0.4;
    const fixed = cs.position === 'fixed';
    const dim = /rgba?\([^)]*0?\.[1-9]/.test(cs.backgroundColor) && covers;
    const modalish = el.getAttribute('role') === 'dialog'
                  || el.getAttribute('aria-modal') === 'true'
                  || /cookie|consent|backdrop|dimmed|overlay/i.test((el.className||'') + ' ' + (el.id||''));
    if ((fixed && covers) || dim || (modalish && covers)) nuke(el);
  });

  // 3) 스크롤 잠금 해제
  for (const e of [document.documentElement, document.body]) {
    e.style.setProperty('overflow','auto','important');
    e.style.setProperty('position','static','important');
  }
  return n;
}"""

with sync_playwright() as p:
    br = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
    ctx = br.new_context(viewport={"width": 1480, "height": 780}, locale="en-GB", user_agent=UA)
    page = ctx.new_page()
    page.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")

    r = page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(5500)
    killed = 0
    for i in range(6):                       # 지연 삽입 레이어 대비 반복
        killed += page.evaluate(KILL_OVERLAY)
        page.wait_for_timeout(700)

    info = page.evaluate("""() => {
      const t = document.body.innerText;
      const alt = t.indexOf('Looking for alternatives');
      return {
        status: 'ok',
        title: document.title.slice(0, 60),
        hasAlternatives: alt >= 0,
        altBlock: alt >= 0 ? t.slice(alt, alt + 320).replace(/\\n+/g, ' | ') : null,
        prices: (t.match(/£[\\d,]+\\.\\d{2}/g) || []).slice(0, 8),
        stillOverlay: [...document.querySelectorAll('body *')].filter(el => {
          const cs = getComputedStyle(el);
          const rr = el.getBoundingClientRect();
          return cs.position === 'fixed' && +cs.zIndex >= 100
                 && rr.width > 300 && rr.height > 200 && cs.display !== 'none';
        }).length
      };
    }""")
    print("overlays removed:", killed)
    print(json.dumps(info, ensure_ascii=False, indent=1))

    page.evaluate("window.scrollTo(0,0)")
    page.wait_for_timeout(500)
    page.screenshot(path=os.path.join(OUT, "sam_pdp_clean.png"))
    print("sam_pdp_clean:", os.path.getsize(os.path.join(OUT, "sam_pdp_clean.png")))
    br.close()
