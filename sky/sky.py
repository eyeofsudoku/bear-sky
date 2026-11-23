#!/usr/bin/env python3
"""
Berlin sky for a Bear blog.

  python sky/sky.py sky      -> set the theme from Berlin's weather and time of day
  python sky/sky.py quotes   -> refresh the list of posts tagged "quotable" (kept in the theme)
  python sky/sky.py tag-all  -> one-off: tag every existing post "quotable", except the excluded titles
  add --dry-run to print what would be sent without changing the blog

Needs the environment variables BEAR_API_KEY and BEAR_SUBDOMAIN.
Standard library only.
"""

import html
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
BERLIN = ZoneInfo("Europe/Berlin")
LAT, LON = 52.52, 13.405
USER_AGENT = "bear-sky/1.0 (+https://github.com/eyeofsudoku/bear-sky)"

# Only posts with this tag are quoted. Tag new posts yourself when you want them in the pool.
QUOTE_TAG = "quotable"
# Used once by "tag-all": posts whose title starts with one of these do NOT get the tag
# (song lyrics and translations are other people's words).
EXCLUDE_TITLE_PREFIXES = ["bazı şarkılar", "serbest çeviri"]

# ---------------------------------------------------------------- palettes (time of day)

# text colours of the light skins; each skin sets every colour so switching skins never mixes two
LIGHT_TEXT = {
    "--heading-color": "#1a1a1a", "--text-color": "#3a3530", "--link-color": "#2a6db5",
    "--visited-color": "#7a5faa", "--blockquote-color": "#5a524a",
    "--code-background-color": "#eeece7", "--code-color": "#2a2520",
}

SKINS = {
    "dawn": {
        "--accent": "#b0644e",
        "--sky": "linear-gradient(180deg, #f1d9d1 0%, #f4e7e0 38%, #f8f4ee 100%)",
        "--link-color": "#245f9e", "--visited-color": "#6c4f9c", "--blockquote-color": "#5f554c",
        "--glow": "255, 186, 150", "--sun-pos": "14% 20%", "--disc": "26px",
        "--fx": "75, 85, 110", "--cloud": "rgba(200, 184, 190, .5)", "--wash": "rgba(150, 140, 150, .24)",
        "--fog": "238, 233, 230", "--veil": "246, 237, 232", "--frame": "58, 53, 48",
    },
    "day": {
        "--accent": "#b07a2a",
        "--sky": "linear-gradient(180deg, #dce9f4 0%, #ecf0f1 40%, #f8f6f1 100%)",
        "--link-color": "#245f9e", "--visited-color": "#6c4f9c",
        "--glow": "255, 210, 110", "--sun-pos": "82% 16%", "--disc": "30px",
        "--fx": "70, 85, 110", "--cloud": "rgba(182, 194, 208, .5)", "--wash": "rgba(140, 150, 165, .24)",
        "--fog": "236, 235, 232", "--veil": "244, 244, 242", "--frame": "58, 53, 48",
    },
    "dusk": {
        "--accent": "#b0563a",
        "--sky": "linear-gradient(180deg, #e0c2c0 0%, #ebd4c6 40%, #f4ebe2 100%)",
        "--text-color": "#3a3028", "--link-color": "#2a5891", "--visited-color": "#684c95",
        "--blockquote-color": "#5d5047",
        "--glow": "240, 140, 100", "--sun-pos": "88% 22%", "--disc": "26px",
        "--fx": "80, 75, 95", "--cloud": "rgba(188, 160, 162, .5)", "--wash": "rgba(140, 125, 130, .26)",
        "--fog": "236, 228, 224", "--veil": "242, 232, 226", "--frame": "58, 48, 40",
    },
    "night": {
        "--accent": "#e3c27a",
        "--sky": "linear-gradient(180deg, #0c1323 0%, #141a2a 50%, #1a1d26 100%)",
        "--heading-color": "#ece8e1", "--text-color": "#cdc8bf", "--link-color": "#8cc2e0",
        "--visited-color": "#b2a0d6", "--blockquote-color": "#a29d94",
        "--code-background-color": "#232838", "--code-color": "#cdc8bf",
        "--glow": "232, 232, 250", "--sun-pos": "82% 15%", "--disc": "13px",
        "--fx": "180, 200, 230", "--cloud": "rgba(62, 72, 98, .6)", "--wash": "rgba(0, 0, 0, .22)",
        "--fog": "70, 75, 88", "--veil": "18, 22, 34", "--frame": "205, 200, 191",
    },
}

# ---------------------------------------------------------------- weather layers (all still, no animation)

STARS = ",\n    ".join(
    f"radial-gradient(circle at {x}% {y}%, rgba(255,255,255,{a}) 0 {r}px, transparent {r + .6:.1f}px)"
    for x, y, a, r in [
        (6, 12, .9, 1), (14, 31, .7, 1), (22, 8, .8, 1.3), (29, 22, .6, 1), (37, 5, .9, 1),
        (44, 27, .7, 1.2), (51, 13, .8, 1), (58, 34, .5, 1), (64, 6, .9, 1.4), (71, 24, .7, 1),
        (93, 18, .8, 1), (97, 37, .6, 1), (9, 52, .5, 1), (26, 64, .4, 1), (47, 58, .45, 1),
        (68, 71, .4, 1), (88, 61, .5, 1.2), (16, 86, .35, 1), (79, 90, .35, 1), (54, 83, .3, 1),
    ]
)



WEATHER = {
    "clear": """
html::before {
    background: radial-gradient(circle at var(--sun-pos),
        rgba(var(--glow), .8) 0 var(--disc),
        rgba(var(--glow), .3) calc(var(--disc) + 2px),
        rgba(var(--glow), .1) 130px,
        transparent 280px);
}
""",
    "cloudy": """
html::before {
    inset: -10%;
    background:
        radial-gradient(ellipse 300px 80px at 18% 14%, var(--cloud), transparent 70%),
        radial-gradient(ellipse 360px 100px at 66% 7%, var(--cloud), transparent 70%),
        radial-gradient(ellipse 260px 70px at 44% 30%, var(--cloud), transparent 70%),
        radial-gradient(ellipse 340px 90px at 92% 38%, var(--cloud), transparent 70%),
        radial-gradient(ellipse 280px 70px at 8% 58%, var(--cloud), transparent 70%),
        radial-gradient(ellipse 320px 80px at 70% 78%, var(--cloud), transparent 70%);
}
html::after {
    background: var(--wash);
    opacity: .6;
}
""",
    "rain": """
html::before {
    background: var(--wash);
}
""",
    "snow": """
html::before {
    background: var(--wash);
}
""",
    "fog": """
html::before {
    inset: -10%;
    background:
        radial-gradient(ellipse 55% 16% at 28% 34%, rgba(var(--fog), .7), transparent 70%),
        radial-gradient(ellipse 50% 14% at 74% 68%, rgba(var(--fog), .6), transparent 70%),
        linear-gradient(180deg, rgba(var(--fog), .15) 0%, rgba(var(--fog), .6) 28%, rgba(var(--fog), .3) 55%, rgba(var(--fog), .65) 82%, rgba(var(--fog), .4) 100%);
}
""",
}

NIGHT_STARS = "\nhtml::after {\n    background-image:\n    " + STARS + ";\n}\n"


# ---------------------------------------------------------------- weather symbol in the Berlin badge
# Each icon: (shape, colour, animation, keyframes, desktop w, h, phone w, h). Shapes are single-colour masks.

KF = {
    "spin": "@keyframes sky-spin { to { transform: rotate(45deg); } }",
    "float": "@keyframes sky-float { 0%, 100% { transform: translateY(-1.5px); } 50% { transform: translateY(1.5px); } }",
    "drift": "@keyframes sky-drift { 0%, 100% { transform: translateX(-2.5px); } 50% { transform: translateX(2.5px); } }",
    "haze": "@keyframes sky-haze { 0%, 100% { transform: translateX(-3px); opacity: .7; } 50% { transform: translateX(3px); opacity: 1; } }",
    "drip": "@keyframes sky-drip { 0% { transform: translateY(-7px) scale(.85); opacity: 0; } 18% { opacity: 1; } 62% { transform: translateY(3px) scale(1); opacity: 1; } 82% { transform: translateY(7px) scaleY(.8) scaleX(1.15); opacity: 0; } 100% { transform: translateY(7px); opacity: 0; } }",
    "flake": "@keyframes sky-flake { 0% { transform: translate(-1px, -2px) rotate(0deg); } 50% { transform: translate(1px, 2px) rotate(30deg); } 100% { transform: translate(-1px, -2px) rotate(60deg); } }",
    "flash": "@keyframes sky-flash { 0%, 70%, 78%, 86%, 100% { opacity: 1; } 74%, 82% { opacity: .25; } }",
}

ICONS = {
    "sun": ('url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20viewBox%3D%22-16%20-16%2032%2032%22%3E%3Ccircle%20r%3D%226%22%20fill%3D%22%23000%22/%3E%3Crect%20x%3D%22-1.3%22%20y%3D%22-15%22%20width%3D%222.6%22%20height%3D%225.5%22%20rx%3D%221.3%22%20fill%3D%22%23000%22%20transform%3D%22rotate%280%29%22/%3E%3Crect%20x%3D%22-1.3%22%20y%3D%22-15%22%20width%3D%222.6%22%20height%3D%225.5%22%20rx%3D%221.3%22%20fill%3D%22%23000%22%20transform%3D%22rotate%2845%29%22/%3E%3Crect%20x%3D%22-1.3%22%20y%3D%22-15%22%20width%3D%222.6%22%20height%3D%225.5%22%20rx%3D%221.3%22%20fill%3D%22%23000%22%20transform%3D%22rotate%2890%29%22/%3E%3Crect%20x%3D%22-1.3%22%20y%3D%22-15%22%20width%3D%222.6%22%20height%3D%225.5%22%20rx%3D%221.3%22%20fill%3D%22%23000%22%20transform%3D%22rotate%28135%29%22/%3E%3Crect%20x%3D%22-1.3%22%20y%3D%22-15%22%20width%3D%222.6%22%20height%3D%225.5%22%20rx%3D%221.3%22%20fill%3D%22%23000%22%20transform%3D%22rotate%28180%29%22/%3E%3Crect%20x%3D%22-1.3%22%20y%3D%22-15%22%20width%3D%222.6%22%20height%3D%225.5%22%20rx%3D%221.3%22%20fill%3D%22%23000%22%20transform%3D%22rotate%28225%29%22/%3E%3Crect%20x%3D%22-1.3%22%20y%3D%22-15%22%20width%3D%222.6%22%20height%3D%225.5%22%20rx%3D%221.3%22%20fill%3D%22%23000%22%20transform%3D%22rotate%28270%29%22/%3E%3Crect%20x%3D%22-1.3%22%20y%3D%22-15%22%20width%3D%222.6%22%20height%3D%225.5%22%20rx%3D%221.3%22%20fill%3D%22%23000%22%20transform%3D%22rotate%28315%29%22/%3E%3C/svg%3E")', "var(--accent)", "sky-spin 9s linear infinite", "spin", 34, 34, 18, 18),
    "moon": ('url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20viewBox%3D%22-16%20-16%2032%2032%22%3E%3Cpath%20d%3D%22M3.5%20-13%20A13%2013%200%201%200%2013%203.5%20A10%2010%200%200%201%203.5%20-13%20Z%22%20fill%3D%22%23000%22/%3E%3C/svg%3E")', "var(--accent)", "sky-float 4s ease-in-out infinite", "float", 30, 30, 17, 17),
    "partly-day": ('url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20viewBox%3D%22-16%20-16%2032%2032%22%3E%3Cdefs%3E%3Cmask%20id%3D%22m%22%3E%3Crect%20x%3D%22-16%22%20y%3D%22-16%22%20width%3D%2232%22%20height%3D%2232%22%20fill%3D%22%23fff%22/%3E%3Cpath%20d%3D%22M-8%2011%20H8.5%20A6.5%206.5%200%200%200%209.3%20-1.9%20A9%209%200%200%200%20-7.8%20-3.2%20A7%207%200%200%200%20-8%2011%20Z%22%20transform%3D%22translate%282%203%29%22%20fill%3D%22%23000%22%20stroke%3D%22%23000%22%20stroke-width%3D%224%22/%3E%3C/mask%3E%3C/defs%3E%3Cg%20mask%3D%22url%28%23m%29%22%3E%3Cg%20transform%3D%22translate%28-5%20-5%29%20scale%280.62%29%22%3E%3Ccircle%20r%3D%226%22%20fill%3D%22%23000%22/%3E%3Crect%20x%3D%22-1.3%22%20y%3D%22-15%22%20width%3D%222.6%22%20height%3D%225.5%22%20rx%3D%221.3%22%20fill%3D%22%23000%22%20transform%3D%22rotate%280%29%22/%3E%3Crect%20x%3D%22-1.3%22%20y%3D%22-15%22%20width%3D%222.6%22%20height%3D%225.5%22%20rx%3D%221.3%22%20fill%3D%22%23000%22%20transform%3D%22rotate%2845%29%22/%3E%3Crect%20x%3D%22-1.3%22%20y%3D%22-15%22%20width%3D%222.6%22%20height%3D%225.5%22%20rx%3D%221.3%22%20fill%3D%22%23000%22%20transform%3D%22rotate%2890%29%22/%3E%3Crect%20x%3D%22-1.3%22%20y%3D%22-15%22%20width%3D%222.6%22%20height%3D%225.5%22%20rx%3D%221.3%22%20fill%3D%22%23000%22%20transform%3D%22rotate%28135%29%22/%3E%3Crect%20x%3D%22-1.3%22%20y%3D%22-15%22%20width%3D%222.6%22%20height%3D%225.5%22%20rx%3D%221.3%22%20fill%3D%22%23000%22%20transform%3D%22rotate%28180%29%22/%3E%3Crect%20x%3D%22-1.3%22%20y%3D%22-15%22%20width%3D%222.6%22%20height%3D%225.5%22%20rx%3D%221.3%22%20fill%3D%22%23000%22%20transform%3D%22rotate%28225%29%22/%3E%3Crect%20x%3D%22-1.3%22%20y%3D%22-15%22%20width%3D%222.6%22%20height%3D%225.5%22%20rx%3D%221.3%22%20fill%3D%22%23000%22%20transform%3D%22rotate%28270%29%22/%3E%3Crect%20x%3D%22-1.3%22%20y%3D%22-15%22%20width%3D%222.6%22%20height%3D%225.5%22%20rx%3D%221.3%22%20fill%3D%22%23000%22%20transform%3D%22rotate%28315%29%22/%3E%3C/g%3E%3C/g%3E%3Cpath%20d%3D%22M-8%2011%20H8.5%20A6.5%206.5%200%200%200%209.3%20-1.9%20A9%209%200%200%200%20-7.8%20-3.2%20A7%207%200%200%200%20-8%2011%20Z%22%20transform%3D%22translate%282%203%29%22%20fill%3D%22%23000%22/%3E%3C/svg%3E")', "var(--link-color)", "sky-drift 6s ease-in-out infinite", "drift", 36, 36, 19, 19),
    "partly-night": ('url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20viewBox%3D%22-16%20-16%2032%2032%22%3E%3Cdefs%3E%3Cmask%20id%3D%22m%22%3E%3Crect%20x%3D%22-16%22%20y%3D%22-16%22%20width%3D%2232%22%20height%3D%2232%22%20fill%3D%22%23fff%22/%3E%3Cpath%20d%3D%22M-8%2011%20H8.5%20A6.5%206.5%200%200%200%209.3%20-1.9%20A9%209%200%200%200%20-7.8%20-3.2%20A7%207%200%200%200%20-8%2011%20Z%22%20transform%3D%22translate%282%203%29%22%20fill%3D%22%23000%22%20stroke%3D%22%23000%22%20stroke-width%3D%224%22/%3E%3C/mask%3E%3C/defs%3E%3Cg%20mask%3D%22url%28%23m%29%22%3E%3Cg%20transform%3D%22translate%28-5%20-5%29%20scale%280.6%29%22%3E%3Cpath%20d%3D%22M3.5%20-13%20A13%2013%200%201%200%2013%203.5%20A10%2010%200%200%201%203.5%20-13%20Z%22%20fill%3D%22%23000%22/%3E%3C/g%3E%3C/g%3E%3Cpath%20d%3D%22M-8%2011%20H8.5%20A6.5%206.5%200%200%200%209.3%20-1.9%20A9%209%200%200%200%20-7.8%20-3.2%20A7%207%200%200%200%20-8%2011%20Z%22%20transform%3D%22translate%282%203%29%22%20fill%3D%22%23000%22/%3E%3C/svg%3E")', "var(--link-color)", "sky-drift 6s ease-in-out infinite", "drift", 36, 36, 19, 19),
    "cloud": ('url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20viewBox%3D%22-16%20-16%2032%2032%22%3E%3Cpath%20d%3D%22M-8%2011%20H8.5%20A6.5%206.5%200%200%200%209.3%20-1.9%20A9%209%200%200%200%20-7.8%20-3.2%20A7%207%200%200%200%20-8%2011%20Z%22%20fill%3D%22%23000%22/%3E%3C/svg%3E")', "var(--link-color)", "sky-drift 6s ease-in-out infinite", "drift", 36, 36, 19, 19),
    "fog": ('url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20viewBox%3D%22-16%20-16%2032%2032%22%20stroke%3D%22%23000%22%20stroke-width%3D%222.6%22%20stroke-linecap%3D%22round%22%3E%3Cpath%20d%3D%22M-12%20-7%20H8%22/%3E%3Cpath%20d%3D%22M-6%200%20H13%22/%3E%3Cpath%20d%3D%22M-13%207%20H5%22/%3E%3Cpath%20d%3D%22M-4%2014%20H10%22%20opacity%3D%22.001%22/%3E%3C/svg%3E")', "var(--link-color)", "sky-haze 5s ease-in-out infinite", "haze", 34, 34, 18, 18),
    "rain": ('url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20viewBox%3D%220%200%2024%2032%22%3E%3Cpath%20d%3D%22M12%201C12%201%202%2013.5%202%2020.5a10%2010%200%200%200%2020%200C22%2013.5%2012%201%2012%201z%22%20fill%3D%22%23000%22/%3E%3C/svg%3E")', "var(--link-color)", "sky-drip 2.6s ease-in infinite", "drip", 24, 34, 13, 18),
    "snow": ('url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20viewBox%3D%22-16%20-16%2032%2032%22%20fill%3D%22none%22%20stroke%3D%22%23000%22%20stroke-width%3D%222.2%22%20stroke-linecap%3D%22round%22%3E%3Cg%20transform%3D%22rotate%280%29%22%3E%3Cpath%20d%3D%22M0%200V-13M0%20-8.5L-3.5%20-11.5M0%20-8.5L3.5%20-11.5M0%20-4L-2.5%20-6.2M0%20-4L2.5%20-6.2%22/%3E%3C/g%3E%3Cg%20transform%3D%22rotate%2860%29%22%3E%3Cpath%20d%3D%22M0%200V-13M0%20-8.5L-3.5%20-11.5M0%20-8.5L3.5%20-11.5M0%20-4L-2.5%20-6.2M0%20-4L2.5%20-6.2%22/%3E%3C/g%3E%3Cg%20transform%3D%22rotate%28120%29%22%3E%3Cpath%20d%3D%22M0%200V-13M0%20-8.5L-3.5%20-11.5M0%20-8.5L3.5%20-11.5M0%20-4L-2.5%20-6.2M0%20-4L2.5%20-6.2%22/%3E%3C/g%3E%3Cg%20transform%3D%22rotate%28180%29%22%3E%3Cpath%20d%3D%22M0%200V-13M0%20-8.5L-3.5%20-11.5M0%20-8.5L3.5%20-11.5M0%20-4L-2.5%20-6.2M0%20-4L2.5%20-6.2%22/%3E%3C/g%3E%3Cg%20transform%3D%22rotate%28240%29%22%3E%3Cpath%20d%3D%22M0%200V-13M0%20-8.5L-3.5%20-11.5M0%20-8.5L3.5%20-11.5M0%20-4L-2.5%20-6.2M0%20-4L2.5%20-6.2%22/%3E%3C/g%3E%3Cg%20transform%3D%22rotate%28300%29%22%3E%3Cpath%20d%3D%22M0%200V-13M0%20-8.5L-3.5%20-11.5M0%20-8.5L3.5%20-11.5M0%20-4L-2.5%20-6.2M0%20-4L2.5%20-6.2%22/%3E%3C/g%3E%3C/svg%3E")', "var(--link-color)", "sky-flake 7s linear infinite", "flake", 34, 34, 18, 18),
    "storm": ('url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20viewBox%3D%22-16%20-16%2032%2032%22%3E%3Cdefs%3E%3Cmask%20id%3D%22m%22%3E%3Crect%20x%3D%22-16%22%20y%3D%22-16%22%20width%3D%2232%22%20height%3D%2232%22%20fill%3D%22%23fff%22/%3E%3Cpath%20d%3D%22M1%200%20L-5%208%20H0%20L-3%2016%20L6%205%20H1%20L4%200%20Z%22%20fill%3D%22%23000%22%20stroke%3D%22%23000%22%20stroke-width%3D%223.5%22%20stroke-linejoin%3D%22round%22/%3E%3C/mask%3E%3C/defs%3E%3Cpath%20d%3D%22M-8%2011%20H8.5%20A6.5%206.5%200%200%200%209.3%20-1.9%20A9%209%200%200%200%20-7.8%20-3.2%20A7%207%200%200%200%20-8%2011%20Z%22%20transform%3D%22translate%280%20-4%29%22%20fill%3D%22%23000%22%20mask%3D%22url%28%23m%29%22/%3E%3Cpath%20d%3D%22M1%200%20L-5%208%20H0%20L-3%2016%20L6%205%20H1%20L4%200%20Z%22%20fill%3D%22%23000%22/%3E%3C/svg%3E")', "var(--link-color)", "sky-flash 4s linear infinite", "flash", 36, 36, 19, 19),
}


def icons_for(code):
    """WMO code -> (day icon, night icon)."""
    if code == 0:
        return "sun", "moon"
    if code in (1, 2):
        return "partly-day", "partly-night"
    if code in (45, 48):
        return "fog", "fog"
    if code in (95, 96, 99):
        return "storm", "storm"
    if code in (71, 73, 75, 77, 85, 86):
        return "snow", "snow"
    if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
        return "rain", "rain"
    return "cloud", "cloud"


def icon_rule(selector, key):
    shape, colour, anim, _, w, h, nw, nh = ICONS[key]
    return (
        f"{selector} .sky-badge::before {{\n"
        f"    width: {w}px;\n    height: {h}px;\n    background: {colour};\n"
        f"    -webkit-mask: {shape} center / contain no-repeat;\n    mask: {shape} center / contain no-repeat;\n"
        f"    animation: {anim};\n}}\n"
        f"@media (max-width: 1000px) {{\n    {selector} .sky-badge::before {{ width: {nw}px; height: {nh}px; }}\n}}\n"
    )


BADGE_LAYOUT = """
/* Berlin badge with a weather symbol on the left */
.sky-badge {
    display: grid;
    grid-template-columns: auto auto;
    column-gap: 14px;
    align-items: center;
    padding-left: 14px;
}
.sky-badge > div {
    grid-column: 2;
}
.sky-badge::before {
    content: "";
    grid-column: 1;
    grid-row: 1 / span 3;
    justify-self: center;
}
@media (max-width: 1000px) {
    .sky-badge {
        display: flex;
        padding-left: 11px;
    }
}
@media (prefers-reduced-motion: reduce) {
    .sky-badge::before {
        animation: none !important;
    }
}
"""


def badge_css(code, time_of_day):
    day, night = icons_for(code)
    used = {ICONS[day][3], ICONS[night][3]}
    css = BADGE_LAYOUT + "\n".join(KF[k] for k in sorted(used)) + "\n"
    css += icon_rule("html", day)
    if night != day:
        css += icon_rule("html.sky-night", night)
        if time_of_day == "night":  # readers without JavaScript
            css += icon_rule("html:not(.sky-js)", night)
    return css


# ---------------------------------------------------------------- weather and time of day

def classify_weather(code):
    """WMO weather code from Open-Meteo -> one of our five skies."""
    if code in (0, 1):
        return "clear"
    if code in (45, 48):
        return "fog"
    if code in (71, 73, 75, 77, 85, 86):
        return "snow"
    if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99):
        return "rain"
    return "cloudy"  # 2, 3 and anything unknown


def classify_time(now, sunrise, sunset):
    h = lambda d: d.hour + d.minute / 60
    t, rise, sset = h(now), h(sunrise), h(sunset)
    if t < rise - 0.5 or t > sset + 0.75:
        return "night"
    if t < rise + 1:
        return "dawn"
    if t > sset - 1:
        return "dusk"
    return "day"


def berlin_weather():
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}"
        "&current=temperature_2m,weather_code&daily=sunrise,sunset"
        "&timezone=Europe%2FBerlin&forecast_days=1"
    )
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                d = json.load(r)
            break
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            if attempt == 2:
                raise SystemExit(f"Weather service unreachable: {e}")
            time.sleep(10)
    now = datetime.now(BERLIN)
    sunrise = datetime.fromisoformat(d["daily"]["sunrise"][0]).replace(tzinfo=BERLIN)
    sunset = datetime.fromisoformat(d["daily"]["sunset"][0]).replace(tzinfo=BERLIN)
    return {
        "time": classify_time(now, sunrise, sunset),
        "weather": classify_weather(int(d["current"]["weather_code"])),
        "temp": round(float(d["current"]["temperature_2m"])),
        "clock": now.strftime("%H:%M"),
        "code": int(d["current"]["weather_code"]),
    }


def build_css(time_of_day, weather, temp, clock, code=None):
    base = (HERE / "fonts" / "fraunces.css").read_text(encoding="utf-8") + "\n" + (HERE / "base.css").read_text(encoding="utf-8")
    block = lambda t: "\n".join(f"    {k}: {v};" for k, v in {**LIGHT_TEXT, **SKINS[t]}.items())
    vars_ = block(time_of_day)
    # The footer script sets html.sky-dawn/-day/-dusk/-night from the reader's clock (Berlin time),
    # so the time of day is always right even if a scheduled run is late. :root is the fallback.
    classes = "\n".join(f"html.sky-{t} {{\n{block(t)}\n}}" for t in SKINS)
    layer = WEATHER[weather]
    if weather == "clear":
        stars = NIGHT_STARS.replace("html::after", "html.sky-night::after")
        if time_of_day == "night":
            stars += NIGHT_STARS.replace("html::after", "html:not(.sky-js)::after")
        layer += stars
    temp_txt = f"{temp}°C".replace("-", "−")
    return (
        f"{base}\n/* ===== sky: {time_of_day}, {weather}, {temp_txt}, set {clock} Berlin time ===== */\n"
        f":root {{\n{vars_}\n}}\n{classes}\n{layer}\n"
        f':root {{ --sky-posts: "{" ".join(quotable_paths())}"; }}\n'
        f'.sky-badge .temp::before {{ content: "{temp_txt}"; }}\n'
        f'.sky-badge .clock:empty::before {{ content: "{clock}"; }}\n'
        + (badge_css(code, time_of_day) if code is not None else "")
    )


# ---------------------------------------------------------------- Bear API

class Bear:
    def __init__(self, subdomain, key, dry_run=False):
        self.root = f"https://bearblog.dev/{subdomain}/api/v1/"
        self.key = key
        self.dry_run = dry_run

    def call(self, method, path, body=None):
        if self.dry_run and method != "GET":
            print(f"[dry run] {method} {path}: {len(json.dumps(body))} bytes")
            return {}
        data = json.dumps(body).encode() if body is not None else None
        for attempt in range(4):
            req = urllib.request.Request(self.root + path, data=data, method=method)
            req.add_header("Authorization", f"Bearer {self.key}")
            # Bear's Cloudflare blocks Python's default "Python-urllib" signature (error 1010)
            req.add_header("User-Agent", USER_AGENT)
            req.add_header("Accept", "application/json")
            if data is not None:
                req.add_header("Content-Type", "application/json")
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    return json.load(r)
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < 3:
                    time.sleep(int(e.headers.get("Retry-After", "10")) + 1)
                    continue
                if e.code >= 500 and attempt < 3:
                    time.sleep(10)
                    continue
                msg = e.read().decode(errors="replace")[:300]
                raise SystemExit(f"Bear API {method} {path} -> {e.code}: {msg}")
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt < 3:
                    time.sleep(10)
                    continue
                raise SystemExit(f"Bear API {method} {path} unreachable: {e}")

    def posts(self):
        page = 1
        while page:
            d = self.call("GET", f"post/?status=published&is_page=false&page={page}")
            yield from d.get("posts", [])
            page = d.get("next_page")
            time.sleep(1)


# ---------------------------------------------------------------- quotes

MD_CLEAN = [
    (re.compile(r"```.*?```", re.S), " "),
    (re.compile(r"\$\$.*?\$\$", re.S), " "),
    (re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I), " "),
    (re.compile(r"<br\s*/?>", re.I), "\n"),
    (re.compile(r"</(p|div|li|h\d|blockquote)>", re.I), "\n"),
    (re.compile(r"<[^>]+>"), ""),
    (re.compile(r"!\[[^\]]*\]\([^)]*\)"), ""),
    (re.compile(r"\[([^\]]*)\]\([^)]*\)"), r"\1"),
    (re.compile(r"\{\{[^}]*\}\}"), ""),
    (re.compile(r"https?://\S+"), ""),
    (re.compile(r"^\s{0,3}(#{1,6}|>+|[-*+]|\d+[.)])\s+", re.M), ""),
    (re.compile(r"(\*\*|__|\*|_|`|~~)"), ""),
]


def candidates(content):
    text = html.unescape(content or "")
    for rx, rep in MD_CLEAN:
        text = rx.sub(rep, text)
    lines = [re.sub(r"\s+", " ", l).strip() for l in text.splitlines()]
    lines = [l for l in lines if l and not re.fullmatch(r"[-*_=~. ]+", l)]
    if not lines:
        return []
    short = sum(len(l) < 80 for l in lines)
    if short / len(lines) >= 0.7:  # poem-like: one line at a time
        pieces = lines
    else:  # prose: sentences
        pieces = []
        for l in lines:
            pieces += re.split(r"(?<=[.!?…])\s+", l)
    out = []
    for p in pieces:
        p = p.strip(" -–—\"'“”")
        if 12 <= len(p) <= 160 and len(p.split()) >= 3:
            out.append(p)
    return out


BLOCK_RX = re.compile(r'<div class="sky-quote">.*?</ul></div>', re.S)  # matches old and new block


# ---------------------------------------------------------------- jobs

def job_sky(bear):
    w = berlin_weather()
    print(f"Berlin {w['clock']}: {w['time']}, {w['weather']} (code {w['code']}), {w['temp']}°C")
    css = build_css(w["time"], w["weather"], w["temp"], w["clock"], w["code"])
    current = bear.call("GET", "blog/").get("custom_styles", "")
    # the clock fallback changes every run; only write when something else changed
    strip = lambda s: re.sub(r"set \d\d:\d\d Berlin time|content: \"\d\d:\d\d\"", "", s or "")
    if strip(current) == strip(css):
        print("Sky unchanged, nothing sent.")
        return
    bear.call("PATCH", "blog/", {"custom_styles": css})
    print("Sky updated.")


def has_tag(tags, tag):
    return any((t or "").strip().lower() == tag for t in (tags or []))


def job_tag_all(bear):
    tagged = skipped = already = 0
    for p in bear.posts():
        title = (p.get("title") or "").strip()
        if any(title.lower().startswith(x.lower()) for x in EXCLUDE_TITLE_PREFIXES):
            print(f"  skip   {title}")
            skipped += 1
            continue
        full = bear.call("GET", f"post/{p['uid']}/")
        time.sleep(1.1)
        tags = full.get("tags") or []
        if has_tag(tags, QUOTE_TAG):
            already += 1
            continue
        bear.call("PATCH", f"post/{p['uid']}/", {"tags": list(tags) + [QUOTE_TAG]})
        time.sleep(1.1)
        print(f"  tagged {title}")
        tagged += 1
    print(f"Done: {tagged} tagged, {already} already had the tag, {skipped} skipped.")


QUOTABLE_FILE = HERE / "quotable.txt"


def quotable_paths():
    if not QUOTABLE_FILE.exists():
        return []
    return [l.strip() for l in QUOTABLE_FILE.read_text(encoding="utf-8").splitlines() if l.strip().startswith("/")]


def job_quotes(bear):
    """Daily: save the addresses of posts tagged "quotable" (into the theme, not the home page)."""
    paths = []
    for p in bear.posts():
        tags = p.get("tags") if "tags" in p else None
        if tags is None:
            tags = bear.call("GET", f"post/{p['uid']}/").get("tags")
            time.sleep(1.1)
        if has_tag(tags, QUOTE_TAG) and p.get("url"):
            paths.append(urllib.parse.urlparse(p["url"]).path or "/")
    paths = sorted(set(paths))
    QUOTABLE_FILE.write_text("\n".join(paths) + "\n", encoding="utf-8")
    print(f'Quotable posts: {len(paths)}')
    # remove the old quote block from the home page, leaving the description as it was
    home = bear.call("GET", "blog/").get("content", "") or ""
    clean = BLOCK_RX.sub("", home).rstrip() + "\n"
    if clean.strip() != home.strip():
        bear.call("PATCH", "blog/", {"content": clean})
        print("Home page cleaned: only your own text is left.")
    job_sky(bear)


def main():
    args = sys.argv[1:]
    dry = "--dry-run" in args
    mode = next((a for a in args if not a.startswith("--")), "sky")
    key = os.environ.get("BEAR_API_KEY", "")
    sub = os.environ.get("BEAR_SUBDOMAIN", "")
    if not key or not sub:
        raise SystemExit("BEAR_API_KEY and BEAR_SUBDOMAIN must be set.")
    bear = Bear(sub, key, dry_run=dry)
    {"sky": job_sky, "quotes": job_quotes, "tag-all": job_tag_all}[mode](bear)


if __name__ == "__main__":
    main()
