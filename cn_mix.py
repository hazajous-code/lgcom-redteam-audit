# -*- coding: utf-8 -*-
"""중국 브랜드 PDP 콘텐츠 구성 분석 — LG·삼성과 동일 기준."""
import json, os, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8")

OUT = "shots"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

STEPS = [
    ("tcl_uk_plp",  "https://www.tcl.com/uk/en/tvs/4k-tv",                              "plp",  "TCL UK · 4K TV 목록"),
    ("hs_uk_plp",   "https://uk.hisense.com/products/tv/uled-miniled-tv/c/hisensetv02", "plp",  "Hisense UK · ULED Mini LED 목록"),
]

KILL = """() => {
  let n=0;
  document.querySelectorAll('div,section,aside,dialog').forEach(el=>{
    const t=el.innerText||''; if(t.length>3000) return;
    if(/Accept|Allow|Aceitar|Alle akzeptieren/i.test(t) && /Decline|Reject|Manage|Settings|Necessary|Recusar/i.test(t)){
      el.style.setProperty('display','none','important'); n++; }
  });
  document.querySelectorAll('body *').forEach(el=>{
    const cs=getComputedStyle(el); if(cs.display==='none') return;
    const r=el.getBoundingClientRect();
    const covers = r.width>innerWidth*0.5 && r.height>innerHeight*0.4;
    if((cs.position==='fixed' && covers) ||
       (/cookie|consent|modal|overlay|backdrop/i.test((el.className||'')+' '+(el.id||'')) && covers)){
      el.style.setProperty('display','none','important'); n++; }
  });
  for(const e of [document.documentElement, document.body]){
    e.style.setProperty('overflow','auto','important');
    e.style.setProperty('position','static','important'); }
  return n;
}"""

PLP_PROBE = """() => {
  const t=document.body.innerText;
  const labels=[...new Set([...document.querySelectorAll('button,label,legend,h3,h4,summary,option')]
    .map(e=>(e.textContent||'').trim().replace(/\\s+/g,' ')).filter(x=>x.length>1&&x.length<40))];
  return {
    title: document.title.slice(0,70),
    hzAnywhere: (t.match(/\\d{2,3}\\s*Hz/g)||[]).slice(0,8),
    hzFilter: labels.filter(x=>/\\d{2,3}\\s*Hz|Refresh/i.test(x)).slice(0,8),
    prices: (t.match(/[£€$]\\s?[\\d.,]+|R\\$\\s?[\\d.,]+/g)||[]).slice(0,8),
    specInCard: (t.match(/\\d{2,3}Hz|QLED|Mini LED|Dolby Vision|HDMI\\s*2\\.1|144Hz|VRR/gi)||[]).slice(0,10),
    compare: /compare/i.test(t),
    pdp: [...new Set([...document.querySelectorAll('a')].map(a=>a.getAttribute('href')||'')
      .filter(h=>/\\/(p|product)\\/|\\d{2}[a-z]\\d|-tv-|\\/tvs?\\/.+\\d/i.test(h)))].slice(0,8)
  };
}"""

out={}
with sync_playwright() as p:
    br=p.chromium.launch(headless=False,args=["--disable-blink-features=AutomationControlled"])
    ctx=br.new_context(viewport={"width":1400,"height":860},locale="en-GB",user_agent=UA)
    page=ctx.new_page()
    page.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
    for key,url,kind,label in STEPS:
        try:
            r=page.goto(url,wait_until="domcontentloaded",timeout=45000)
            page.wait_for_timeout(4000)
            for _ in range(3):
                page.evaluate(KILL); page.wait_for_timeout(500)
            page.evaluate("""async()=>{const s=ms=>new Promise(r=>setTimeout(r,ms));
              for(let y=0;y<3000;y+=700){window.scrollTo(0,y);await s(140);} window.scrollTo(0,0);await s(400);}""")
            d=page.evaluate(PLP_PROBE); d["status"]=r.status if r else 0; d["label"]=label
            out[key]=d
            page.screenshot(path=os.path.join(OUT,f"{key}.png"))
            print(f"\n[{label}] status={d['status']}")
            print("  Hz 노출:", d["hzAnywhere"][:5] or "없음")
            print("  Hz 필터:", d["hzFilter"] or "없음")
            print("  가격:", d["prices"][:4] or "없음")
            print("  카드 스펙:", d["specInCard"][:6] or "없음")
            print("  PDP:", d["pdp"][:3])
        except Exception as e:
            print(f"\n[{label}] FAIL {str(e)[:100]}")
    br.close()
json.dump(out,open("cn_mix.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
print("\n→ cn_mix.json")
