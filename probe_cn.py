# -*- coding: utf-8 -*-
"""중국 브랜드 TV 사이트 구조 탐색 — PLP/PDP 경로와 콘텐츠 성격 파악."""
import json, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

CANDIDATES = [
    ("tcl_uk",  "https://www.tcl.com/uk/en/tvs"),
    ("tcl_global", "https://www.tcl.com/global/en/products/home-entertainment"),
    ("hisense_uk", "https://hisense.co.uk/televisions/"),
    ("hisense_uk2", "https://hisense.co.uk/product-category/televisions/"),
    ("xiaomi_th", "https://www.mi.com/th/product-list/tv/"),
    ("tcl_br", "https://www.tcl.com/br/pt/tvs"),
]

KILL = """() => {
  let n=0;
  document.querySelectorAll('div,section,aside,dialog').forEach(el=>{
    const t=el.innerText||''; if(t.length>3000) return;
    if(/Accept|Aceitar|ยอมรับ|Alle akzeptieren/i.test(t) && /Decline|Reject|Recusar|ปฏิเสธ|Ablehnen|Settings|Manage/i.test(t)){
      el.style.setProperty('display','none','important'); n++; }
  });
  document.querySelectorAll('body *').forEach(el=>{
    const cs=getComputedStyle(el); if(cs.display==='none') return;
    const r=el.getBoundingClientRect();
    if(cs.position==='fixed' && r.width>innerWidth*0.5 && r.height>innerHeight*0.4){
      el.style.setProperty('display','none','important'); n++; }
  });
  for(const e of [document.documentElement, document.body]){
    e.style.setProperty('overflow','auto','important');
    e.style.setProperty('position','static','important'); }
  return n;
}"""

PROBE = """() => {
  const t = document.body.innerText;
  const filters = [...new Set([...document.querySelectorAll('button,label,legend,h3,h4,summary')]
    .map(e=>(e.textContent||'').trim().replace(/\\s+/g,' '))
    .filter(x=>x.length>1 && x.length<34))];
  return {
    title: document.title.slice(0,70),
    len: (document.querySelector('main')||document.body).innerText.length,
    hzFilter: filters.filter(x=>/\\d{2,3}\\s*Hz|Refresh|refresh/i.test(x)).slice(0,6),
    filterish: filters.filter(x=>/Size|Screen|Price|Resolution|Series|Filter|Sort|Inch|Panel|Type/i.test(x)).slice(0,12),
    prices: (t.match(/[£€$]\\s?[\\d.,]+|R\\$\\s?[\\d.,]+|฿\\s?[\\d.,]+/g)||[]).slice(0,6),
    hasCompare: /compare|comparar|เปรียบเทียบ|vergleich/i.test(t),
    hasSpecTable: !!document.querySelector('table') || /specification|spec\\b/i.test(t),
    productLinks: [...new Set([...document.querySelectorAll('a')].map(a=>a.getAttribute('href')||'')
      .filter(h=>/tv|television|oled|qled|mini-?led/i.test(h) && /\\d/.test(h)))].slice(0,6)
  };
}"""

out = {}
with sync_playwright() as p:
    br = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
    ctx = br.new_context(viewport={"width": 1400, "height": 860}, locale="en-GB", user_agent=UA)
    page = ctx.new_page()
    page.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
    for key, url in CANDIDATES:
        try:
            r = page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(3500)
            page.evaluate(KILL)
            page.wait_for_timeout(500)
            d = page.evaluate(PROBE)
            d["status"] = r.status if r else 0
            d["url"] = page.url
            out[key] = d
            print(f"\n[{key}] status={d['status']}  len={d['len']}")
            print("  title:", d["title"])
            print("  Hz필터:", d["hzFilter"] or "없음")
            print("  가격:", d["prices"][:4] or "없음")
            print("  비교기능:", d["hasCompare"])
            print("  제품링크:", d["productLinks"][:3])
        except Exception as e:
            print(f"\n[{key}] FAIL {str(e)[:90]}")
            out[key] = {"error": str(e)[:120]}
    br.close()

json.dump(out, open("probe_cn.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\n→ probe_cn.json")
