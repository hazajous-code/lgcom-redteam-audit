# -*- coding: utf-8 -*-
"""
redteam runner — 화면은 1번만 뜨고, 페르소나는 N개 돌린다.

회의에서 나온 "수천 개 에이전트를 동시에 뿌린다"는 그대로는 성립하지 않는다.
lg.com 은 엣지(Akamai)에서 headless 브라우저를 403 으로 막기 때문에
브라우저를 N번 띄우는 순간 그게 병목이자 비용이 된다.

그래서 두 단계로 나눈다.

  1) snapshot  실제(headed) 브라우저로 화면을 '한 번' 순회하며
               접힌 요소를 펼친 뒤 DOM 텍스트와 캡처를 저장한다.
  2) evaluate  저장된 스냅샷 위에서 페르소나 N개를 '병렬로' 평가한다.
               이 단계에는 브라우저가 필요 없다. 비용은 모델 호출량뿐이다.

이 구조면 페르소나를 100개에서 1,000개로 늘려도 브라우저는 그대로 1대다.

사용법
    pip install playwright anthropic && playwright install chromium
    set ANTHROPIC_API_KEY=...

    python runner.py snapshot --config targets.json
    python runner.py evaluate --personas personas.json --workers 8
    python runner.py report
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import dataclasses
import json
import os
import pathlib
import re
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

ROOT = pathlib.Path(__file__).resolve().parent
SNAP_DIR = ROOT / "snapshots"
OUT_DIR = ROOT / "results"

# 평가는 호출량이 많으므로 중간 모델, 종합은 상위 모델을 쓴다.
EVAL_MODEL = "claude-sonnet-5"
SYNTH_MODEL = "claude-opus-5"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# 동의/거부 버튼은 절대 클릭하지 않는다. 화면을 덮는 오버레이만 CSS 로 숨긴다.
HIDE_OVERLAY = """() => {
  let n = 0;
  document.querySelectorAll('body *').forEach(el => {
    const cs = getComputedStyle(el);
    if ((cs.position === 'fixed' || cs.position === 'sticky') && +cs.zIndex >= 100) {
      const r = el.getBoundingClientRect();
      if (r.width > 300 && r.height > 200) { el.style.setProperty('display','none','important'); n++; }
    }
  });
  document.documentElement.style.overflow = 'auto';
  document.body.style.overflow = 'auto';
  return n;
}"""

# 접힌 것을 펼치지 않으면 스펙의 15% 만 관측된다 (UK PDP 674자 → 4,531자).
EXPAND = """() => {
  // 헤더·내비의 드롭다운까지 누르면 느려지고 페이지가 이동할 수 있다.
  // 본문과 스펙 영역으로만 범위를 좁힌다.
  const LABELS = /See All Specs|Alle Spezifikationen|ดูข้อมูลจำเพาะทั้งหมด|Todas as especifica|Ver todas/i;
  const scopes = [document.querySelector('#pdp-specs-section'),
                  document.querySelector('main')].filter(Boolean);
  if (!scopes.length) scopes.push(document.body);
  const inChrome = el => el.closest('header,nav,footer,[role="banner"],[role="navigation"]');
  let clicked = 0;
  for (const sc of scopes) {
    sc.querySelectorAll('button,a,[role="button"]').forEach(b => {
      if (clicked < 40 && LABELS.test(b.textContent || '') && b.offsetParent && !inChrome(b)) {
        b.click(); clicked++;
      }
    });
    sc.querySelectorAll('[aria-expanded="false"]').forEach(b => {
      if (clicked < 40 && b.offsetParent && !inChrome(b)) {
        try { b.click(); clicked++; } catch (e) {}
      }
    });
  }
  return clicked;
}"""

PROBE = """() => {
  const specs = document.querySelector('#pdp-specs-section');
  const acc = [...document.querySelectorAll('[aria-expanded]')];
  return {
    title: document.title,
    url: location.href,
    text: (document.querySelector('main') || document.body).innerText,
    specText: specs ? specs.innerText : '',
    accordions: acc.length,
    expanded: acc.filter(b => b.getAttribute('aria-expanded') === 'true').length,
    footnotes: (document.body.innerText.match(/\\d{1,2}\\)\\s/g) || []).length,
    prices: (document.body.innerText.match(/[£€$฿]\\s?[\\d.,]+|R\\$\\s?[\\d.,]+/g) || []).slice(0, 8),
    links: [...document.querySelectorAll('main a, a')].map(a => a.getAttribute('href') || '')
             .filter(h => h && !h.startsWith('#')).slice(0, 400),
  };
}"""


# ────────────────────────────── 1) SNAPSHOT ──────────────────────────────
def cmd_snapshot(args):
    from playwright.sync_api import sync_playwright

    targets = json.loads(pathlib.Path(args.config).read_text(encoding="utf-8"))
    SNAP_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        # headless=False 가 필수. headless 는 엣지에서 403 이다.
        browser = p.chromium.launch(
            headless=False, args=["--disable-blink-features=AutomationControlled"])
        ctx = browser.new_context(viewport={"width": 1280, "height": 900}, user_agent=UA)
        page = ctx.new_page()
        page.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")

        for t in targets:
            key = t["key"]
            try:
                resp = page.goto(t["url"], wait_until="domcontentloaded", timeout=60000)
                status = resp.status if resp else 0
                page.wait_for_timeout(3000)
                page.evaluate(HIDE_OVERLAY)
                page.evaluate("""async () => {
                    const s = ms => new Promise(r => setTimeout(r, ms));
                    for (let y = 0; y < 2200; y += 700) { window.scrollTo(0, y); await s(120); }
                    window.scrollTo(0, 0); await s(400);
                }""")

                before = page.evaluate("(document.querySelector('#pdp-specs-section')||document.body).innerText.length")
                clicked = page.evaluate(EXPAND)
                page.wait_for_timeout(1800)
                probe = page.evaluate(PROBE)
                probe.update({
                    "key": key, "status": status, "country": t.get("country"),
                    "kind": t.get("kind"), "expandClicked": clicked,
                    "specLenBefore": before, "specLenAfter": len(probe["specText"]),
                    "capturedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
                })
                page.screenshot(path=str(SNAP_DIR / f"{key}.png"))
                (SNAP_DIR / f"{key}.json").write_text(
                    json.dumps(probe, ensure_ascii=False), encoding="utf-8")
                print(f"OK   {key:<16} status={status} acc={probe['accordions']}/"
                      f"{probe['expanded']} spec={before}→{probe['specLenAfter']}")
            except Exception as e:
                print(f"FAIL {key:<16} {str(e)[:90]}")

        browser.close()


# ────────────────────────────── 2) EVALUATE ──────────────────────────────
SYSTEM = """당신은 lg.com 에 실제로 들어온 고객 한 명이다. 마케터가 아니다.

주어진 것은 당신이 지금 보고 있는 화면의 텍스트다. 여기 없는 정보는 화면에 없는 것이다.
추측해서 채우지 마라. "아마 어딘가 있겠지"라고 생각하지 마라.

당신의 과업을 끝내려면 무엇을 알아야 하는지 먼저 정하고,
그 정보가 이 화면에 있는지 확인하라.

없다면 당신은 막힌 것이다. 막혔다면 실제 사람처럼 반응하라.
다른 사이트로 갈 수도, 매장에 가기로 마음먹을 수도, 그냥 창을 닫을 수도 있다.

반드시 아래 JSON 만 출력하라. 다른 말은 쓰지 마라.
{
  "completed": true | false,
  "friction": 1-10 정수,
  "blocked_on": "무엇을 확인하지 못했는가 (없으면 null)",
  "missing_content": "그 자리에 무엇이 있었어야 하는가 (없으면 null)",
  "evidence": "화면에서 근거가 된 문자열을 그대로 인용 (없으면 null)",
  "next_action": "continue | external_search | competitor | offline_store | ask_someone | abandon",
  "voc": "이탈 직전 혼잣말 한두 문장. 실제 말투로."
}"""


def evaluate_one(client, persona, snap):
    text = snap["text"][:14000]
    spec = snap["specText"][:6000]
    prompt = f"""[당신]
{persona['profile']}

[오늘의 과업]
{persona['task']}

[지금 보고 있는 화면]
국가: {snap.get('country')}   화면 종류: {snap.get('kind')}
URL: {snap['url']}
제목: {snap['title']}

--- 본문 ---
{text}

--- 스펙 영역 (접힌 것을 펼친 뒤) ---
{spec if spec else '(이 화면에는 스펙 영역이 없다)'}
"""
    msg = client.messages.create(
        model=EVAL_MODEL,
        max_tokens=900,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text.strip()
    m = re.search(r"\{.*\}", raw, re.S)
    result = json.loads(m.group(0)) if m else {"parse_error": raw[:300]}
    result.update({
        "persona_id": persona["id"], "persona": persona["profile"][:60],
        "screen": snap["key"], "country": snap.get("country"), "kind": snap.get("kind"),
    })
    return result


def cmd_evaluate(args):
    from anthropic import Anthropic

    client = Anthropic()
    personas = json.loads(pathlib.Path(args.personas).read_text(encoding="utf-8"))
    snaps = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(SNAP_DIR.glob("*.json"))]
    if not snaps:
        sys.exit("스냅샷이 없다. 먼저 `runner.py snapshot` 을 실행하라.")

    jobs = [(p, s) for p in personas for s in snaps
            if not p.get("countries") or s.get("country") in p["countries"]]
    print(f"페르소나 {len(personas)} × 화면 {len(snaps)} → 평가 {len(jobs)}건 "
          f"(worker {args.workers})")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "evaluations.jsonl"
    done = 0
    with out_path.open("w", encoding="utf-8") as fh, \
            cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(evaluate_one, client, p, s): (p, s) for p, s in jobs}
        for fut in cf.as_completed(futures):
            p, s = futures[fut]
            try:
                r = fut.result()
            except Exception as e:
                r = {"persona_id": p["id"], "screen": s["key"], "error": str(e)[:200]}
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            fh.flush()
            done += 1
            if done % 10 == 0 or done == len(jobs):
                print(f"  {done}/{len(jobs)}")
    print("→", out_path)


# ────────────────────────────── 3) REPORT ──────────────────────────────
def cmd_report(args):
    path = OUT_DIR / "evaluations.jsonl"
    if not path.exists():
        sys.exit("평가 결과가 없다. 먼저 `runner.py evaluate` 를 실행하라.")
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    ok = [r for r in rows if "friction" in r]

    def agg(key):
        d = {}
        for r in ok:
            d.setdefault(r.get(key) or "-", []).append(r)
        return d

    print(f"\n총 평가 {len(rows)}건 (유효 {len(ok)})")
    print(f"과업 완료율 {sum(1 for r in ok if r.get('completed'))/max(len(ok),1)*100:.1f}%")

    print("\n── 화면별 마찰 (높은 순) ──")
    for k, v in sorted(agg("screen").items(),
                       key=lambda kv: -sum(r["friction"] for r in kv[1]) / len(kv[1])):
        avg = sum(r["friction"] for r in v) / len(v)
        comp = sum(1 for r in v if r.get("completed")) / len(v) * 100
        print(f"  {k:<18} 마찰 {avg:4.1f}  완료 {comp:5.1f}%  n={len(v)}")

    print("\n── 이탈처 분포 ──")
    dest = agg("next_action")
    for k, v in sorted(dest.items(), key=lambda kv: -len(kv[1])):
        print(f"  {k:<18} {len(v):4d}건 ({len(v)/len(ok)*100:4.1f}%)")

    print("\n── 가장 많이 지목된 결핍 콘텐츠 ──")
    miss = {}
    for r in ok:
        m = (r.get("missing_content") or "").strip()
        if m:
            miss[m] = miss.get(m, 0) + 1
    for k, c in sorted(miss.items(), key=lambda kv: -kv[1])[:15]:
        print(f"  {c:3d}회  {k[:88]}")

    print("\n── 마찰 상위 VOC ──")
    for r in sorted(ok, key=lambda r: -r["friction"])[:8]:
        print(f"  [{r['friction']}] {r['screen']:<16} {r.get('persona','')[:26]}")
        print(f"        “{(r.get('voc') or '')[:110]}”")

    summary = {
        "총평가": len(rows), "유효": len(ok),
        "완료율": round(sum(1 for r in ok if r.get("completed")) / max(len(ok), 1) * 100, 1),
        "화면별마찰": {k: round(sum(r["friction"] for r in v) / len(v), 1)
                   for k, v in agg("screen").items()},
        "이탈처": {k: len(v) for k, v in dest.items()},
        "결핍콘텐츠": dict(sorted(miss.items(), key=lambda kv: -kv[1])[:20]),
    }
    (OUT_DIR / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n→", OUT_DIR / "summary.json")


def main():
    ap = argparse.ArgumentParser(description="lg.com 레드팀 러너")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("snapshot", help="화면을 1회 수집 (headed 브라우저 필요)")
    a.add_argument("--config", default="targets.json")
    a.set_defaults(func=cmd_snapshot)

    b = sub.add_parser("evaluate", help="스냅샷 위에서 페르소나 N개 병렬 평가")
    b.add_argument("--personas", default="personas.json")
    b.add_argument("--workers", type=int, default=8)
    b.set_defaults(func=cmd_evaluate)

    c = sub.add_parser("report", help="집계")
    c.set_defaults(func=cmd_report)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
