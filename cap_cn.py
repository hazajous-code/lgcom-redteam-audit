# -*- coding: utf-8 -*-
"""Hisense 주사율 필터 · TCL 스펙 전면 카드 캡처."""
import json, os, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8")

OUT = "shots"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

KILL = """() => {
  let n=0;
  document.querySelectorAll('div,section,aside,dialog').forEach(el=>{
    const t=el.innerText||''; if(t.length>3000) return;
    if(/Accept|Allow/i.test(t) && /Decline|Reject|Refuse|Manage|Settings|Necessary|Cookie setting/i.test(t)){
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

def prep(page, rounds=3):
    for _ in range(rounds):
        page.evaluate(KILL); page.wait_for_timeout(500)

with sync_playwright() as p:
    br = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
    ctx = br.new_context(viewport={"width": 1400, "height": 860}, locale="en-GB", user_agent=UA)
    page = ctx.new_page()
    page.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")

    # ── TCL: 스펙이 카드 전면에 노출된 목록 ──
    page.goto("https://www.tcl.com/uk/en/tvs/4k-tv", wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(4500); prep(page)
    page.evaluate("""() => {
      const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT); let n;
      while((n=w.nextNode())) if(/144Hz/.test(n.nodeValue||'')){
        n.parentElement.scrollIntoView({block:'center'}); window.scrollBy(0,-140); return; }
    }""")
    page.wait_for_timeout(1200); prep(page, 1)
    page.screenshot(path=os.path.join(OUT, "tcl_cards.png"))
    print("  tcl_cards:", os.path.getsize(os.path.join(OUT, "tcl_cards.png")))
    br.close()
