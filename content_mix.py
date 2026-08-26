# -*- coding: utf-8 -*-
"""PDP 콘텐츠 구성 분석 — 페이지가 무엇으로 채워져 있는가.

브랜드 서사 / 수상·인증 / 기술 설명 / 구매 결정 지원 / 프로모션 으로 분류해
'콘텐츠는 많은데 구매 결정용이 아니다'를 수치로 만든다.
"""
import json, os, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8")

OUT = "shots"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

TARGETS = [
    ("sam_uk", "https://www.samsung.com/uk/tvs/oled-tv/s95h-77-inch-4k-smart-tv-qe77s99hatxxu/", "Samsung UK · OLED S95H 77\""),
]

CLASSIFY = """() => {
  const BUCKETS = {
    decision: /compare|comparison|vs\\b|which|choose|size guide|dimensions|fits|installation|delivery|warranty|what.s in the box|specs?\\b|refresh rate|hdmi|input lag|energy|running cost|price|finance|instal/i,
    proof:    /award|winner|editor.s choice|rated|certified|verified|review|tested|honoree/i,
    brand:    /experience|immerse|immersive|redefин|redefine|discover|world.s|no\\.?1|innovation|design philosophy|story|vision/i,
    tech:     /processor|ai |algorithm|panel|pixel|dolby|hdr|upscal|engine|technology|booster|atmos/i,
    promo:    /offer|deal|save|free|trade.?up|bundle|discount|voucher|cashback|member/i
  };
  const sections = [...document.querySelectorAll('section, [class*="section" i], [class*="component" i]')];
  const seen = new Set();
  const out = { decision:0, proof:0, brand:0, tech:0, promo:0, other:0 };
  const samples = { decision:[], proof:[], brand:[], tech:[], promo:[] };
  for (const el of sections) {
    if (el.closest('header,nav,footer')) continue;
    const t = (el.innerText || '').trim();
    if (t.length < 60 || t.length > 6000) continue;
    // 중첩 섹션 중복 계산 방지
    let dup = false;
    for (const s of seen) { if (s.contains(el) || el.contains(s)) { dup = true; break; } }
    if (dup) continue;
    seen.add(el);
    const head = t.slice(0, 220);
    let hit = 'other';
    for (const [k, re] of Object.entries(BUCKETS)) { if (re.test(head)) { hit = k; break; } }
    out[hit] += t.length;
    if (samples[hit] && samples[hit].length < 4) samples[hit].push(head.replace(/\\n+/g,' | ').slice(0,90));
  }
  return { buckets: out, samples,
           total: Object.values(out).reduce((a,b)=>a+b,0),
           sectionCount: seen.size,
           footnotes: (document.body.innerText.match(/\\d{1,2}\\)\\s/g)||[]).length,
           pageChars: (document.querySelector('main')||document.body).innerText.length };
}"""

results = {}
with sync_playwright() as p:
    br = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
    ctx = br.new_context(viewport={"width": 1280, "height": 900}, locale="en-GB", user_agent=UA)
    page = ctx.new_page()
    page.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")

    for key, url, label in TARGETS:
        try:
            r = page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(4500)
            page.evaluate("""() => {
              document.querySelectorAll('body *').forEach(el=>{
                const cs=getComputedStyle(el);
                if((cs.position==='fixed'||cs.position==='sticky') && +cs.zIndex>=100){
                  const b=el.getBoundingClientRect();
                  if(b.width>300&&b.height>200) el.style.setProperty('display','none','important');
                }});
              document.documentElement.style.overflow='auto'; document.body.style.overflow='auto';
            }""")
            page.evaluate("""async()=>{const s=ms=>new Promise(r=>setTimeout(r,ms));
              for(let y=0;y<9000;y+=800){window.scrollTo(0,y);await s(140);} window.scrollTo(0,0);await s(500);}""")
            data = page.evaluate(CLASSIFY)
            data["label"] = label
            data["status"] = r.status if r else 0
            results[key] = data
            page.screenshot(path=os.path.join(OUT, f"mix_{key}.png"))
            b = data["buckets"]; tot = max(data["total"], 1)
            print(f"\n{label}  (status {data['status']}, 섹션 {data['sectionCount']}, 각주 {data['footnotes']})")
            for k in ["decision", "proof", "brand", "tech", "promo", "other"]:
                print(f"   {k:<9} {b[k]:>6}자  {b[k]/tot*100:5.1f}%")
        except Exception as e:
            print("FAIL", key, str(e)[:110])
    br.close()

json.dump(results, open("content_mix.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\n→ content_mix.json")
