# -*- coding: utf-8 -*-
import sys, os
from playwright.sync_api import sync_playwright
from PIL import Image
sys.stdout.reconfigure(encoding="utf-8")
OUT="shots"
UA=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
HIDE='[id*="onetrust" i],[class*="cookie" i][class*="banner" i],[class*="floating" i][class*="bar" i],[class*="chat" i][class*="widget" i]{display:none!important}'

TARGETS = [
  ("th_plp",        "https://www.lg.com/th/tvs/", None, None),
  ("th_guide_hub",  "https://www.lg.com/th/tvs-soundbars/tv-buying-guide/", None, None),
  ("th_guide_game", "https://www.lg.com/th/tvs-soundbars/tv-buying-guide/gaming-tv/", "เรียนรู้เพิ่มเติม", None),
  ("th_promo",      "https://www.lg.com/th/promotions/", None, None),
  ("th_pdp_hero",   "https://www.lg.com/th/tv-soundbars/oled-evo/oled65c5psa/", None, None),
  ("th_pdp_spec",   None, None, "#pdp-specs-section"),
  ("uk_lineup",     "https://www.lg.com/uk/buying-guides/tv-lineup-guide/", "ALL TVs Summary", None),
  ("uk_promo",      "https://www.lg.com/uk/promotion/", None, None),
]

def scrollto(pg, needle):
    pg.evaluate("""(needle) => {
      const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT); let n;
      while((n=w.nextNode())) if((n.nodeValue||'').includes(needle)){
        n.parentElement.scrollIntoView({block:'start'}); window.scrollBy(0,-100); return true; }
      return false; }""", needle)

with sync_playwright() as p:
    br=p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
    ctx=br.new_context(viewport={"width":1280,"height":900}, locale="en-GB", user_agent=UA)
    pg=ctx.new_page()
    pg.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
    for name, url, needle, sel in TARGETS:
        try:
            if url:
                pg.goto(url, wait_until="domcontentloaded", timeout=60000)
                pg.wait_for_timeout(4500)
                pg.add_style_tag(content=HIDE)
                pg.evaluate("""async()=>{const s=ms=>new Promise(r=>setTimeout(r,ms));
                  for(let y=0;y<2600;y+=650){window.scrollTo(0,y);await s(120);} window.scrollTo(0,0); await s(400);}""")
            if sel:
                ok = pg.evaluate("(s)=>{const e=document.querySelector(s); if(e){e.scrollIntoView({block:'start'});window.scrollBy(0,-90);return true;} return false;}", sel)
                if not ok: raise ValueError("sel not found "+sel)
                pg.wait_for_timeout(1200)
            elif needle:
                scrollto(pg, needle); pg.wait_for_timeout(1200)
            path=os.path.join(OUT,name+".png"); pg.screenshot(path=path)
            print("OK  ", name, os.path.getsize(path))
        except Exception as e:
            print("FAIL", name, str(e)[:110])
    br.close()
