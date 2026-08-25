# -*- coding: utf-8 -*-
import sys, os, json
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8")
OUT="shots"
UA=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
HIDE='[id*="onetrust" i],[class*="cookie" i][class*="banner" i],[class*="chat" i][class*="widget" i]{display:none!important}'
URL="https://www.lg.com/th/tv-soundbars/oled-evo/oled65c5psa/"

with sync_playwright() as p:
    br=p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
    ctx=br.new_context(viewport={"width":1280,"height":900}, locale="en-GB", user_agent=UA)
    pg=ctx.new_page()
    pg.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
    pg.goto(URL, wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_timeout(5000)
    pg.add_style_tag(content=HIDE)
    pg.evaluate("""async()=>{const s=ms=>new Promise(r=>setTimeout(r,ms));
      for(let y=0;y<6000;y+=700){window.scrollTo(0,y);await s(110);} window.scrollTo(0,0); await s(500);}""")

    info = pg.evaluate("""() => {
      const t=document.body.innerText;
      const spec=document.querySelector('#pdp-specs-section');
      return { discontinued: /เลิกผลิต/.test(t),
               prices: (t.match(/฿\s?[\d,]+/g)||[]).slice(0,6),
               specLen: spec?spec.innerText.length:0,
               hasMM: spec? /mm/.test(spec.innerText):false };
    }""")
    print(json.dumps(info, ensure_ascii=False))

    ok = pg.evaluate("""() => { const e=document.querySelector('#pdp-specs-section');
      if(e){ e.scrollIntoView({block:'center'}); return true;} return false; }""")
    pg.wait_for_timeout(1500)
    pg.screenshot(path=os.path.join(OUT,"th_pdp_spec.png"))
    print("spec shot", ok, os.path.getsize(os.path.join(OUT,"th_pdp_spec.png")))

    # 단종 배지 + 4중 가격 영역
    pg.evaluate("window.scrollTo(0,0)"); pg.wait_for_timeout(900)
    pg.screenshot(path=os.path.join(OUT,"th_pdp_price.png"))
    print("price shot", os.path.getsize(os.path.join(OUT,"th_pdp_price.png")))
    br.close()
