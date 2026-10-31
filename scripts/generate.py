#!/usr/bin/env python3
"""Build the SVGs used by the profile README.

Writes, for both GitHub themes:
  assets/header-{dark,light}.svg     animated typing headline
  assets/languages-{dark,light}.svg  language-share rings, from public repos

Usage: python3 scripts/generate.py
Env:   GH_USER (default ianjohndal5), GITHUB_TOKEN (optional; raises the API rate limit)
"""

import json
import os
import urllib.request
from pathlib import Path

USER = os.environ.get("GH_USER", "ianjohndal5")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = Path(__file__).resolve().parent.parent / "assets"

TOP_N = 6
SKIP_REPOS = {USER}              # the profile repo itself
SKIP_LANGUAGES = set()           # e.g. {"HTML", "CSS"} to count only programming languages

HEADLINE = "am i gonna be a programmer?"
SUBTITLE = "hi, i'm ian  ·  web apps  ·  dev tools  ·  game mods"

MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', 'DejaVu Sans Mono', monospace"

THEMES = {
    "dark": dict(bg="#161b22", border="#30363d", fg="#e6edf3", muted="#8b949e", accent="#a371f7", track="#30363d"),
    "light": dict(bg="#ffffff", border="#d0d7de", fg="#1f2328", muted="#59636e", accent="#8250df", track="#eaeef2"),
}

# Colours from GitHub Linguist, so the rings match the language bars on repo pages.
LANG_COLORS = {
    "C#": "#178600", "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Python": "#3572A5",
    "HTML": "#e34c26", "CSS": "#663399", "SCSS": "#c6538c", "PHP": "#4F5D95", "Shell": "#89e051",
    "Java": "#b07219", "C++": "#f34b7d", "C": "#555555", "Go": "#00ADD8", "Rust": "#dea584",
    "Lua": "#000080", "Luau": "#00A2FF", "Kotlin": "#A97BFF", "Dart": "#00B4AB", "Vue": "#41b883",
    "Svelte": "#ff3e00", "PowerShell": "#012456", "Batchfile": "#C1F12E", "Dockerfile": "#384d54",
    "Tree-sitter Query": "#8ea64c", "GDScript": "#355570", "Swift": "#F05138", "Ruby": "#701516",
}


def api(path):
    req = urllib.request.Request(f"https://api.github.com{path}", headers={"Accept": "application/vnd.github+json"})
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def language_totals():
    repos, page = [], 1
    while True:
        batch = api(f"/users/{USER}/repos?per_page=100&type=owner&page={page}")
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    totals = {}
    for repo in repos:
        if repo["fork"] or repo["name"] in SKIP_REPOS:
            continue
        for lang, size in api(f"/repos/{USER}/{repo['name']}/languages").items():
            if lang not in SKIP_LANGUAGES:
                totals[lang] = totals.get(lang, 0) + size
    return totals


def header_svg(t):
    w, h, size = 800, 128, 30
    char_w = size * 0.6
    text_w = len(HEADLINE) * char_w
    x0 = (w - text_w) / 2
    lead, typing = 0.4, 2.2               # seconds before typing starts, typing duration
    total = lead + typing
    steps = [round(i * char_w, 2) for i in range(len(HEADLINE) + 1)]
    # Hold at 0 during the lead-in, then reveal one character per step. The base
    # attributes hold the final state, so static renderers show the full text.
    widths = ";".join(["0"] + [str(s) for s in steps])
    cursor_x = ";".join([str(round(x0 + 2, 2))] + [str(round(x0 + s + 2, 2)) for s in steps])
    key_times = ";".join(["0"] + [f"{(lead + typing * i / len(HEADLINE)) / total:.4f}" for i in range(len(HEADLINE) + 1)])
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{HEADLINE}">
  <title>{HEADLINE}</title>
  <defs>
    <clipPath id="type">
      <rect x="{x0}" y="10" height="60" width="{text_w}">
        <animate attributeName="width" values="{widths}" keyTimes="{key_times}" dur="{total}s" calcMode="discrete" fill="freeze"/>
      </rect>
    </clipPath>
  </defs>
  <text x="{x0}" y="56" textLength="{text_w}" lengthAdjust="spacing" clip-path="url(#type)"
        font-family="{MONO}" font-size="{size}" font-weight="600" fill="{t['accent']}">{HEADLINE}</text>
  <rect x="{x0 + text_w + 2}" y="30" width="3" height="34" fill="{t['accent']}">
    <animate attributeName="x" values="{cursor_x}" keyTimes="{key_times}" dur="{total}s" calcMode="discrete" fill="freeze"/>
    <animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="1.05s" repeatCount="indefinite"/>
  </rect>
  <text x="{w / 2}" y="104" text-anchor="middle" font-family="{MONO}" font-size="15" fill="{t['muted']}" xml:space="preserve">{SUBTITLE}<animate attributeName="opacity" values="0;0;1" keyTimes="0;{total / (total + 0.8):.4f};1" dur="{total + 0.8}s" fill="freeze"/></text>
</svg>
"""


def languages_svg(t, top, total):
    cols, cell_w, w = 3, 170, 540
    rows = (len(top) + cols - 1) // cols
    r, stroke = 40, 9
    circ = 2 * 3.14159265 * r
    row_h, top_pad = 142, 104
    h = top_pad + (rows - 1) * row_h + 112
    x_start = (w - cols * cell_w) / 2 + cell_w / 2
    parts = []
    for i, (lang, size) in enumerate(top):
        cx = x_start + (i % cols) * cell_w
        cy = top_pad + (i // cols) * row_h
        pct = size / total * 100
        arc = circ * pct / 100
        color = LANG_COLORS.get(lang, t["muted"])
        delay, dur = 0.15 * i, 1.1
        hold = delay / (delay + dur)
        parts.append(f"""  <g>
    <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{t['track']}" stroke-width="{stroke}"/>
    <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="{stroke}" stroke-linecap="round"
            stroke-dasharray="{arc:.2f} {circ:.2f}" transform="rotate(-90 {cx} {cy})">
      <animate attributeName="stroke-dasharray" values="0 {circ:.2f};0 {circ:.2f};{arc:.2f} {circ:.2f}" keyTimes="0;{hold:.4f};1"
               dur="{delay + dur:.2f}s" calcMode="spline" keySplines="0 0 1 1;0.2 0.7 0.3 1" fill="freeze"/>
    </circle>
    <text x="{cx}" y="{cy + 6}" text-anchor="middle" font-family="{MONO}" font-size="16" font-weight="700" fill="{t['fg']}">{pct:.1f}%</text>
    <text x="{cx}" y="{cy + r + 28}" text-anchor="middle" font-family="{MONO}" font-size="13" fill="{t['muted']}">{lang}</text>
  </g>""")
    label = ", ".join(f"{lang} {size / total * 100:.1f}%" for lang, size in top)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Most used languages: {label}">
  <title>Most used languages: {label}</title>
  <rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="6" fill="{t['bg']}" stroke="{t['border']}"/>
  <text x="24" y="34" font-family="{MONO}" font-size="14" font-weight="600" fill="{t['accent']}">most used languages</text>
{chr(10).join(parts)}
  <text x="{w - 24}" y="{h - 16}" text-anchor="end" font-family="{MONO}" font-size="11" fill="{t['muted']}">share of code across public repos</text>
</svg>
"""


def main():
    OUT.mkdir(exist_ok=True)
    totals = language_totals()
    total = sum(totals.values())
    top = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:TOP_N]
    for name, theme in THEMES.items():
        (OUT / f"header-{name}.svg").write_text(header_svg(theme), encoding="utf-8")
        (OUT / f"languages-{name}.svg").write_text(languages_svg(theme, top, total), encoding="utf-8")
    for lang, size in top:
        print(f"{lang:<12} {size / total * 100:5.1f}%")


if __name__ == "__main__":
    main()
