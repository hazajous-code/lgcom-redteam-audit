# -*- coding: utf-8 -*-
import sys, os
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8")
OUT="shots"
UA=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
with sync_playwright() as p:
    br=p.chromium.launch(headless=False,args=["--disable-blink-features=AutomationControlled"])
    ctx=br.new_context(viewport={"width":1280,"height":900},locale="en-GB",user_agent=UA)
    pg=ctx.new_page()
    pg.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
    pg.goto("https://www.samsung.com/uk/tvs/all-tvs/",wait_until="domcontentloaded",timeout=60000)
    pg.wait_for_timeout(5000)
    # 동의/거부 어떤 버튼도 클릭하지 않고, 화면을 덮는 오버레이만 CSS 로 숨김
    hidden = pg.evaluate("""() => {
      let n=0;
      document.querySelectorAll('body *').forEach(el=>{
        const cs=getComputedStyle(el);
        if((cs.position==='fixed'||cs.position==='sticky') && +cs.zIndex>=100){
          const r=el.getBoundingClientRect();
          if(r.width>300 && r.height>200){ el.style.setProperty('display','none','important'); n++; }
        }
      });
      document.documentElement.style.overflow='auto';
      document.body.style.overflow='auto';
      return n;
    }""")
    print("overlays hidden:", hidden)
    pg.wait_for_timeout(600)
    pg.evaluate("""()=>{const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);let n;
      while((n=w.nextNode())) if((n.nodeValue||'').includes('83 Results')){
        n.parentElement.scrollIntoView({block:'start'}); window.scrollBy(0,-70); return}}""")
    pg.wait_for_timeout(1000)
    pg.screenshot(path=os.path.join(OUT,"sam_plp.png"))
    print("sam_plp", os.path.getsize(os.path.join(OUT,"sam_plp.png")))
    # 게이밍 필터 펼친 상태
    opened = pg.evaluate("""()=>{const b=[...document.querySelectorAll('button')]
      .find(e=>/^\s*Features\s*$/.test(e.textContent||''));
      if(b){b.scrollIntoView({block:'center'});b.click();return true}return false}""")
    pg.wait_for_timeout(1800)
    pg.screenshot(path=os.path.join(OUT,"sam_filter.png"))
    print("sam_filter", opened, os.path.getsize(os.path.join(OUT,"sam_filter.png")))
    br.close()
