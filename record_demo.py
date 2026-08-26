# -*- coding: utf-8 -*-
"""P01(게이머)이 lg.com 에서 막히는 과정을 실제 세션으로 녹화.

자막은 브라우저 폰트에 의존하지 않는다 — PIL 로 PNG 를 만들어 주입한다.
(lg.com CSP 가 외부 웹폰트를 막고, 크로미움에 한글 폰트가 없어 자모가 분리되는 문제 회피)
쿠키 동의/거부 버튼은 누르지 않고 오버레이만 제거한다.
"""
import base64, io as _io, os, shutil, sys
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")

OUT = "video"
if os.path.isdir(OUT):
    shutil.rmtree(OUT)
os.makedirs(OUT)

W, H = 960, 580
BAR_H = 66
FONT = "C:/Windows/Fonts/malgun.ttf"
FONT_B = "C:/Windows/Fonts/malgunbd.ttf"
f_txt = ImageFont.truetype(FONT, 19)
f_pill = ImageFont.truetype(FONT_B if os.path.exists(FONT_B) else FONT, 14)
f_num = ImageFont.truetype(FONT, 14)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def caption_png(pill: str, text: str, n: int, total: int) -> str:
    """자막 바를 PNG data URI 로."""
    im = Image.new("RGB", (W, BAR_H), (14, 16, 18))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 2], fill=(165, 0, 52))          # 상단 라인
    # 페르소나 칩
    pw = d.textbbox((0, 0), pill, font=f_pill)[2] + 20
    d.rounded_rectangle([18, 20, 18 + pw, 46], 4, fill=(165, 0, 52))
    d.text((28, 26), pill, font=f_pill, fill=(255, 255, 255))
    # 본문
    d.text((18 + pw + 16, 22), text, font=f_txt, fill=(255, 255, 255))
    # 단계 카운터
    cnt = f"{n} / {total}"
    cw = d.textbbox((0, 0), cnt, font=f_num)[2]
    d.text((W - cw - 20, 26), cnt, font=f_num, fill=(154, 160, 166))
    buf = _io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


INIT = r"""
window.__cap = (src) => {
  let img = document.getElementById('__capimg');
  if (!img) {
    img = document.createElement('img');
    img.id = '__capimg';
    img.style.cssText = `position:fixed;left:0;bottom:0;width:100%;z-index:2147483647;
      display:block;box-shadow:0 -6px 24px rgba(0,0,0,.35)`;
    document.body.appendChild(img);
    document.body.style.paddingBottom = '70px';
  }
  img.src = src;
};
window.__mark = (needle) => {
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let node;
  while ((node = w.nextNode())) {
    if ((node.nodeValue || '').includes(needle)) {
      let el = node.parentElement;
      if (!el || el.id === '__capimg') continue;
      for (let i = 0; i < 2 && el.parentElement; i++) {
        if (el.getBoundingClientRect().height > 26) break;
        el = el.parentElement;
      }
      el.scrollIntoView({ block: 'center' });
      el.style.outline = '3px solid #A50034';
      el.style.outlineOffset = '3px';
      el.style.background = 'rgba(165,0,52,.10)';
      return true;
    }
  }
  return false;
};
window.__freeze = () => {
  document.querySelectorAll('video').forEach(v => {
    try { v.pause(); v.autoplay = false; v.removeAttribute('autoplay'); } catch (e) {}
  });
  if (!document.getElementById('__fz')) {
    const st = document.createElement('style');
    st.id = '__fz';
    st.textContent = `*,*::before,*::after{animation:none !important;
      transition:none !important;scroll-behavior:auto !important}`;
    document.head.appendChild(st);
  }
};
window.__kill = () => {
  document.querySelectorAll('div,section,aside,dialog').forEach(el => {
    const t = el.innerText || '';
    if (t.length > 3000) return;
    if (/Accept|Allow/i.test(t) && /Decline|Reject|Refuse|Manage|Settings|Necessary/i.test(t))
      el.style.setProperty('display', 'none', 'important');
  });
  document.querySelectorAll('body *').forEach(el => {
    if (el.id === '__capimg') return;
    const cs = getComputedStyle(el);
    if (cs.display === 'none') return;
    const r = el.getBoundingClientRect();
    if (cs.position === 'fixed' && r.width > innerWidth * .5 && r.height > innerHeight * .4)
      el.style.setProperty('display', 'none', 'important');
  });
  for (const e of [document.documentElement, document.body]) {
    e.style.setProperty('overflow', 'auto', 'important');
    e.style.setProperty('position', 'static', 'important');
  }
};
"""

TOTAL = 11

with sync_playwright() as p:
    br = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
    ctx = br.new_context(viewport={"width": W, "height": H}, locale="en-GB", user_agent=UA,
                         record_video_dir=OUT, record_video_size={"width": W, "height": H})
    page = ctx.new_page()
    page.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
    page.add_init_script(INIT)

    def say(n, txt, pill="P01 · 게이머"):
        page.evaluate("window.__freeze()")
        page.evaluate("(s)=>window.__cap(s)", caption_png(pill, txt, n, TOTAL))
        page.wait_for_timeout(300)
        page.screenshot(path=os.path.join(OUT, f"step{n:02d}.png"))

    def wait(ms): page.wait_for_timeout(ms)

    def clean():
        for _ in range(3):
            page.evaluate("window.__kill(); window.__freeze()")
            page.wait_for_timeout(350)

    page.goto("https://www.lg.com/uk/tvs/", wait_until="domcontentloaded", timeout=60000)
    wait(3800); clean()
    say(1, "lg.com/uk 진입. 4K 165Hz 게이밍 TV를 찾는다."); wait(2100)

    say(2, "게이밍 필터가 있는지 본다."); wait(1000)
    page.evaluate("window.__mark('Ultimate Game Experience')"); wait(2200)

    say(3, "ALLM · FreeSync · G-Sync 뿐. 주사율로는 후보를 좁힐 수 없다."); wait(2900)

    cnt = page.evaluate("""()=>{const m=(document.body.innerText||'').match(/(\d+)\s*Results/i);
      return m?m[1]:null;}""")
    say(4, (f"결국 {cnt}개를 직접 훑는다. C6 상세로 들어간다." if cnt
            else "결국 목록 전체를 직접 훑는다. C6 상세로 들어간다.")); wait(1600)
    page.goto("https://www.lg.com/uk/tvs-soundbars/oled-evo/oled65c64la/",
              wait_until="domcontentloaded", timeout=60000)
    wait(3800); clean()

    say(5, "상단 Key Features 를 확인한다."); wait(1000)
    page.evaluate("window.__mark('Up to 165Hz')"); wait(2600)

    say(6, "165Hz 라고 한다. 스펙표에서 확인해 본다."); wait(1600)
    page.evaluate("()=>{const e=document.querySelector('#pdp-specs-section'); if(e) e.scrollIntoView({block:'center'});}")
    wait(1500)

    say(7, "스펙표는 120Hz Native 라고 쓴다. 위와 다른 숫자다."); wait(900)
    page.evaluate("window.__mark('120Hz Native')"); wait(2900)

    before = page.evaluate("(document.querySelector('#pdp-specs-section')||document.body).innerText.length")
    say(8, "포트별 HDMI 규격이 없다. See All Specs 를 눌러 본다."); wait(1800)
    page.evaluate("""()=>{const b=[...document.querySelectorAll('button')]
      .find(e=>/See All Specs/i.test(e.textContent||'') && e.offsetParent);
      if(b){ b.scrollIntoView({block:'center'}); b.click(); }}""")
    wait(2600); clean()
    after = page.evaluate("(document.querySelector('#pdp-specs-section')||document.body).innerText.length")

    say(9, f"펼치니 {before:,}자 → {after:,}자. 응답속도와 HFR 이 여기 있었다."); wait(1000)
    page.evaluate("window.__mark('Response Time')"); wait(2900)

    say(10, "치수는 1441 x 826 x 45.1 — 단위가 없다."); wait(900)
    page.evaluate("window.__mark('1441 x 826')"); wait(2900)

    say(11, "HDMI 포트 규격은 끝내 없다. 포럼에서 찾기로 하고 창을 닫는다.", "P01 · 이탈")
    wait(3200)

    ctx.close(); br.close()

for v in [f for f in os.listdir(OUT) if f.endswith(".webm")]:
    src, dst = os.path.join(OUT, v), os.path.join(OUT, "redteam-demo.webm")
    if src != dst:
        os.rename(src, dst)
    print("영상:", dst, os.path.getsize(dst) // 1024, "KB")
