#!/usr/bin/env python3
"""Generate Swiss architectural HUD detail pages (/apps/<slug>/index.html) for all 15 AllCraft Studio apps."""

import html
import pathlib
from apps_catalog import APPS_CATALOG


def _esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def render_app_page(app: dict, all_apps: list[dict]) -> str:
    slug = app["slug"]
    prefix = app["prefix"]
    full_name = f"{prefix}Craft"
    num = app["num"]
    code = app["code"]
    cat = app["category"]
    color = app["color"]
    mount = app["mount"]
    repo = app["repo"]
    hero = app["hero"]
    icon = app["icon"]

    highlights_html = []
    for idx, (h_title, h_desc) in enumerate(app["highlights"], start=1):
        highlights_html.append(
            f"""
          <li class="hl-cell">
            <div class="hl-top">
              <span class="hl-dot"></span>
              <span class="hud-label" style="color:var(--faint)">{idx:02d}</span>
            </div>
            <h3 class="font-display">{_esc(h_title)}</h3>
            <p>{_esc(h_desc)}</p>
          </li>"""
        )

    shortcuts_html = "".join(
        f'<div class="kv-row"><span>{_esc(sc.split(" — ")[1])}</span><code>{_esc(sc.split(" — ")[0])}</code></div>'
        for sc in app["shortcuts"]
    )

    others = [a for a in all_apps if a["slug"] != slug]
    family_cards = []
    for o in others:
        o_name = f"{o['prefix']}Craft"
        family_cards.append(
            f"""
        <div class="fam-card" style="--app:{o['color']}">
          <span class="fam-topline" aria-hidden="true"></span>
          <div class="fam-head">
            <span class="fam-num hud-label">{o['num']}</span>
            <span class="fam-cat hud-label">{_esc(o['category'])}</span>
            <a class="fam-launch hud-label" href="{o['mount']}" title="Launch {o_name} in Browser">● Launch</a>
          </div>
          <a class="fam-link" href="/apps/{o['slug']}/">
            <div class="fam-hero">
              <img src="{o['hero']}" alt="{o_name}" loading="lazy" decoding="async" referrerpolicy="no-referrer"
                   onerror="this.style.display='none'">
            </div>
            <div class="fam-body">
              <img class="fam-icon" src="{o['icon']}" alt="" width="128" height="128" loading="lazy" decoding="async" referrerpolicy="no-referrer"
                   onerror="this.outerHTML='<div class=\\'fam-icon-fb\\'>{o['code']}</div>'">
              <h3 class="fam-title">{_esc(o['prefix'])}<span style="color:var(--app)">Craft</span></h3>
              <p class="fam-desc">{_esc(o['short_desc'])}</p>
              <span class="fam-cta hud-label">Explore {o_name} &nearr;</span>
            </div>
          </a>
        </div>"""
        )

    # 14 other apps + 2-column summary card = 16 cells = exact 4x4 grid!
    family_cards.append(
        """
        <div class="fam-summary">
          <div>
            <p class="hud-label" style="margin:0;color:var(--faint)">15 / 15 Unified Cloud</p>
            <h3 class="font-display" style="margin:12px 0 0;font-size:30px;color:var(--ink-strong)">Explore the <span style="color:var(--app)">entire suite</span>.</h3>
            <p style="margin:10px 0 0;max-width:460px;font-size:14.5px;line-height:1.6;color:var(--muted)">Every Craft application shares the same zero-cloud privacy model, keyboard-first ergonomics, and instant WebGPU + WebAssembly runtime.</p>
          </div>
          <a href="/#lineup" class="btn-primary hud-label" style="height:42px;padding:0 18px;width:fit-content">&larr; Back to All 15 Apps</a>
        </div>"""
    )

    footer_app_links = "".join(
        f'<a href="/apps/{a["slug"]}/">{_esc(a["prefix"])}Craft</a>' for a in all_apps
    )

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="dark" style="--app:{color}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="referrer" content="no-referrer">
  <meta name="theme-color" content="#0b0b0c" id="meta-theme-color">
  <title>{full_name} — {_esc(cat)} | The AllCraft Studio</title>
  <meta name="description" content="{_esc(app['lead'])}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@100..125,500..900&family=Instrument+Serif:ital@0;1&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
  <script>
    (() => {{
      const saved = localStorage.getItem("allcraft_theme");
      if (saved === "light" || saved === "dark") {{
        document.documentElement.setAttribute("data-theme", saved);
      }}
    }})();
  </script>
  <style>
    :root, html[data-theme="dark"] {{
      --bg: #0b0b0c;
      --bg-glass: rgba(11, 11, 12, 0.78);
      --bg-sunken: #111114;
      --bg-hover: #151519;
      --line: #232329;
      --line-strong: #3c3c46;
      --ink-strong: #f5f5f7;
      --ink: #e4e4e9;
      --muted: #9a9aa6;
      --faint: #666672;
      --invert-bg: #f5f5f7;
      --invert-fg: #0b0b0c;
    }}
    html[data-theme="light"] {{
      --bg: #f2f1ee;
      --bg-glass: rgba(242, 241, 238, 0.84);
      --bg-sunken: #e7e5e0;
      --bg-hover: #eceae5;
      --line: #d6d3cc;
      --line-strong: #9e9a90;
      --ink-strong: #111113;
      --ink: #1e1e22;
      --muted: #57554f;
      --faint: #85827a;
      --invert-bg: #111113;
      --invert-fg: #f2f1ee;
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: "Inter", system-ui, -apple-system, sans-serif;
      -webkit-font-smoothing: antialiased;
      overflow-x: hidden;
    }}
    a {{ color: inherit; text-decoration: none; }}
    .font-display {{ font-family: "Archivo", system-ui, sans-serif; font-weight: 500; letter-spacing: -0.035em; }}
    .hud-label {{
      font-family: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 11px; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; line-height: 1.3;
    }}

    /* Top Sticky HUD Bar */
    .topbar {{
      position: sticky; top: 0; z-index: 50; height: 48px;
      border-bottom: 1px solid var(--line); background: var(--bg-glass);
      backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
    }}
    .topbar-inner {{
      max-width: 1280px; height: 100%; margin: 0 auto; padding: 0 24px;
      border-left: 1px solid var(--line); border-right: 1px solid var(--line);
      display: flex; align-items: center; justify-content: space-between; gap: 16px;
    }}
    .crumbs {{ display: flex; align-items: center; gap: 8px; }}
    .brand-link {{
      display: inline-flex; align-items: center; gap: 8px;
      font-family: "Archivo", sans-serif; font-weight: 800; font-stretch: 125%;
      font-size: 14px; letter-spacing: 0.06em; color: var(--ink-strong);
    }}
    .topnav {{ display: flex; align-items: center; gap: 20px; }}
    .topnav a {{ color: var(--muted); transition: color 0.15s ease; }}
    .topnav a:hover {{ color: var(--ink-strong); }}
    .top-actions {{ display: flex; align-items: center; gap: 8px; }}
    .icon-btn {{
      height: 32px; padding: 0 11px; border: 1px solid var(--line);
      background: var(--bg); color: var(--muted); cursor: pointer;
      display: inline-flex; align-items: center; gap: 6px;
      transition: all 0.15s ease;
    }}
    .icon-btn:hover {{ color: var(--ink-strong); border-color: var(--line-strong); }}
    .launch-top-btn {{
      height: 32px; padding: 0 12px; background: var(--app); color: #0b0b0c;
      font-weight: 800; display: inline-flex; align-items: center; gap: 6px;
    }}
    .launch-top-btn:hover {{ opacity: 0.88; }}
    @media (max-width: 920px) {{ .topnav {{ display: none; }} }}
    @media (max-width: 560px) {{ .crumb-hide {{ display: none; }} }}

    /* Architectural Frame & Ticks */
    .section-wrap {{ position: relative; border-top: 1px solid var(--line); }}
    .section-wrap:first-of-type {{ border-top: none; }}
    .frame {{
      position: relative; max-width: 1280px; margin: 0 auto;
      border-left: 1px solid var(--line); border-right: 1px solid var(--line);
    }}
    .tick {{ position: absolute; width: 11px; height: 11px; pointer-events: none; z-index: 35; }}
    .tick::before, .tick::after {{ content: ""; position: absolute; background: var(--line-strong); }}
    .tick::before {{ left: 5px; top: 0; width: 1px; height: 11px; }}
    .tick::after {{ left: 0; top: 5px; width: 11px; height: 1px; }}
    .tick-tl {{ top: -6px; left: -6px; }}
    .tick-tr {{ top: -6px; right: -6px; }}

    .eyebrow {{
      position: sticky; top: 48px; z-index: 30;
      border-bottom: 1px solid var(--line); background: var(--bg-glass);
      backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
      display: flex; align-items: center; justify-content: space-between; gap: 16px;
      padding: 12px 40px;
    }}
    @media (max-width: 768px) {{ .eyebrow {{ padding: 11px 20px; }} }}

    /* Hero Content */
    .hero-pad {{ padding: 56px 40px 48px; }}
    @media (max-width: 768px) {{ .hero-pad {{ padding: 36px 20px; }} }}
    .app-identity {{ display: flex; align-items: center; gap: 18px; margin-bottom: 24px; flex-wrap: wrap; }}
    .hero-icon {{
      width: 80px; height: 80px; object-fit: contain;
      filter: drop-shadow(0 10px 22px rgba(0,0,0,0.4));
    }}
    .hero-icon-fb {{
      width: 76px; height: 76px; border-radius: 18px; background: #141418;
      border: 2px solid var(--app); color: var(--app);
      display: flex; align-items: center; justify-content: center;
      font-family: "Archivo", sans-serif; font-size: 30px; font-weight: 800;
    }}
    .id-badges {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }}
    .pill {{
      padding: 3px 8px; border: 1px solid var(--line); background: var(--bg-sunken);
      font-family: "JetBrains Mono", monospace; font-size: 10px; font-weight: 600;
      letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted);
    }}
    .pill.accent {{ color: var(--app); border-color: color-mix(in srgb, var(--app) 40%, var(--line)); }}
    .hero-h1 {{
      margin: 0; max-width: 920px;
      font-size: clamp(38px, 5.8vw, 68px); line-height: 1.0; color: var(--ink-strong);
    }}
    .hero-lead {{
      margin: 22px 0 0; max-width: 720px;
      font-size: 18.5px; line-height: 1.62; color: var(--muted);
    }}
    .cta-row {{ margin-top: 32px; display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }}
    .btn-primary {{
      height: 48px; padding: 0 26px; background: var(--invert-bg); color: var(--invert-fg);
      border: 1px solid var(--invert-bg); display: inline-flex; align-items: center; justify-content: center;
      gap: 9px; cursor: pointer; transition: opacity 0.15s ease;
    }}
    .btn-primary:hover {{ opacity: 0.85; }}
    .btn-accent {{
      height: 48px; padding: 0 26px; background: var(--app); color: #0b0b0c;
      border: 1px solid var(--app); font-weight: 800;
      display: inline-flex; align-items: center; justify-content: center; gap: 9px;
      cursor: pointer; transition: opacity 0.15s ease;
    }}
    .btn-accent:hover {{ opacity: 0.88; }}
    .btn-secondary {{
      height: 48px; padding: 0 22px; background: var(--bg); color: var(--ink);
      border: 1px solid var(--line-strong); display: inline-flex; align-items: center; justify-content: center;
      gap: 9px; cursor: pointer; transition: all 0.15s ease;
    }}
    .btn-secondary:hover {{ background: var(--invert-bg); color: var(--invert-fg); border-color: var(--invert-bg); }}

    .meta-strip {{
      margin-top: 24px; display: flex; flex-wrap: wrap; gap: 8px 20px; color: var(--faint);
    }}
    .share-strip {{
      margin-top: 24px; display: inline-grid; grid-auto-flow: column; gap: 1px;
      border: 1px solid var(--line); background: var(--line);
    }}
    @media (max-width: 600px) {{
      .share-strip {{ display: grid; grid-auto-flow: row; grid-template-columns: repeat(3, 1fr); width: 100%; }}
    }}
    .share-cell {{
      height: 36px; padding: 0 13px; background: var(--bg); color: var(--muted); border: none;
      display: inline-flex; align-items: center; justify-content: center; cursor: pointer;
      transition: all 0.15s ease;
    }}
    .share-cell.label {{ color: var(--faint); cursor: default; }}
    button.share-cell:hover, a.share-cell:hover {{ background: var(--invert-bg); color: var(--invert-fg); }}

    /* Full-Bleed Framed Workspace Showcase */
    .showcase-box {{ border-top: 1px solid var(--line); background: var(--bg-sunken); }}
    .showcase-bar {{
      display: flex; align-items: center; justify-content: space-between; gap: 12px;
      padding: 10px 24px; border-bottom: 1px solid var(--line); background: var(--bg);
    }}
    .showcase-media {{
      position: relative; aspect-ratio: 16 / 10; overflow: hidden; background: #09090b;
    }}
    .showcase-media img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}

    /* 02 / Highlights 3x2 Grid */
    .sec-pad {{ padding: 64px 40px 48px; }}
    @media (max-width: 768px) {{ .sec-pad {{ padding: 44px 20px 36px; }} }}
    .sec-h2 {{ margin: 0; font-size: clamp(34px, 4.8vw, 56px); line-height: 1.03; color: var(--ink-strong); }}
    .sec-sub {{ margin: 16px 0 0; max-width: 620px; font-size: 17px; line-height: 1.6; color: var(--muted); }}
    .hl-grid {{
      display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1px;
      border-top: 1px solid var(--line); background: var(--line); list-style: none; margin: 0; padding: 0;
    }}
    @media (max-width: 920px) {{ .hl-grid {{ grid-template-columns: 1fr; }} }}
    .hl-cell {{ background: var(--bg); padding: 32px; }}
    .hl-top {{ display: flex; align-items: center; justify-content: space-between; }}
    .hl-dot {{ width: 10px; height: 10px; background: var(--app); display: inline-block; }}
    .hl-cell h3 {{ margin: 22px 0 10px; font-size: 23px; color: var(--ink-strong); }}
    .hl-cell p {{ margin: 0; font-size: 14.5px; line-height: 1.62; color: var(--muted); }}

    /* 03 / Screenshots & Workflow Split Grid */
    .shots-subgrid {{
      display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1px;
      border-top: 1px solid var(--line); background: var(--line);
    }}
    @media (max-width: 860px) {{ .shots-subgrid {{ grid-template-columns: 1fr; }} }}
    .shot-panel {{ background: var(--bg); display: flex; flex-direction: column; }}
    .shot-crop {{
      aspect-ratio: 16 / 9; overflow: hidden; border-bottom: 1px solid var(--line); background: var(--bg-sunken);
    }}
    .shot-crop img {{
      width: 100%; height: 100%; object-fit: cover; display: block;
      transform: scale(1.28);
    }}
    .shot-crop.left-zoom img {{ transform-origin: 15% 22%; }}
    .shot-crop.right-zoom img {{ transform-origin: 85% 68%; }}
    .shot-info {{ padding: 24px 28px 28px; }}
    .kv-list {{ margin-top: 14px; display: flex; flex-direction: column; gap: 8px; }}
    .kv-row {{
      display: flex; align-items: center; justify-content: space-between; gap: 12px;
      padding: 8px 12px; border: 1px solid var(--line); background: var(--bg-sunken); font-size: 13px;
    }}
    .kv-row code {{
      font-family: "JetBrains Mono", monospace; font-size: 11.5px; color: var(--app);
    }}

    /* 04 / Get App Section */
    .opt-banner {{
      border-top: 1px solid var(--line); background: var(--bg-sunken); padding: 40px;
      display: flex; align-items: center; justify-content: space-between; gap: 28px; flex-wrap: wrap;
    }}
    @media (max-width: 768px) {{ .opt-banner {{ padding: 28px 20px; }} }}
    .plat-grid {{
      display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1px;
      border-top: 1px solid var(--line); background: var(--line);
    }}
    @media (max-width: 900px) {{ .plat-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
    @media (max-width: 540px) {{ .plat-grid {{ grid-template-columns: 1fr; }} }}
    .plat-cell {{ background: var(--bg); padding: 26px; display: flex; flex-direction: column; gap: 8px; }}
    .plat-cell h4 {{ margin: 4px 0 0; font-size: 19px; color: var(--ink-strong); }}
    .plat-cell p {{ margin: 0; font-size: 13.5px; color: var(--muted); line-height: 1.55; }}

    .source-grid {{
      display: grid; grid-template-columns: 1fr 1.15fr; gap: 1px;
      border-top: 1px solid var(--line); background: var(--line);
    }}
    @media (max-width: 900px) {{ .source-grid {{ grid-template-columns: 1fr; }} }}
    .spec-box, .term-box {{ background: var(--bg); padding: 34px 36px; }}
    @media (max-width: 768px) {{ .spec-box, .term-box {{ padding: 24px 20px; }} }}
    .term-win {{
      margin-top: 18px; border: 1px solid var(--line-strong); background: #09090b; color: #e4e4e7;
    }}
    .term-bar {{
      display: flex; align-items: center; justify-content: space-between;
      padding: 8px 14px; border-bottom: 1px solid #232329; background: #121216;
    }}
    .term-pre {{
      margin: 0; padding: 18px; overflow-x: auto;
      font-family: "JetBrains Mono", monospace; font-size: 12.5px; line-height: 1.7; color: #d4d4d8;
    }}

    /* 05 / The Family Grid */
    .fam-grid {{
      display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1px;
      border-top: 1px solid var(--line); background: var(--line);
    }}
    @media (max-width: 1180px) {{ .fam-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
    @media (max-width: 640px) {{ .fam-grid {{ grid-template-columns: 1fr; }} }}
    .fam-card {{ position: relative; background: var(--bg); display: flex; flex-direction: column; transition: background 0.2s ease; }}
    .fam-card:hover {{ background: var(--bg-hover); }}
    .fam-topline {{
      position: absolute; top: 0; left: 0; right: 0; height: 2px; background: var(--app);
      transform: scaleX(0); transform-origin: left; transition: transform 0.28s ease; z-index: 5;
    }}
    .fam-card:hover .fam-topline {{ transform: scaleX(1); }}
    .fam-head {{
      display: flex; align-items: center; gap: 8px; padding: 10px 18px; border-bottom: 1px solid var(--line);
    }}
    .fam-num {{ padding: 3px 7px; background: var(--app); color: #0b0b0c; font-weight: 800; }}
    .fam-cat {{ color: var(--faint); flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    .fam-launch {{
      padding: 3px 7px; border: 1px solid rgba(34,197,94,0.4); color: #4ade80; font-size: 9.5px;
    }}
    .fam-launch:hover {{ background: #22c55e; color: #0b0b0c; }}
    .fam-link {{ display: flex; flex-direction: column; flex: 1; }}
    .fam-hero {{ aspect-ratio: 16 / 10; overflow: hidden; border-bottom: 1px solid var(--line); background: var(--bg-sunken); }}
    .fam-hero img {{ width: 100%; height: 100%; object-fit: cover; display: block; transition: transform 0.45s ease; }}
    .fam-card:hover .fam-hero img {{ transform: scale(1.035); }}
    .fam-body {{ padding: 0 22px 22px; display: flex; flex-direction: column; flex: 1; }}
    .fam-icon {{ width: 56px; height: 56px; margin-top: -28px; object-fit: contain; filter: drop-shadow(0 6px 12px rgba(0,0,0,0.35)); }}
    .fam-icon-fb {{
      width: 54px; height: 54px; margin-top: -27px; border-radius: 12px; background: #141418;
      border: 2px solid var(--app); color: var(--app); display: flex; align-items: center; justify-content: center;
      font-family: "Archivo", sans-serif; font-weight: 800; font-size: 20px;
    }}
    .fam-title {{ margin: 12px 0 0; font-family: "Archivo", sans-serif; font-size: 23px; font-weight: 500; color: var(--ink-strong); }}
    .fam-desc {{ margin: 8px 0 18px; font-size: 13.5px; line-height: 1.55; color: var(--muted); flex: 1; }}
    .fam-cta {{ color: var(--muted); margin-top: auto; }}
    .fam-card:hover .fam-cta {{ color: var(--ink-strong); }}
    .fam-summary {{
      grid-column: span 2; background: var(--bg); padding: 32px;
      display: flex; flex-direction: column; justify-content: space-between; gap: 20px;
    }}
    @media (max-width: 640px) {{ .fam-summary {{ grid-column: span 1; }} }}

    /* Bottom CTA & Multi-Column Architectural Footer */
    .start-box {{
      padding: 88px 28px; text-align: center; display: flex; flex-direction: column; align-items: center;
    }}
    .site-footer {{ border-top: 1px solid var(--line); }}
    .footer-grid {{
      max-width: 1280px; margin: 0 auto; padding: 40px;
      border-left: 1px solid var(--line); border-right: 1px solid var(--line);
      display: grid; grid-template-columns: 1.4fr 1fr 1fr; gap: 32px;
    }}
    @media (max-width: 820px) {{ .footer-grid {{ grid-template-columns: 1fr; padding: 28px 20px; }} }}
    .footer-apps {{ display: flex; flex-wrap: wrap; gap: 8px 14px; margin-top: 12px; }}
    .footer-apps a {{ color: var(--muted); font-size: 13px; }}
    .footer-apps a:hover {{ color: var(--ink-strong); }}

    /* Floating Bottom-Right Quick-Jump HUD Index */
    .quick-hud {{
      position: fixed; right: 18px; bottom: 18px; z-index: 45;
      display: flex; flex-direction: column; gap: 1px;
      border: 1px solid var(--line-strong); background: var(--line);
      box-shadow: 0 14px 34px rgba(0,0,0,0.45);
    }}
    .quick-hud a {{
      padding: 6px 10px; background: var(--bg-glass); backdrop-filter: blur(10px);
      color: var(--faint); font-size: 9.5px; transition: all 0.15s ease;
    }}
    .quick-hud a:hover {{ color: var(--ink-strong); background: var(--bg-hover); }}
    @media (max-width: 1100px) {{ .quick-hud {{ display: none; }} }}

    #toast {{
      position: fixed; bottom: 24px; left: 24px; z-index: 100;
      padding: 11px 16px; background: var(--invert-bg); color: var(--invert-fg);
      border: 1px solid var(--line-strong); transform: translateY(16px); opacity: 0;
      pointer-events: none; transition: all 0.2s ease;
    }}
    #toast.show {{ transform: translateY(0); opacity: 1; }}
  </style>
</head>
<body>

  <!-- Sticky Architectural Top Bar -->
  <header class="topbar">
    <div class="topbar-inner">
      <div class="crumbs hud-label">
        <a href="/" class="brand-link">
          <svg width="18" height="15" viewBox="0 0 116.34 97.5" fill="currentColor" aria-hidden="true">
            <path d="M104.28,49.49L81.55,0h-31.23l-3.17,4.76L14.75,53.63,0,75.85l21.55,21.55,63.79-36.94,16.99,37.04,14.01-21.74-12.06-26.27ZM32.89,65.66l32.42-48.87,10.91,23.77-43.32,25.09Z"></path>
          </svg>
          <span>ALLCRAFT</span>
        </a>
        <span class="crumb-hide" style="color:var(--faint)">/</span>
        <a href="/#lineup" class="crumb-hide" style="color:var(--muted)">Apps</a>
        <span style="color:var(--faint)">/</span>
        <span style="color:var(--app)">{full_name}</span>
      </div>

      <nav class="topnav hud-label">
        <a href="#overview">01 / Overview</a>
        <a href="#highlights">02 / Highlights</a>
        <a href="#screenshots">03 / Screenshots</a>
        <a href="#get-it">04 / Get It</a>
        <a href="#family">05 / Family</a>
      </nav>

      <div class="top-actions">
        <a href="{mount}" class="launch-top-btn hud-label">&#9654; Launch Web</a>
        <button type="button" id="theme-toggle" class="icon-btn hud-label"><span id="theme-label">Light</span></button>
      </div>
    </div>
  </header>

  <main>
    <!-- 01 / OVERVIEW & HERO -->
    <section id="overview" class="section-wrap">
      <div class="frame">
        <span class="tick tick-tl" aria-hidden="true"></span>
        <span class="tick tick-tr" aria-hidden="true"></span>

        <div class="eyebrow">
          <p class="hud-label" style="margin:0;color:var(--muted)"><span style="color:var(--faint)">01</span> <span style="color:var(--faint);margin:0 6px">/</span> {full_name}</p>
          <p class="hud-label" style="margin:0;color:var(--faint)">{num} of 15 &middot; {_esc(cat)}</p>
        </div>

        <div class="hero-pad">
          <div class="app-identity">
            <img class="hero-icon" src="{icon}" alt="{full_name} icon" width="160" height="160" referrerpolicy="no-referrer"
                 onerror="this.outerHTML='<div class=\\'hero-icon-fb\\'>{code}</div>'">
            <div>
              <div style="font-family:'Archivo',sans-serif;font-size:28px;font-weight:600;letter-spacing:-0.02em;color:var(--ink-strong)">
                {_esc(prefix)}<span style="color:var(--app)">Craft</span>
              </div>
              <div class="id-badges">
                <span class="pill accent">● Live in Browser</span>
                <span class="pill accent">WebGPU + Wasm</span>
                <span class="pill">MIT / Apache-2.0</span>
              </div>
            </div>
          </div>

          <h1 class="hero-h1 font-display">{_esc(app['headline_before'])}<span style="color:var(--app)">{_esc(app['headline_accent'])}</span>{_esc(app['headline_after'])}</h1>
          <p class="hero-lead">{_esc(app['lead'])}</p>

          <div class="cta-row">
            <a href="{mount}" class="btn-accent hud-label">&#9654; Launch {full_name} in Browser</a>
            <a href="https://github.com/{repo}" target="_blank" rel="noopener" class="btn-secondary hud-label">View Source on GitHub &nearr;</a>
            <a href="/#lineup" class="btn-secondary hud-label">&larr; All 15 Apps</a>
          </div>

          <div class="meta-strip hud-label">
            <span>Web (Zero Install)</span>
            <span>macOS &middot; Windows &middot; Linux &middot; FreeBSD</span>
            <span>100% Local Files &middot; No Subscription</span>
          </div>

          <div class="share-strip">
            <span class="share-cell label hud-label">Share</span>
            <button type="button" class="share-cell hud-label" id="copy-link-btn">Copy link</button>
            <a class="share-cell hud-label" target="_blank" rel="noopener" href="https://x.com/intent/post?text={full_name}%20on%20The%20AllCraft%20Studio&url=https%3A%2F%2Fthe-allcraft.pages.dev%2Fapps%2F{slug}%2F">X</a>
            <a class="share-cell hud-label" target="_blank" rel="noopener" href="https://www.reddit.com/submit?url=https%3A%2F%2Fthe-allcraft.pages.dev%2Fapps%2F{slug}%2F&title={full_name}%20%E2%80%94%20Open-Source%20Rust%20%2B%20WebAssembly">Reddit</a>
            <a class="share-cell hud-label" target="_blank" rel="noopener" href="https://bsky.app/intent/compose?text={full_name}%20https%3A%2F%2Fthe-allcraft.pages.dev%2Fapps%2F{slug}%2F">Bluesky</a>
            <a class="share-cell hud-label" target="_blank" rel="noopener" href="https://www.linkedin.com/sharing/share-offsite/?url=https%3A%2F%2Fthe-allcraft.pages.dev%2Fapps%2F{slug}%2F">LinkedIn</a>
          </div>
        </div>

        <div class="showcase-box">
          <div class="showcase-bar hud-label">
            <span style="color:var(--app)">00 / Live Studio Workspace</span>
            <span style="color:var(--muted)">{_esc(app['hero_caption'])}</span>
            <span style="color:var(--faint)">Pure Rust + Wasm</span>
          </div>
          <div class="showcase-media">
            <img src="{hero}" alt="{full_name} workspace" referrerpolicy="no-referrer">
          </div>
        </div>
      </div>
    </section>

    <!-- 02 / HIGHLIGHTS -->
    <section id="highlights" class="section-wrap">
      <div class="frame">
        <span class="tick tick-tl" aria-hidden="true"></span>
        <span class="tick tick-tr" aria-hidden="true"></span>

        <div class="eyebrow">
          <p class="hud-label" style="margin:0;color:var(--muted)"><span style="color:var(--faint)">02</span> <span style="color:var(--faint);margin:0 6px">/</span> Highlights</p>
          <p class="hud-label" style="margin:0;color:var(--faint)">Capabilities &amp; toolset</p>
        </div>

        <div class="sec-pad">
          <h2 class="sec-h2 font-display">What&rsquo;s <span style="color:var(--app)">inside</span>.</h2>
          <p class="sec-sub">Every core tool in {full_name} is written in clean-room Rust for instant responsiveness on desktop and WebAssembly.</p>
        </div>

        <ol class="hl-grid">{"".join(highlights_html)}
        </ol>
      </div>
    </section>

    <!-- 03 / SCREENSHOTS & WORKFLOW -->
    <section id="screenshots" class="section-wrap">
      <div class="frame">
        <span class="tick tick-tl" aria-hidden="true"></span>
        <span class="tick tick-tr" aria-hidden="true"></span>

        <div class="eyebrow">
          <p class="hud-label" style="margin:0;color:var(--muted)"><span style="color:var(--faint)">03</span> <span style="color:var(--faint);margin:0 6px">/</span> Screenshots &amp; Workflow</p>
          <p class="hud-label" style="margin:0;color:var(--faint)">Interface details &amp; shortcuts</p>
        </div>

        <div class="shots-subgrid">
          <div class="shot-panel">
            <div class="showcase-bar hud-label">
              <span style="color:var(--app)">01</span>
              <span style="color:var(--muted)">Tools, Canvas &amp; Shortcuts</span>
            </div>
            <div class="shot-crop left-zoom">
              <img src="{hero}" alt="{full_name} tools detail" loading="lazy" referrerpolicy="no-referrer">
            </div>
            <div class="shot-info">
              <h3 class="font-display" style="margin:0;font-size:22px;color:var(--ink-strong)">Muscle-memory shortcuts</h3>
              <p style="margin:8px 0 0;font-size:14px;color:var(--muted)">Familiar professional keybindings work right inside your browser tab (with browser shortcut capture).</p>
              <div class="kv-list">{shortcuts_html}</div>
            </div>
          </div>

          <div class="shot-panel">
            <div class="showcase-bar hud-label">
              <span style="color:var(--app)">02</span>
              <span style="color:var(--muted)">Inspector, Formats &amp; Automation</span>
            </div>
            <div class="shot-crop right-zoom">
              <img src="{hero}" alt="{full_name} inspector detail" loading="lazy" referrerpolicy="no-referrer">
            </div>
            <div class="shot-info">
              <h3 class="font-display" style="margin:0;font-size:22px;color:var(--ink-strong)">Open formats &amp; Agent-ready CLI</h3>
              <p style="margin:8px 0 0;font-size:14px;color:var(--muted)">Work directly on standard industry files locally, or drive {full_name} headlessly from scripts and AI agents.</p>
              <div class="kv-list">
                <div class="kv-row"><span>File Formats</span><code>{_esc(app['formats'])}</code></div>
                <div class="kv-row"><span>Core Engine</span><code>{_esc(app['engine'])}</code></div>
                <div class="kv-row"><span>CLI / MCP</span><code>{_esc(app['cli_example'])}</code></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 04 / GET IT -->
    <section id="get-it" class="section-wrap">
      <div class="frame">
        <span class="tick tick-tl" aria-hidden="true"></span>
        <span class="tick tick-tr" aria-hidden="true"></span>

        <div class="eyebrow">
          <p class="hud-label" style="margin:0;color:var(--muted)"><span style="color:var(--faint)">04</span> <span style="color:var(--faint);margin:0 6px">/</span> Get {full_name}</p>
          <p class="hud-label" style="margin:0;color:var(--faint)">Instant Web Studio or Native Source</p>
        </div>

        <div class="opt-banner">
          <div style="max-width:680px">
            <span class="pill accent">Recommended &middot; Zero Install</span>
            <h2 class="font-display" style="margin:14px 0 0;font-size:clamp(28px,4vw,42px);color:var(--ink-strong)">Run {full_name} <span style="color:var(--app)">instantly</span> in your browser.</h2>
            <p style="margin:12px 0 0;font-size:15.5px;line-height:1.6;color:var(--muted)">Streams in parallel 6 MiB gzipped WebAssembly chunks from Cloudflare Edge with a native desktop splash screen. Your files stay 100% in your device memory.</p>
          </div>
          <a href="{mount}" class="btn-accent hud-label">&#9654; Open {full_name} ({mount})</a>
        </div>

        <div class="plat-grid">
          <div class="plat-cell">
            <span class="hud-label" style="color:var(--app)">WebAssembly</span>
            <h4 class="font-display">Browser Studio</h4>
            <p>Chrome, Edge, Firefox &amp; Safari with WebGPU / WebGL2 acceleration at <code>{mount}</code>.</p>
          </div>
          <div class="plat-cell">
            <span class="hud-label" style="color:var(--faint)">macOS</span>
            <h4 class="font-display">Apple Silicon &amp; Intel</h4>
            <p>Native Metal GPU backend; build `.app` / `.dmg` bundles from `packaging/macos`.</p>
          </div>
          <div class="plat-cell">
            <span class="hud-label" style="color:var(--faint)">Windows</span>
            <h4 class="font-display">x64 &amp; ARM64</h4>
            <p>Native DirectX 12 / Vulkan backend; MSI installers in `packaging/windows`.</p>
          </div>
          <div class="plat-cell">
            <span class="hud-label" style="color:var(--faint)">Linux &amp; BSD</span>
            <h4 class="font-display">Flatpak, DEB &amp; RPM</h4>
            <p>Native Vulkan / Wayland / X11 builds via `packaging/linux` and `packaging/freebsd`.</p>
          </div>
        </div>

        <div class="source-grid">
          <div class="spec-box">
            <p class="hud-label" style="margin:0;color:var(--faint)">Technical Specifications</p>
            <h3 class="font-display" style="margin:12px 0 18px;font-size:28px;color:var(--ink-strong)">Open source down to the metal.</h3>
            <div class="kv-list">
              <div class="kv-row"><span>Repository</span><code>github.com/{repo}</code></div>
              <div class="kv-row"><span>Web Route</span><code>the-allcraft.pages.dev{mount}</code></div>
              <div class="kv-row"><span>License</span><code>MIT OR Apache-2.0</code></div>
              <div class="kv-row"><span>Cloud Uploads</span><code>None (100% Client-Side)</code></div>
            </div>
          </div>

          <div class="term-box">
            <p class="hud-label" style="margin:0;color:var(--faint)">Build Natively</p>
            <h3 class="font-display" style="margin:12px 0 6px;font-size:28px;color:var(--ink-strong)">Run it <span style="color:var(--app)">today</span>.</h3>
            <p style="margin:0;font-size:14px;color:var(--muted)">Clone the repository and compile a native release binary with Cargo:</p>
            <div class="term-win">
              <div class="term-bar hud-label">
                <span style="color:#a1a1aa">Terminal</span>
                <button type="button" id="copy-cmd-btn" style="background:none;border:1px solid #3f3f46;color:#e4e4e7;padding:3px 9px;cursor:pointer" class="hud-label">Copy</button>
              </div>
              <pre class="term-pre" id="clone-cmd">git clone https://github.com/{repo}.git
cd {slug}
cargo run --release</pre>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 05 / THE FAMILY -->
    <section id="family" class="section-wrap">
      <div class="frame">
        <span class="tick tick-tl" aria-hidden="true"></span>
        <span class="tick tick-tr" aria-hidden="true"></span>

        <div class="eyebrow">
          <p class="hud-label" style="margin:0;color:var(--muted)"><span style="color:var(--faint)">05</span> <span style="color:var(--faint);margin:0 6px">/</span> The family</p>
          <p class="hud-label" style="margin:0;color:var(--faint)">Explore the other 14 crafts</p>
        </div>

        <div class="sec-pad">
          <h2 class="sec-h2 font-display">More from <span style="color:var(--app)">the family</span>.</h2>
          <p class="sec-sub">Every app in The AllCraft Studio is built to the same standards and runs right in your browser.</p>
        </div>

        <div class="fam-grid">{"".join(family_cards)}
        </div>
      </div>
    </section>

    <!-- BOTTOM CTA -->
    <section id="get-started" class="section-wrap">
      <div class="frame">
        <span class="tick tick-tl" aria-hidden="true"></span>
        <span class="tick tick-tr" aria-hidden="true"></span>

        <div class="start-box">
          <p class="hud-label" style="margin:0;color:var(--faint)">Zero install &middot; Ready in seconds</p>
          <h2 class="font-display" style="margin:18px 0 0;font-size:clamp(40px,6vw,68px);line-height:0.98;color:var(--ink-strong)">Start crafting with <span style="color:var(--app)">{full_name}</span>.</h2>
          <div class="cta-row" style="margin-top:32px;justify-content:center">
            <a href="{mount}" class="btn-accent hud-label">&#9654; Launch {full_name} Now</a>
            <a href="/" class="btn-secondary hud-label">Back to Studio Home</a>
          </div>
        </div>
      </div>
    </section>
  </main>

  <footer class="site-footer">
    <div class="footer-grid">
      <div>
        <div class="brand-link" style="margin-bottom:10px">ALLCRAFT STUDIO</div>
        <p style="margin:0;font-size:13px;line-height:1.6;color:var(--faint)">15 open-source pure Rust + WebAssembly creative, 3D, media, office and CAD tools. Dual-licensed under MIT OR Apache-2.0. Independent fork not affiliated with upstream ArtCraft Team.</p>
      </div>
      <div>
        <div class="hud-label" style="color:var(--ink-strong)">All 15 Detail Pages</div>
        <div class="footer-apps">{footer_app_links}</div>
      </div>
      <div>
        <div class="hud-label" style="color:var(--ink-strong)">Quick Links</div>
        <div class="footer-apps" style="flex-direction:column;gap:8px">
          <a href="{mount}">Launch {full_name} Web ({mount})</a>
          <a href="https://github.com/{repo}" target="_blank" rel="noopener">{repo} on GitHub</a>
          <a href="https://github.com/thepixopik/allcraft" target="_blank" rel="noopener">AllCraft Hub Pipeline</a>
        </div>
      </div>
    </div>
  </footer>

  <!-- Floating Quick-Jump Index -->
  <nav class="quick-hud hud-label" aria-label="Quick section jump">
    <a href="#overview">01 Overview</a>
    <a href="#highlights">02 Highlights</a>
    <a href="#screenshots">03 Screenshots</a>
    <a href="#get-it">04 Get It</a>
    <a href="#family">05 The Family</a>
    <a href="{mount}" style="color:var(--app)">&#9654; Launch App</a>
  </nav>

  <div id="toast" class="hud-label">Copied to clipboard</div>

  <script>
    const showToast = (msg) => {{
      const t = document.getElementById("toast");
      t.textContent = msg;
      t.classList.add("show");
      setTimeout(() => t.classList.remove("show"), 2000);
    }};

    const syncTheme = () => {{
      const cur = document.documentElement.getAttribute("data-theme") || "dark";
      document.getElementById("theme-label").textContent = cur === "dark" ? "Light" : "Dark";
      document.getElementById("meta-theme-color").setAttribute("content", cur === "dark" ? "#0b0b0c" : "#f2f1ee");
    }};
    syncTheme();

    document.getElementById("theme-toggle").addEventListener("click", () => {{
      const cur = document.documentElement.getAttribute("data-theme") || "dark";
      const next = cur === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      localStorage.setItem("allcraft_theme", next);
      syncTheme();
    }});

    document.getElementById("copy-link-btn").addEventListener("click", async () => {{
      try {{
        await navigator.clipboard.writeText(location.href);
        showToast("Page link copied");
      }} catch (_) {{}}
    }});

    document.getElementById("copy-cmd-btn").addEventListener("click", async () => {{
      try {{
        const txt = document.getElementById("clone-cmd").textContent;
        await navigator.clipboard.writeText(txt);
        showToast("Clone commands copied");
      }} catch (_) {{}}
    }});
  </script>
</body>
</html>
"""


def build_all(dist_dir: pathlib.Path) -> None:
    apps_root = dist_dir / "apps"
    apps_root.mkdir(parents=True, exist_ok=True)
    for app in APPS_CATALOG:
        out_dir = apps_root / app["slug"]
        out_dir.mkdir(parents=True, exist_ok=True)
        html_str = render_app_page(app, APPS_CATALOG)
        (out_dir / "index.html").write_text(html_str, encoding="utf-8")
    print(f"    Generated {len(APPS_CATALOG)} detail pages under dist/apps/<slug>/index.html")


if __name__ == "__main__":
    build_all(pathlib.Path(__file__).resolve().parent.parent / "dist")
