#!/usr/bin/env python3
"""Build the blueprint-style SVG panels used by the profile README.

Writes, for both GitHub themes (dark and light):
  assets/hero-*.svg       name, role, tagline and title block
  assets/portfolio-*.svg  link card for the portfolio site
  assets/parts-*.svg      the stack, drawn as a parts list
  assets/languages-*.svg  language-share gauges, from public repos

Usage: python3 scripts/generate.py
Env:   GH_USER (default ianjohndal5), GITHUB_TOKEN (optional; raises the API rate limit)
"""

import base64
import datetime
import json
import math
import os
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

USER = os.environ.get("GH_USER", "ianjohndal5")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = Path(__file__).resolve().parent.parent / "assets"

# ---- Content -----------------------------------------------------------------

NAME = "Ian Dal"
ROLE = "Software developer — web apps, dev tools, computer vision & game mods"
TAGLINE = "Fast with AI. Careful with anything irreversible."
TITLE_BLOCK = [("AUTHOR", "Ian Dal"), ("OS", "Arch Linux"), ("REV", datetime.date.today().strftime("%Y.%m"))]

PORTFOLIO_HOST = "ianjohndal.onrender.com"
PORTFOLIO_DESC = "My personal site, with a built-in AI chatbot"
PORTFOLIO_STACK = "REACT · TYPESCRIPT · VITE · TAILWIND · FLOWISE"

# (skillicons.dev id, label). None draws a built-in sparkle instead of an icon.
PARTS = [
    ("cs", "C#"), ("dotnet", ".NET"), ("ts", "TypeScript"), ("react", "React"),
    ("py", "Python"), ("opencv", "OpenCV"), ("sqlite", "SQLite"), ("tailwind", "Tailwind"),
    ("raspberrypi", "Raspberry Pi"), ("js", "JavaScript"), ("arch", "Arch Linux"), (None, "AI coding tools"),
]

TOP_N = 6
SKIP_REPOS = {USER}              # the profile repo itself
SKIP_LANGUAGES = set()           # e.g. {"HTML", "CSS"} to count only programming languages

# ---- Look --------------------------------------------------------------------

W = 840
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', 'DejaVu Sans Mono', monospace"

THEMES = {
    "dark": dict(bg="#0b1a2e", line="#58a6ff", fg="#e6edf3", muted="#8ba3c7", accent="#79c0ff",
                 chip="#0f2340", track="#1c3352", minor=0.06, major=0.13, icons="dark"),
    "light": dict(bg="#f6f9fd", line="#0969da", fg="#1f2328", muted="#57606a", accent="#0969da",
                  chip="#ffffff", track="#dbe6f3", minor=0.06, major=0.12, icons="light"),
}

# Colours from GitHub Linguist, so the gauges match the language bars on repo pages.
LANG_COLORS = {
    "C#": "#178600", "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Python": "#3572A5",
    "HTML": "#e34c26", "CSS": "#663399", "SCSS": "#c6538c", "PHP": "#4F5D95", "Shell": "#89e051",
    "Java": "#b07219", "C++": "#f34b7d", "C": "#555555", "Go": "#00ADD8", "Rust": "#dea584",
    "Lua": "#000080", "Luau": "#00A2FF", "Kotlin": "#A97BFF", "Dart": "#00B4AB", "Vue": "#41b883",
    "Svelte": "#ff3e00", "PowerShell": "#012456", "Batchfile": "#C1F12E", "Dockerfile": "#384d54",
    "Tree-sitter Query": "#8ea64c", "GDScript": "#355570", "Swift": "#F05138", "Ruby": "#701516",
}

# ---- Data --------------------------------------------------------------------


def fetch(url, accept="application/vnd.github+json"):
    req = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": f"{USER}-profile"})
    if TOKEN and url.startswith("https://api.github.com"):
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def language_totals():
    repos, page = [], 1
    while True:
        batch = json.loads(fetch(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner&page={page}"))
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    totals = {}
    for repo in repos:
        if repo["fork"] or repo["name"] in SKIP_REPOS:
            continue
        langs = json.loads(fetch(f"https://api.github.com/repos/{USER}/{repo['name']}/languages"))
        for lang, size in langs.items():
            if lang not in SKIP_LANGUAGES:
                totals[lang] = totals.get(lang, 0) + size
    return totals


def icon_data_uri(icon_id, theme):
    """Inline the icon so the SVG needs no network access when GitHub renders it."""
    try:
        svg = fetch(f"https://skillicons.dev/icons?i={icon_id}&theme={theme}", accept="image/svg+xml")
    except OSError:
        return None
    return "data:image/svg+xml;base64," + base64.b64encode(svg).decode()

# ---- Drawing helpers -----------------------------------------------------------
# Every animation holds its final state in the base attributes, so renderers
# that ignore animation still show the finished drawing.


def fade(delay, dur=0.6):
    return (f'<animate attributeName="opacity" values="0;0;1" keyTimes="0;{delay / (delay + dur):.4f};1" '
            f'dur="{delay + dur:.2f}s" fill="freeze"/>')


def draw(points, t, delay, dur=0.8, width=1.4, opacity=1.0, dash=None, color=None):
    """A polyline that draws itself in. Dashed lines fade in instead."""
    length = sum(math.dist(points[i], points[i + 1]) for i in range(len(points) - 1))
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    stroke = color or t["line"]
    if dash:
        return (f'<polyline points="{pts}" fill="none" stroke="{stroke}" stroke-width="{width}" '
                f'stroke-opacity="{opacity}" stroke-dasharray="{dash}">{fade(delay, dur)}</polyline>')
    return (f'<polyline points="{pts}" fill="none" stroke="{stroke}" stroke-width="{width}" stroke-opacity="{opacity}" '
            f'stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="{length:.1f}">'
            f'<animate attributeName="stroke-dashoffset" values="{length:.1f};{length:.1f};0" '
            f'keyTimes="0;{delay / (delay + dur):.4f};1" dur="{delay + dur:.2f}s" fill="freeze"/></polyline>')


def text(x, y, content, t, size=12, color=None, family=MONO, weight=400, anchor="start", spacing=0, delay=None):
    anim = fade(delay) if delay is not None else ""
    ls = f' letter-spacing="{spacing}"' if spacing else ""
    return (f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" font-weight="{weight}" '
            f'fill="{color or t["fg"]}" text-anchor="{anchor}"{ls} xml:space="preserve">{escape(content)}{anim}</text>')


def sheet(t, h, label, aria, body):
    """Grid-paper panel with a drawing border, corner marks and a sheet label."""
    x0, y0, x1, y1 = 10, 10, W - 10, h - 10
    marks = []
    for cx, cy, dx, dy in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        marks.append(f'<polyline points="{cx + 14 * dx},{cy} {cx},{cy} {cx},{cy + 14 * dy}" fill="none" '
                     f'stroke="{t["accent"]}" stroke-width="2"/>')
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img" aria-label="{escape(aria)}">
  <title>{escape(aria)}</title>
  <defs>
    <pattern id="minor" width="12" height="12" patternUnits="userSpaceOnUse" x="{x0}" y="{y0}">
      <path d="M12 0.5H0.5V12" fill="none" stroke="{t['line']}" stroke-opacity="{t['minor']}"/>
    </pattern>
    <pattern id="major" width="60" height="60" patternUnits="userSpaceOnUse" x="{x0}" y="{y0}">
      <path d="M60 0.5H0.5V60" fill="none" stroke="{t['line']}" stroke-opacity="{t['major']}"/>
    </pattern>
  </defs>
  <rect x="0.5" y="0.5" width="{W - 1}" height="{h - 1}" rx="6" fill="{t['bg']}" stroke="{t['line']}" stroke-opacity="0.45"/>
  <rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" fill="url(#minor)"/>
  <rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" fill="url(#major)" stroke="{t['line']}" stroke-opacity="0.3"/>
  {''.join(marks)}
  {text(30, 40, label, t, size=11, color=t['muted'], spacing=2)}
{body}
</svg>
"""

# ---- Panels --------------------------------------------------------------------


def hero_svg(t):
    h = 250
    body = [
        text(28, 110, NAME, t, size=48, family=SANS, weight=700, delay=0.15),
        text(30, 144, ROLE, t, size=16, family=SANS, color=t["muted"], delay=0.4),
        draw([(30, 166), (92, 166)], t, 0.55, 0.5, width=3, color=t["accent"]),
        text(30, 198, TAGLINE, t, size=15, color=t["accent"], weight=600, delay=0.75),
    ]

    # Line-drawn cube with a centre line and a dimension line, top right.
    cx, cy, s = 700, 78, 42
    a, b = s * math.cos(math.radians(30)), s / 2
    T0, T1, T2, T3 = (cx, cy - 2 * b), (cx + a, cy - b), (cx, cy), (cx - a, cy - b)
    B1, B2, B3 = (cx + a, cy - b + s), (cx, cy + s), (cx - a, cy - b + s)
    body += [
        draw([(cx, 22), (cx, 160)], t, 0.1, 0.6, width=1, opacity=0.45, dash="8 4 2 4"),
        draw([T0, T1, T2, T3, T0], t, 0.2),
        draw([T3, B3, B2, B1, T1], t, 0.45),
        draw([T2, B2], t, 0.7, 0.4),
        draw([(cx - a, 128), (cx - a, 142)], t, 0.85, 0.2, width=1, opacity=0.7),
        draw([(cx + a, 128), (cx + a, 142)], t, 0.85, 0.2, width=1, opacity=0.7),
        draw([(cx - a, 135), (cx + a, 135)], t, 0.95, 0.4, width=1, opacity=0.7),
        text(cx, 152, "1 : 1", t, size=10, color=t["muted"], anchor="middle", delay=1.1),
    ]

    # Title block, bottom right, like the corner of an engineering drawing.
    widths = [104, 108, 84]
    bx, by, bh = W - 20 - sum(widths), 168, 58
    cells = [f'<rect x="{bx}" y="{by}" width="{sum(widths)}" height="{bh}" fill="{t["bg"]}" stroke="{t["line"]}" stroke-opacity="0.6"/>']
    x = bx
    for i, ((label, value), w) in enumerate(zip(TITLE_BLOCK, widths)):
        if i:
            cells.append(f'<line x1="{x}" y1="{by}" x2="{x}" y2="{by + bh}" stroke="{t["line"]}" stroke-opacity="0.6"/>')
        cells.append(text(x + 10, by + 19, label, t, size=9, color=t["muted"], spacing=1.5))
        cells.append(text(x + 10, by + 43, value, t, size=13))
        x += w
    body.append(f'  <g>{"".join(cells)}{fade(1.0)}</g>')

    return sheet(t, h, "SHEET 01 — PROFILE", f"{NAME}. {ROLE}. {TAGLINE}", "\n".join(f"  {b}" for b in body))


def portfolio_svg(t):
    h = 150
    body = [
        text(30, 88, f"{PORTFOLIO_HOST} ↗", t, size=26, family=SANS, weight=700, delay=0.15),
        text(30, 113, PORTFOLIO_DESC, t, size=14, family=SANS, color=t["muted"], delay=0.35),
        text(30, 132, PORTFOLIO_STACK, t, size=10, color=t["accent"], spacing=1.5, delay=0.5),
    ]

    # Wireframe of a web page with a chat widget, right side.
    x0, y0, x1, y1 = 598, 24, 812, 128
    body += [
        draw([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], t, 0.1, 0.9),
        draw([(x0, y0 + 16), (x1, y0 + 16)], t, 0.5, 0.4, width=1, opacity=0.7),
        draw([(x0 + 42, y0 + 4), (x1 - 10, y0 + 4), (x1 - 10, y0 + 12), (x0 + 42, y0 + 12), (x0 + 42, y0 + 4)],
             t, 0.6, 0.4, width=1, opacity=0.6),
        draw([(x0 + 14, y0 + 32), (x0 + 96, y0 + 32)], t, 0.7, 0.3, width=4),
        draw([(x0 + 14, y0 + 46), (x0 + 120, y0 + 46)], t, 0.8, 0.3, width=2, opacity=0.5),
        draw([(x0 + 14, y0 + 55), (x0 + 108, y0 + 55)], t, 0.85, 0.3, width=2, opacity=0.5),
        draw([(x0 + 14, y0 + 68), (x0 + 96, y0 + 68), (x0 + 96, y0 + 94), (x0 + 14, y0 + 94), (x0 + 14, y0 + 68)],
             t, 0.9, 0.4, width=1, opacity=0.6),
        draw([(x0 + 14, y0 + 68), (x0 + 96, y0 + 94)], t, 1.0, 0.3, width=1, opacity=0.35),
        draw([(x0 + 96, y0 + 68), (x0 + 14, y0 + 94)], t, 1.0, 0.3, width=1, opacity=0.35),
    ]
    dots = "".join(f'<circle cx="{x0 + 9 + 9 * k}" cy="{y0 + 8}" r="2.5" fill="{t["line"]}" fill-opacity="0.7"/>'
                   for k in range(3))
    bx, by = x1 - 98, y1 - 50
    bubble = (f'<rect x="{bx}" y="{by}" width="62" height="24" rx="8" fill="{t["bg"]}" stroke="{t["accent"]}" stroke-width="1.4"/>'
              + "".join(f'<circle cx="{bx + 19 + 12 * k}" cy="{by + 12}" r="2.5" fill="{t["accent"]}"/>' for k in range(3))
              + f'<circle cx="{x1 - 18}" cy="{y1 - 16}" r="9" fill="{t["accent"]}"/>')
    body += [f"<g>{dots}{fade(0.5, 0.4)}</g>", f"<g>{bubble}{fade(1.15, 0.5)}</g>"]

    aria = f"Portfolio: {PORTFOLIO_HOST}. {PORTFOLIO_DESC}. Built with React, TypeScript, Vite, Tailwind and Flowise."
    return sheet(t, h, "DETAIL A — PORTFOLIO", aria, "\n".join(f"  {b}" for b in body))


def parts_svg(t):
    cols, col_w, chip_w, chip_h, row_h, top = 4, 197, 185, 36, 44, 58
    rows = (len(PARTS) + cols - 1) // cols
    h = top + rows * row_h + 18
    x_start = (W - cols * col_w) / 2 + (col_w - chip_w) / 2
    body = []
    for i, (icon_id, label) in enumerate(PARTS):
        x = x_start + (i % cols) * col_w
        y = top + (i // cols) * row_h
        icon = icon_data_uri(icon_id, t["icons"]) if icon_id else None
        if icon:
            glyph = f'<image x="{x + 8}" y="{y + 7}" width="22" height="22" href="{icon}"/>'
        else:  # sparkle for AI tools, or a fallback if the icon could not be fetched
            gx, gy = x + 19, y + 18
            glyph = (f'<path d="M{gx} {gy - 10} Q{gx} {gy} {gx + 10} {gy} Q{gx} {gy} {gx} {gy + 10} '
                     f'Q{gx} {gy} {gx - 10} {gy} Q{gx} {gy} {gx} {gy - 10}Z" fill="{t["accent"]}"/>')
        body.append(
            f'  <g><rect x="{x}" y="{y}" width="{chip_w}" height="{chip_h}" rx="4" fill="{t["chip"]}" '
            f'stroke="{t["line"]}" stroke-opacity="0.35"/>{glyph}'
            f'{text(x + 40, y + 23, f"{i + 1:02d}", t, size=10, color=t["muted"])}'
            f'{text(x + 62, y + 23, label, t, size=13)}{fade(0.1 + 0.05 * i, 0.4)}</g>')
    return sheet(t, h, "FIG. 01 — PARTS LIST", "Stack: " + ", ".join(p[1] for p in PARTS), "\n".join(body))


def languages_svg(t, top, total):
    h, cell, cy, r = 228, 132, 112, 38
    x_start = (W - len(top) * cell) / 2 + cell / 2
    circ = 2 * math.pi * r
    body = []
    for i, (lang, size) in enumerate(top):
        cx = x_start + i * cell
        pct = size / total * 100
        arc = circ * pct / 100
        color = LANG_COLORS.get(lang, t["muted"])
        ticks = []
        for k in range(60):
            ang = math.radians(k * 6 - 90)
            r0 = 44 if k % 5 == 0 else 46
            ticks.append(f"M{cx + r0 * math.cos(ang):.1f} {cy + r0 * math.sin(ang):.1f}"
                         f"L{cx + 50 * math.cos(ang):.1f} {cy + 50 * math.sin(ang):.1f}")
        delay, dur = 0.15 * i, 1.1
        hold = delay / (delay + dur)
        body.append(f"""  <g>
    <path d="{''.join(ticks)}" stroke="{t['line']}" stroke-opacity="0.35" stroke-width="1"/>
    <circle cx="{cx:.1f}" cy="{cy}" r="{r}" fill="none" stroke="{t['track']}" stroke-width="7"/>
    <circle cx="{cx:.1f}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="7"
            stroke-dasharray="{arc:.2f} {circ:.2f}" transform="rotate(-90 {cx:.1f} {cy})">
      <animate attributeName="stroke-dasharray" values="0 {circ:.2f};0 {circ:.2f};{arc:.2f} {circ:.2f}" keyTimes="0;{hold:.4f};1"
               dur="{delay + dur:.2f}s" calcMode="spline" keySplines="0 0 1 1;0.2 0.7 0.3 1" fill="freeze"/>
    </circle>
    {text(f"{cx:.1f}", cy + 6, f"{pct:.1f}%", t, size=16, weight=700, anchor="middle")}
    {text(f"{cx:.1f}", cy + r + 30, lang.upper(), t, size=11, color=t['muted'], anchor="middle", spacing=1.2)}
  </g>""")
    body.append("  " + text(W - 30, h - 22, "bytes of code across public repos · updated daily", t,
                            size=10, color=t["muted"], anchor="end"))
    aria = "Language share: " + ", ".join(f"{lang} {size / total * 100:.1f}%" for lang, size in top)
    return sheet(t, h, "FIG. 02 — LANGUAGE SHARE", aria, "\n".join(body))


def main():
    OUT.mkdir(exist_ok=True)
    for name, theme in THEMES.items():
        (OUT / f"hero-{name}.svg").write_text(hero_svg(theme), encoding="utf-8")
        (OUT / f"portfolio-{name}.svg").write_text(portfolio_svg(theme), encoding="utf-8")
        (OUT / f"parts-{name}.svg").write_text(parts_svg(theme), encoding="utf-8")
    try:
        totals = language_totals()
    except OSError as err:  # rate limit or network trouble: keep the last good panel
        print(f"Skipping language panel, GitHub API unavailable: {err}")
        return
    total = sum(totals.values())
    top = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:TOP_N]
    for name, theme in THEMES.items():
        (OUT / f"languages-{name}.svg").write_text(languages_svg(theme, top, total), encoding="utf-8")
    for lang, size in top:
        print(f"{lang:<12} {size / total * 100:5.1f}%")


if __name__ == "__main__":
    main()
