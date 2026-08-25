# -*- coding: utf-8 -*-
import sys, os
from playwright.sync_api import sync_playwright
from PIL import Image
sys.stdout.reconfigure(encoding="utf-8")
OUT="shots"
UA=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
HIDE='[id*="onetrust" i],[class*="cookie" i][class*="banner" i],[class*="floating" i][class*="bar" i]{display:none!important}'

def viewshot(pg, name):
    p=os.path.join(OUT,name+".png"); pg.screenshot(path=p)
    print("OK", name, os.path.getsize(p)); return p

with sync_playwright() as p:
    br=p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
    ctx=br.new_context(viewport={"width":1280,"height":900}, locale="en-GB", user_agent=UA)
    pg=ctx.new_page()
    pg.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")

    # ---- UK PDP : See All Specs 펼친 상태 ----
    pg.goto("https://www.lg.com/uk/tvs-soundbars/oled-evo/oled65c64la/",
            wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_timeout(4500); pg.add_style_tag(content=HIDE)
    ok = pg.evaluate("""() => {
      const b=[...document.querySelectorAll('button')]
        .find(e=>/See All Specs/i.test(e.textContent||'') && e.offsetParent);
      if(b){b.scrollIntoView({block:'center'}); b.click(); return true;} return false; }""")
    pg.wait_for_timeout(3000)
    ln = pg.evaluate("(document.querySelector('#pdp-specs-section')||document.body).innerText.length")
    print("expanded:", ok, "len:", ln)
    # GAMING 헤딩으로 스크롤 후 뷰포트 캡처
    pg.evaluate("""() => {
      const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT); let n;
      while((n=w.nextNode())) if(/^\s*GAMING\s*$/.test(n.nodeValue||'')){
        n.parentElement.scrollIntoView({block:'start'}); window.scrollBy(0,-90); return; } }""")
    pg.wait_for_timeout(1200)
    viewshot(pg,"uk_pdp_seeall_gaming")

    # ---- UK PLP : 필터 + 카드 ----
    pg.goto("https://www.lg.com/uk/tvs/", wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_timeout(4500); pg.add_style_tag(content=HIDE)
    pg.evaluate("""async()=>{const s=ms=>new Promise(r=>setTimeout(r,ms));
      for(let y=0;y<3000;y+=600){window.scrollTo(0,y);await s(120);} window.scrollTo(0,0); await s(500);}""")
    pg.evaluate("""() => {
      const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT); let n;
      while((n=w.nextNode())) if(/Ultimate Game Experience/.test(n.nodeValue||'')){
        n.parentElement.scrollIntoView({block:'center'}); return; } }""")
    pg.wait_for_timeout(1200)
    f=viewshot(pg,"uk_plp_filter_view")
    im=Image.open(f); im.crop((0,0,470,im.height)).save(os.path.join(OUT,"uk_plp_filter.png"))
    print("OK uk_plp_filter", os.path.getsize(os.path.join(OUT,"uk_plp_filter.png")))
    br.close()
