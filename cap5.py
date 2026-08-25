# -*- coding: utf-8 -*-
import sys, os, json
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8")
OUT="shots"
UA=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
HIDE='[id*="onetrust" i],[class*="cookie" i][class*="banner" i],[class*="chat" i][class*="widget" i],[class*="floating" i][class*="bar" i]{display:none!important}'

JOBS=[
 ("br_plp","https://www.lg.com/br/tvs-e-soundbars/todas-tvs-soundbars/",None,None),
 ("br_pdp","https://www.lg.com/br/tvs-e-soundbars/oled-evo/oled55c6psa/",None,"#pdp-specs-section"),
 ("br_404","https://www.lg.com/br/tvs/",None,None),
 ("sam_plp","https://www.samsung.com/uk/tvs/all-tvs/","120Hz Motion",None),
]
with sync_playwright() as p:
    br=p.chromium.launch(headless=False,args=["--disable-blink-features=AutomationControlled"])
    ctx=br.new_context(viewport={"width":1280,"height":900},locale="en-GB",user_agent=UA)
    pg=ctx.new_page()
    pg.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
    for name,url,needle,sel in JOBS:
        try:
            pg.goto(url,wait_until="domcontentloaded",timeout=60000)
            pg.wait_for_timeout(4500)
            pg.add_style_tag(content=HIDE)
            pg.evaluate("""async()=>{const s=ms=>new Promise(r=>setTimeout(r,ms));
              for(let y=0;y<2600;y+=650){window.scrollTo(0,y);await s(120);} window.scrollTo(0,0); await s(400);}""")
            if sel:
                ok=pg.evaluate("(s)=>{const e=document.querySelector(s);if(e){e.scrollIntoView({block:'start'});window.scrollBy(0,-80);return true}return false}",sel)
                if not ok: raise ValueError("sel miss")
                pg.wait_for_timeout(1200)
            elif needle:
                pg.evaluate("""(nd)=>{const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);let n;
                  while((n=w.nextNode())) if((n.nodeValue||'').includes(nd)){n.parentElement.scrollIntoView({block:'center'});return}}""",needle)
                pg.wait_for_timeout(1200)
            path=os.path.join(OUT,name+".png"); pg.screenshot(path=path)
            print("OK  ",name,os.path.getsize(path))
        except Exception as e:
            print("FAIL",name,str(e)[:90])
    br.close()
