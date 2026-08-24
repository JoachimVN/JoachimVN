# -*- coding: utf-8 -*-
"""Draw every SVG in the profile README.

The design is a scoreboard, because that is what the work is: dart scores with
checkout math, a music popularity index, a stock trading game, a board game
running tournaments between sixteen AI strategies. The name is set on a flip dot
board and the figures are seven segment digits, both drawn from geometry rather
than type, so nothing depends on a font the viewer may not have. GitHub serves
these through an image proxy that blocks webfonts, so drawn glyphs are also the
only way to keep the lettering identical everywhere.

Colours are not invented here. The board, cream and gold are the same tokens
joavn.dev uses (--bg, --text, --accent), and the language mix uses the LANG_COLORS
map from Portfolio/script.js, so the profile and the site read as one thing.

Every board is drawn at two widths. A 1000px board shown in a 390px phone column
renders at 36%, which turns 11px labels into 4px and makes the rails, the stack
rows and the legend unreadable. So there is a second 400px layout that reflows
rather than shrinks: the name breaks over three lines, the scoreboard becomes two
by two, and the stack puts its items under their label. The README chooses between
them with a width media query on <source>, which GitHub's sanitiser keeps.

No dependencies and no network access: the numbers come from assets/stats.json,
which scripts/fetch_stats.py refreshes. Run `python scripts/generate.py` after
changing anything here.

Animation note: every reveal begins at 0s with the element's base attribute
already set to its final value, so a renderer that snapshots frame zero, or
ignores SMIL entirely, still shows the finished board rather than a blank one.
"""
import datetime
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets")

MONO = "ui-monospace,'SF Mono','Cascadia Mono','DejaVu Sans Mono',Consolas,monospace"

# joavn.dev's own tokens: --bg #09090E, --text #F2EFE6, --accent #C9952A.
# Light mode swaps the board and the chalk, and darkens the accents to hold up
# against cream.
DARK = dict(bg="#09090E", fg="#F2EFE6", dim="#89836F", rule="#26252E",
            unlit="0.09", grain="0.05",
            accents=["#C9952A", "#3572A5", "#E34C26", "#00ADD8"])
LIGHT = dict(bg="#F2EFE6", fg="#09090E", dim="#6B6759", rule="#DCD7C7",
             unlit="0.13", grain="0.03",
             accents=["#966E17", "#2A5A85", "#B93A18", "#0083A3"])

# Copied from Portfolio/script.js so a language is the same colour in both places.
LANG_COLORS = {
    "JavaScript": "#f1e05a", "TypeScript": "#2b7489", "Python": "#3572A5",
    "C#": "#178600", "C++": "#f34b7d", "C": "#555555", "HTML": "#e34c26",
    "CSS": "#563d7c", "Rust": "#dea584", "Go": "#00ADD8", "Java": "#b07219",
    "GDScript": "#355570", "Lua": "#000080", "Other": "#888888",
}

# Two layouts, not one layout scaled. Type sizes in the narrow one are chosen so
# that a 400px board in a roughly 390px column renders at close to 1:1.
WIDE = dict(
    w=1000, pad=44, eb_fs=11, eb_ls=2.2, item_fs=13,
    name_lines=["JOACHIM", "VALDERSNES NILSEN"], pitch=8.6, dot=2.7,
    dw=26.0, dh=46.0, dt=5.0, gap=8, score_cols=4, legend_cols=3,
    items_below=False, items_x=200,
)
NARROW = dict(
    w=400, pad=18, eb_fs=10, eb_ls=0.8, item_fs=10.5,
    name_lines=["JOACHIM", "VALDERSNES", "NILSEN"], pitch=6.0, dot=1.85,
    dw=17.0, dh=30.0, dt=3.4, gap=5, score_cols=2, legend_cols=2,
    items_below=True, items_x=18,
)


def is_wide(L):
    return L["w"] > 600


def mono_w(text, fs, ls=0.0):
    return len(text) * (fs * 0.6 + ls)


def reveal(delay, fade=0.7, attr="opacity", a="0", b="1"):
    """A delayed reveal that begins at 0s. The caller sets the element's base
    attribute to the final value, so frame zero and no SMIL both look finished."""
    total = delay + fade
    return ('<animate attributeName="%s" values="%s;%s;%s" keyTimes="0;%.4f;1" '
            'dur="%.2fs" begin="0s" fill="freeze"/>' % (attr, a, a, b, delay / total, total))


def panel(p, L, h, body, label, extra_defs=""):
    """A board: flat rectangle, hairline inner frame, and a little surface grain."""
    w = L["w"]
    inset = 12.5 if is_wide(L) else 7.5
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h:.0f}" width="{w}" height="{h:.0f}" role="img" aria-label="{label}">
  <defs>
    <filter id="grain" x="0" y="0" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="3" stitchTiles="stitch"/>
      <feColorMatrix type="saturate" values="0"/>
    </filter>{extra_defs}
  </defs>
  <rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1:.0f}" fill="{p['bg']}" stroke="{p['rule']}"/>
  <rect x="{inset}" y="{inset}" width="{w - inset * 2}" height="{h - inset * 2:.0f}" fill="none" stroke="{p['rule']}" opacity="0.7"/>
  <rect x="1" y="1" width="{w - 2}" height="{h - 2:.0f}" filter="url(#grain)" opacity="{p['grain']}" style="mix-blend-mode:overlay"/>
{body}
</svg>
'''


def rail(p, L, y, left, right="", right_fill=None):
    """One line of small tracked type, left aligned and optionally right aligned."""
    out = ['<text x="%d" y="%.1f" font-family="%s" font-size="%s" letter-spacing="%s" fill="%s">%s</text>'
           % (L["pad"], y, MONO, L["eb_fs"], L["eb_ls"], p["dim"], left)]
    if right:
        out.append('<text x="%d" y="%.1f" text-anchor="end" font-family="%s" font-size="%s" '
                   'letter-spacing="%s" fill="%s">%s</text>'
                   % (L["w"] - L["pad"], y, MONO, L["eb_fs"], L["eb_ls"],
                      right_fill or p["fg"], right))
    return "".join(out)


def tick(colour, L, y):
    return '<rect x="%d" y="%.1f" width="%d" height="2" fill="%s"/>' % (
        L["pad"], y, 30 if is_wide(L) else 22, colour)


def hrule(p, L, y):
    return '<rect x="%d" y="%.1f" width="%d" height="1" fill="%s"/>' % (
        L["pad"], y, L["w"] - L["pad"] * 2, p["rule"])


# --------------------------------------------------------------- flip dot type
# 5x7 cells per glyph, the resolution a real dot matrix board uses.
GLYPHS = {
    "A": ".###.|#...#|#...#|#####|#...#|#...#|#...#",
    "B": "####.|#...#|#...#|####.|#...#|#...#|####.",
    "C": ".###.|#...#|#....|#....|#....|#...#|.###.",
    "D": "####.|#...#|#...#|#...#|#...#|#...#|####.",
    "E": "#####|#....|#....|####.|#....|#....|#####",
    "F": "#####|#....|#....|####.|#....|#....|#....",
    "G": ".###.|#...#|#....|#.###|#...#|#...#|.###.",
    "H": "#...#|#...#|#...#|#####|#...#|#...#|#...#",
    "I": "#####|..#..|..#..|..#..|..#..|..#..|#####",
    "J": "..###|...#.|...#.|...#.|...#.|#..#.|.##..",
    "K": "#...#|#..#.|#.#..|##...|#.#..|#..#.|#...#",
    "L": "#....|#....|#....|#....|#....|#....|#####",
    "M": "#...#|##.##|#.#.#|#.#.#|#...#|#...#|#...#",
    "N": "#...#|##..#|#.#.#|#..##|#...#|#...#|#...#",
    "O": ".###.|#...#|#...#|#...#|#...#|#...#|.###.",
    "P": "####.|#...#|#...#|####.|#....|#....|#....",
    "Q": ".###.|#...#|#...#|#...#|#.#.#|#..#.|.##.#",
    "R": "####.|#...#|#...#|####.|#.#..|#..#.|#...#",
    "S": ".####|#....|#....|.###.|....#|....#|####.",
    "T": "#####|..#..|..#..|..#..|..#..|..#..|..#..",
    "U": "#...#|#...#|#...#|#...#|#...#|#...#|.###.",
    "V": "#...#|#...#|#...#|#...#|#...#|.#.#.|..#..",
    "W": "#...#|#...#|#...#|#.#.#|#.#.#|##.##|#...#",
    "X": "#...#|#...#|.#.#.|..#..|.#.#.|#...#|#...#",
    "Y": "#...#|#...#|.#.#.|..#..|..#..|..#..|..#..",
    "Z": "#####|....#|...#.|..#..|.#...|#....|#####",
    " ": ".....|.....|.....|.....|.....|.....|.....",
}
COLS, ROWS = 5, 7


def lit_dots(L, y0, line_gap):
    dots, pitch, pad = [], L["pitch"], L["pad"]
    for row_index, line in enumerate(L["name_lines"]):
        top = y0 + row_index * (ROWS * pitch + line_gap)
        for char_index, char in enumerate(line):
            grid = GLYPHS.get(char, GLYPHS[" "]).split("|")
            for r, cells in enumerate(grid):
                for c, cell in enumerate(cells):
                    if cell == "#":
                        dots.append((pad + (char_index * (COLS + 1) + c) * pitch,
                                     top + r * pitch))
    return dots


# ------------------------------------------------------------------- banner
# NTNU's Bachelor of Engineering in Computer Science (BIDATA), started August 2025.
PROGRAMME = "COMPUTER SCIENCE ENGINEERING"
STUDY_START = 2025
STUDY_YEARS = 3
STUDY_END = datetime.date(2028, 6, 1)            # graduates that spring

LOCATION = "TRONDHEIM, NORWAY"
AVAILABILITY = "OPEN TO INTERNSHIPS"
SITE = "JOAVN.DEV"


def study_year(today=None):
    """Which year of the bachelor is running, counting from the August rollover.
    Returns None from graduation onwards, so the board stops claiming it."""
    today = today or datetime.date.today()
    if today >= STUDY_END:
        return None
    year = today.year - STUDY_START + (1 if today.month >= 8 else 0)
    return year if 1 <= year <= STUDY_YEARS else None


def year_label():
    year = study_year()
    return "YEAR %d OF %d" % (year, STUDY_YEARS) if year else ""


def banner(p, L):
    gold, cyan = p["accents"][0], p["accents"][3]
    pitch, dot, wide = L["pitch"], L["dot"], is_wide(L)
    line_gap = 16 if wide else 10
    top_y, board_y = (48, 96) if wide else (28, 58)

    lines = L["name_lines"]
    board_h = len(lines) * ROWS * pitch + (len(lines) - 1) * line_gap - (pitch - dot * 2)
    board_w = L["w"] - L["pad"] * 2
    lit = "".join('<use href="#d" x="%.1f" y="%.1f"/>' % (x, y)
                  for x, y in lit_dots(L, board_y, line_gap))

    if wide:
        programme = " &#183; ".join(x for x in ["NTNU", PROGRAMME, year_label()] if x)
        top = rail(p, L, top_y, programme, SITE)
        rule_top, rule_bottom, h = 62, 248, 300
        rails = rail(p, L, 274, LOCATION, AVAILABILITY, cyan)
    else:
        # Three rail lines instead of two, so nothing has to be abbreviated.
        rule_top = top_y + 14
        rule_bottom = board_y + board_h + 16
        top = rail(p, L, top_y, "NTNU &#183; " + PROGRAMME, year_label())
        rails = (rail(p, L, rule_bottom + 20, LOCATION, SITE)
                 + rail(p, L, rule_bottom + 38, AVAILABILITY, "", cyan))
        h = rule_bottom + 54

    defs = f'''
    <circle id="d" r="{dot}"/>
    <pattern id="unlit" width="{pitch}" height="{pitch}" patternUnits="userSpaceOnUse" x="{L['pad']}" y="{board_y}">
      <circle cx="0" cy="0" r="{dot}" fill="{gold}" opacity="{p['unlit']}"/>
    </pattern>
    <clipPath id="sweep">
      <rect x="{L['pad'] - dot}" y="{board_y - dot}" width="{board_w}" height="{board_h}">
        {reveal(0.1, 1.3, "width", "0", str(board_w))}
      </rect>
    </clipPath>'''
    body = f'''  {top}
  {hrule(p, L, rule_top)}
  <rect x="{L['pad'] - dot}" y="{board_y - dot}" width="{board_w}" height="{board_h}" fill="url(#unlit)"/>
  <g clip-path="url(#sweep)" fill="{gold}">{lit}</g>
  {hrule(p, L, rule_bottom)}
  {rails}'''
    year = study_year()
    where = "NTNU, Trondheim" + (", year %d of %d" % (year, STUDY_YEARS) if year else "")
    return panel(p, L, h, body, "Joachim Valdersnes Nilsen. Computer science engineering at %s. "
                                "Open to internships. joavn.dev" % where, defs)


# -------------------------------------------------------------- seven segment
SEGMENTS = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc",
            "5": "afgcd", "6": "afgecd", "7": "abc", "8": "abcdefg", "9": "abcdfg"}


def _bar(x, y, length, thickness, vertical):
    t = thickness / 2
    if vertical:
        pts = [(x, y), (x + t, y + t), (x + t, y + length - t),
               (x, y + length), (x - t, y + length - t), (x - t, y + t)]
    else:
        pts = [(x, y), (x + t, y - t), (x + length - t, y - t),
               (x + length, y), (x + length - t, y + t), (x + t, y + t)]
    return " ".join("%.1f,%.1f" % pt for pt in pts)


def digit(char, x, y, p, L, colour):
    dw, dh, dt = L["dw"], L["dh"], L["dt"]
    half = dh / 2
    shapes = {
        "a": _bar(x, y, dw, dt, False), "g": _bar(x, y + half, dw, dt, False),
        "d": _bar(x, y + dh, dw, dt, False), "f": _bar(x, y, half, dt, True),
        "b": _bar(x + dw, y, half, dt, True), "e": _bar(x, y + half, half, dt, True),
        "c": _bar(x + dw, y + half, half, dt, True),
    }
    on = SEGMENTS.get(char, "")
    out = []
    for name, points in shapes.items():
        if name in on:
            out.append('<polygon points="%s" fill="%s"/>' % (points, colour))
        else:
            # Unlit segments are what make it read as a display rather than a number.
            out.append('<polygon points="%s" fill="%s" opacity="%s">%s</polygon>'
                       % (points, colour, p["unlit"],
                          reveal(0, 0.9, "opacity", "0.45", p["unlit"])))
    return "".join(out)


def number(value, cx, y, p, L, colour):
    text = str(value)
    dw, gap = L["dw"], L["gap"]
    x = cx - (len(text) * dw + (len(text) - 1) * gap) / 2
    return "".join(digit(c, x + i * (dw + gap), y, p, L, colour) for i, c in enumerate(text))


def scoreboard(p, L, d):
    cells = [("COMMITS", d["commits"]), ("PULL REQUESTS", d["prs"]),
             ("REPOSITORIES", d["repos"]), ("ISSUES OPENED", d["issues"])]
    wide = is_wide(L)
    cols = L["score_cols"]
    inner = L["w"] - L["pad"] * 2
    cw = inner / cols
    top_y = 48 if wide else 28
    rule_y = 70 if wide else 42
    row_h = L["dh"] + (30 if wide else 34)
    label_fs = 10.5 if wide else 9.5
    parts = []
    for i, (label, value) in enumerate(cells):
        colour = p["accents"][i]
        col, row = i % cols, i // cols
        cx = L["pad"] + cw * col + cw / 2
        label_y = rule_y + 34 + row * row_h
        if col:
            parts.append('<rect x="%.1f" y="%.1f" width="1" height="%.0f" fill="%s"/>'
                         % (L["pad"] + cw * col, label_y - 18, row_h - 16, p["rule"]))
        parts.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="%s" font-size="%s" '
                     'letter-spacing="1.6" fill="%s">%s</text>'
                     % (cx, label_y, MONO, label_fs, colour, label))
        parts.append(number(value, cx, label_y + 14, p, L, colour))
    rows = (len(cells) + cols - 1) // cols
    h = rule_y + 34 + (rows - 1) * row_h + L["dh"] + 32
    body = f'''  {rail(p, L, top_y, "SCOREBOARD")}
  {tick(p['accents'][0], L, top_y + 8)}
  {hrule(p, L, rule_y)}
{chr(10).join("  " + s for s in parts)}'''
    return panel(p, L, h, body, "Scoreboard: %s commits, %s pull requests, %s repositories, "
                                "%s issues opened" % (d["commits"], d["prs"], d["repos"], d["issues"]))


# --------------------------------------------------------------- language mix
def langs(p, L, d):
    wide = is_wide(L)
    mix = list(d["languages"].items())
    total = sum(v for _, v in mix) or 1
    shares = [(name, size / total) for name, size in mix]
    inner = L["w"] - L["pad"] * 2
    top_y = 48 if wide else 28
    rule_y = 70 if wide else 42
    bar_y = 86 if wide else 56
    bar_h = 18 if wide else 14

    bar, x = [], float(L["pad"])
    for name, share in shares:
        w = inner * share
        bar.append('<rect x="%.2f" y="%d" width="%.2f" height="%d" fill="%s"/>'
                   % (x, bar_y, max(w - 2, 1), bar_h, LANG_COLORS.get(name, "#888888")))
        x += w

    cols = L["legend_cols"]
    colw = inner / cols
    row_h = 26 if wide else 22
    first = bar_y + (40 if wide else 32)
    legend = []
    for i, (name, share) in enumerate(shares):
        lx = L["pad"] + colw * (i % cols)
        ly = first + (i // cols) * row_h
        colour = LANG_COLORS.get(name, "#888888")
        legend.append('<rect x="%.1f" y="%.1f" width="8" height="8" fill="%s"/>' % (lx, ly - 8, colour))
        legend.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="%s" fill="%s">%s</text>'
                      % (lx + 14, ly, MONO, L["item_fs"], p["fg"], name))
        legend.append('<text x="%.1f" y="%.1f" text-anchor="end" font-family="%s" font-size="%s" '
                      'fill="%s">%.1f%%</text>'
                      % (lx + colw - (30 if wide else 10), ly, MONO, L["item_fs"], p["dim"], share * 100))
    rows = (len(shares) + cols - 1) // cols
    h = first + (rows - 1) * row_h + 26
    defs = f'''
    <clipPath id="wipe"><rect x="{L['pad']}" y="{bar_y}" width="{inner}" height="{bar_h}">
      {reveal(0.15, 1.0, "width", "0", str(inner))}
    </rect></clipPath>'''
    body = f'''  {rail(p, L, top_y, "LANGUAGE MIX")}
  {tick(p['accents'][3], L, top_y + 8)}
  {hrule(p, L, rule_y)}
  <g clip-path="url(#wipe)">{"".join(bar)}</g>
{chr(10).join("  " + s for s in legend)}'''
    return panel(p, L, h, body, "Language mix: " + ", ".join("%s %.1f percent" % (n, s * 100)
                                                             for n, s in shares), defs)


# ----------------------------------------------------------------- the stack
STACK = [("LANGUAGES", ["TypeScript", "Java", "JavaScript", "Python", "C#", "SQL"]),
         ("FRONTEND", ["React", "Vite", "Tailwind", "JavaFX", "PWA"]),
         ("BACKEND", ["Node", "Express", "Socket.IO", "PostgreSQL", "Drizzle", "Zod"]),
         ("TOOLING", ["Git", "Vitest", "Playwright", "Actions", "Railway", "Tailscale"])]
SEP = "  &#183;  "


def wrap_items(items, fs, limit):
    """Greedy wrap on the separator, measured rather than guessed."""
    sep_w = mono_w("     ", fs)                  # the separator is five characters wide
    lines, line, width = [], [], 0.0
    for item in items:
        item_w = mono_w(item, fs)
        extra = (sep_w if line else 0) + item_w
        if line and width + extra > limit:
            lines.append(line)
            line, width = [item], item_w
        else:
            line.append(item)
            width += extra
    if line:
        lines.append(line)
    return lines


def stack(p, L):
    wide = is_wide(L)
    top_y = 48 if wide else 28
    rule_y = 70 if wide else 42
    inner = L["w"] - L["pad"] * 2
    rows, y = [], rule_y + (34 if wide else 22)
    for i, (label, items) in enumerate(STACK):
        colour = p["accents"][i]
        rows.append('<rect x="%d" y="%.1f" width="7" height="7" fill="%s"/>' % (L["pad"], y - 7, colour))
        rows.append('<text x="%d" y="%.1f" font-family="%s" font-size="%s" letter-spacing="%s" fill="%s">%s</text>'
                    % (L["pad"] + 17, y, MONO, L["eb_fs"], L["eb_ls"], colour, label))
        if L["items_below"]:
            y += 17
            limit, x = inner, L["items_x"]
        else:
            limit, x = L["w"] - L["pad"] - L["items_x"], L["items_x"]
        for line in wrap_items(items, L["item_fs"], limit):
            spans = ('<tspan fill="%s">%s</tspan>' % (p["dim"], SEP)).join(line)
            rows.append('<text x="%d" y="%.1f" font-family="%s" font-size="%s" fill="%s">%s</text>'
                        % (x, y, MONO, L["item_fs"], p["fg"], spans))
            y += 17
        y += (17 if wide else 13)
    h = y + (2 if wide else 4)
    body = f'''  {rail(p, L, top_y, "STACK")}
  {tick(p['accents'][1], L, top_y + 8)}
  {hrule(p, L, rule_y)}
{chr(10).join("  " + r for r in rows)}'''
    label = "; ".join("%s: %s" % (name, ", ".join(items)) for name, items in STACK)
    return panel(p, L, h, body, label)


# --------------------------------------------------------------- link plates
def plate(label, accent):
    h, size = 40, 12
    w = mono_w(label, size, 1.8) + 44
    p = DARK
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h}" width="{w:.0f}" height="{h}" role="img" aria-label="{label}">
  <rect x="0.5" y="0.5" width="{w - 1:.1f}" height="{h - 1}" fill="{p['bg']}" stroke="{accent}" stroke-opacity="0.7"/>
  <rect x="10" y="{h / 2 - 4}" width="8" height="8" fill="{accent}"/>
  <text x="28" y="{h / 2 + 4.5}" font-family="{MONO}" font-size="{size}" letter-spacing="1.8" fill="{p['fg']}">{label}</text>
</svg>
'''


def main():
    with open(os.path.join(OUT, "stats.json"), encoding="utf-8") as f:
        d = json.load(f)

    files = {}
    for theme, p in (("dark", DARK), ("light", LIGHT)):
        for size, L in (("", WIDE), ("-narrow", NARROW)):
            files["banner%s-%s.svg" % (size, theme)] = banner(p, L)
            files["stack%s-%s.svg" % (size, theme)] = stack(p, L)
            files["scoreboard%s-%s.svg" % (size, theme)] = scoreboard(p, L, d)
            files["langs%s-%s.svg" % (size, theme)] = langs(p, L, d)
    files["plate-portfolio.svg"] = plate("JOAVN.DEV", DARK["accents"][0])
    files["plate-linkedin.svg"] = plate("LINKEDIN", "#0A66C2")
    files["plate-email.svg"] = plate("EMAIL", DARK["accents"][2])

    for name in sorted(files):
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(files[name])
        print("wrote %-28s %6d bytes" % (name, len(files[name])))


if __name__ == "__main__":
    main()
