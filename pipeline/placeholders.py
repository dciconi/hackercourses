"""Draw one placeholder illustration per topic -> site/img/topics/<slug>.svg

Used for courses without a usable preview image. Original line art, no text, 16:9.
"""

import re
from html import escape

from classify import OTHER, ROOT, TOPICS

OUT = ROOT / "site" / "img" / "topics"
OG = ROOT / "site" / "img" / "og"  # PNG social cards: topic art + one for the site
INK = "#f6efe2"
ACCENT = "#ff7a1f"
W, H = 640, 360


def slug(topic):
    return re.sub(r"[^a-z0-9]+", "-", topic.lower().replace("&", "and")).strip("-")


def line(x1, y1, x2, y2, color=INK, w=6):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{w}" stroke-linecap="round"/>'


def circle(cx, cy, r, fill="none", stroke=INK, w=6):
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{w}"/>'


def path(d, stroke=INK, w=6, fill="none"):
    return (f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{w}" '
            'stroke-linecap="round" stroke-linejoin="round"/>')


def rect(x, y, w, h, r=10, fill="none", stroke=INK, sw=6):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


def neural():
    layers = [[(220, y) for y in (110, 180, 250)], [(320, y) for y in (80, 145, 215, 280)], [(420, y) for y in (145, 215)]]
    edges = [line(a[0], a[1], b[0], b[1], w=3) for l1, l2 in zip(layers, layers[1:]) for a in l1 for b in l2]
    nodes = [circle(x, y, 17, fill="#00000055") for layer in layers for x, y in layer]
    return "".join(edges + nodes) + circle(320, 145, 17, fill=ACCENT, stroke=ACCENT)


def tree():
    pts = {"r": (320, 85), "a": (235, 170), "b": (405, 170), "c": (190, 260), "d": (280, 260), "e": (360, 260), "f": (450, 260)}
    edges = [("r", "a"), ("r", "b"), ("a", "c"), ("a", "d"), ("b", "e"), ("b", "f")]
    hot = {("r", "b"), ("b", "e")}
    out = [line(*pts[p], *pts[q], color=ACCENT if (p, q) in hot else INK) for p, q in edges]
    out += [circle(x, y, 20, fill=ACCENT if k in "rbe" else "#00000055", stroke=ACCENT if k in "rbe" else INK)
            for k, (x, y) in pts.items()]
    return "".join(out)


def chip():
    out = [rect(245, 105, 150, 150, r=14)]
    for i in range(4):  # four pins per side
        x, y = 266 + i * 36, 126 + i * 36
        out += [line(x, 105, x, 72), line(x, 255, x, 288), line(245, y, 212, y), line(395, y, 428, y)]
    out.append(rect(285, 145, 70, 70, r=8, fill=ACCENT, stroke=ACCENT))
    return "".join(out)


def plot():
    curve = "M170 230 C 215 120, 255 120, 300 180 S 385 250, 430 140 S 470 100, 480 105"
    return (line(160, 290, 490, 290) + line(170, 300, 170, 70) + path(curve)
            + line(340, 250, 470, 140, color=ACCENT, w=5) + circle(404, 196, 11, fill=ACCENT, stroke=ACCENT))


def code():
    return (path("M260 110 L190 180 L260 250") + path("M380 110 L450 180 L380 250")
            + line(345, 95, 295, 265, color=ACCENT, w=8))


def web():
    return (rect(170, 85, 260, 180, r=14) + line(170, 125, 430, 125)
            + "".join(circle(195 + i * 22, 105, 5, fill=INK, stroke=INK, w=2) for i in range(3))
            + line(200, 160, 330, 160, w=5) + line(200, 190, 300, 190, w=5)
            + rect(380, 150, 90, 150, r=14, fill="#00000088") + rect(395, 172, 60, 90, r=6, fill=ACCENT, stroke=ACCENT)
            + line(410, 282, 440, 282, w=4))


def database():
    top = '<ellipse cx="320" cy="100" rx="110" ry="30" fill="{f}" stroke="{s}" stroke-width="6"/>'
    return (top.format(f=ACCENT, s=ACCENT) + line(210, 100, 210, 260) + line(430, 100, 430, 260)
            + path("M210 153 A110 30 0 0 0 430 153") + path("M210 206 A110 30 0 0 0 430 206")
            + path("M210 260 A110 30 0 0 0 430 260"))


def lock():
    return (path("M265 165 V125 A55 55 0 0 1 375 125 V165") + rect(235, 165, 170, 130, r=16)
            + circle(320, 220, 16, fill=ACCENT, stroke=ACCENT) + line(320, 230, 320, 262, color=ACCENT, w=12))


def atom():
    orbit = '<ellipse cx="320" cy="180" rx="150" ry="52" fill="none" stroke="{c}" stroke-width="5" transform="rotate({a} 320 180)"/>'
    return ("".join(orbit.format(c=INK, a=a) for a in (0, 60, 120)) + circle(320, 180, 22, fill=ACCENT, stroke=ACCENT)
            + circle(470, 180, 9, fill=INK, stroke=INK))


def chart():
    bars = "".join(rect(200 + i * 62, 270 - h, 40, h, r=6, fill="#00000055") for i, h in enumerate((60, 95, 130, 170)))
    return (line(170, 280, 480, 280) + bars + path("M190 230 L280 200 L350 170 L455 95", stroke=ACCENT)
            + path("M425 92 L458 93 L453 125", stroke=ACCENT))


def bezier():
    return (path("M170 260 C 230 80, 410 80, 470 260") + line(170, 260, 230, 80, w=3) + line(470, 260, 410, 80, w=3)
            + rect(220, 70, 20, 20, r=3, fill=INK, stroke=INK, sw=2) + rect(400, 70, 20, 20, r=3, fill=INK, stroke=INK, sw=2)
            + circle(170, 260, 12, fill=ACCENT, stroke=ACCENT) + circle(470, 260, 12, fill=ACCENT, stroke=ACCENT)
            + circle(320, 125, 9, fill=ACCENT, stroke=ACCENT))


def book():
    return (path("M320 110 C 280 90, 220 88, 175 100 V 270 C 220 258, 280 260, 320 280 Z")
            + path("M320 110 C 360 90, 420 88, 465 100 V 270 C 420 258, 360 260, 320 280 Z")
            + "".join(line(200, 140 + i * 30, 295, 145 + i * 30, w=4) for i in range(4))
            + "".join(line(345, 145 + i * 30, 440, 140 + i * 30, w=4) for i in range(3))
            + path("M405 92 V 150 L420 138 L435 150 V 90", stroke=ACCENT, fill=ACCENT, w=4))


def bulb():
    return (path("M285 230 C 285 200, 255 185, 255 145 A65 65 0 0 1 385 145 C 385 185, 355 200, 355 230 Z")
            + line(290, 255, 350, 255) + line(298, 280, 342, 280)
            + "".join(line(320 + 110 * dx, 145 + 110 * dy, 320 + 135 * dx, 145 + 135 * dy, color=ACCENT)
                      for dx, dy in ((-1, 0), (1, 0), (-0.7, -0.7), (0.7, -0.7), (0, -1)))
            + path("M300 205 L320 175 L340 205", stroke=ACCENT, w=5))


MOTIFS = {
    "Machine Learning & AI": (neural, "#2b2350", "#3f3070"),
    "Algorithms & Data Structures": (tree, "#123a3a", "#1d5656"),
    "CS Fundamentals & Systems": (chip, "#1f2a38", "#2e4157"),
    "Mathematics": (plot, "#3a2414", "#5a391f"),
    "Programming Languages": (code, "#1d3324", "#2b4d35"),
    "Web & Mobile Development": (web, "#13304a", "#1d486d"),
    "Databases & Data Engineering": (database, "#33203a", "#4d3058"),
    "Security & Cryptography": (lock, "#2a1a1a", "#4a2a2c"),
    "Science & Engineering": (atom, "#102d40", "#184864"),
    "Business, Finance & Economics": (chart, "#2f2d14", "#4b4721"),
    "Design & Creative": (bezier, "#3d1d30", "#5d2d4a"),
    "Humanities & Social Science": (book, "#34281c", "#503d29"),
    OTHER: (bulb, "#262626", "#3d3d3d"),
}


def svg(topic):
    draw, c1, c2 = MOTIFS[topic]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="{escape(topic)}">
<defs>
<linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></linearGradient>
<pattern id="d" width="24" height="24" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.6" fill="{INK}" opacity=".12"/></pattern>
</defs>
<rect width="{W}" height="{H}" fill="url(#g)"/><rect width="{W}" height="{H}" fill="url(#d)"/>
{draw()}
</svg>
"""


SITE_CARD = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630">
<defs><pattern id="d" width="28" height="28" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.8" fill="{INK}" opacity=".10"/></pattern></defs>
<rect width="1200" height="630" fill="#1b1a15"/><rect width="1200" height="630" fill="url(#d)"/>
<rect x="96" y="150" width="120" height="120" rx="26" fill="{ACCENT}"/>
<path d="M130 188h52M130 210h38M130 232h22" stroke="#fff" stroke-width="11" stroke-linecap="round"/>
<text x="246" y="240" font-family="Segoe UI, Arial, sans-serif" font-size="92" font-weight="700" fill="{INK}">Hacker Courses</text>
<text x="100" y="380" font-family="Segoe UI, Arial, sans-serif" font-size="46" fill="{INK}" opacity=".85">The online courses programmers keep recommending,</text>
<text x="100" y="442" font-family="Segoe UI, Arial, sans-serif" font-size="46" fill="{INK}" opacity=".85">ranked from public comments since 2006.</text>
<rect x="100" y="510" width="210" height="8" rx="4" fill="{ACCENT}"/>
</svg>"""


def png(svg_text, width, height):
    """Rasterize for social previews, which don't accept SVG."""
    import resvg_py
    return bytes(resvg_py.svg_to_bytes(svg_string=svg_text, width=width, height=height))


def main():
    names = [name for name, _ in TOPICS] + [OTHER]
    assert set(names) == set(MOTIFS), "every topic needs a motif"
    OUT.mkdir(parents=True, exist_ok=True)
    OG.mkdir(parents=True, exist_ok=True)
    for topic in names:
        art = svg(topic)
        (OUT / f"{slug(topic)}.svg").write_text(art, encoding="utf-8")
        (OG / f"{slug(topic)}.png").write_bytes(png(art, 1200, 675))
    (OG / "site.png").write_bytes(png(SITE_CARD, 1200, 630))
    print(f"wrote {len(names)} placeholders to {OUT} and social cards to {OG}")


if __name__ == "__main__":
    main()
