#!/usr/bin/env python3
"""Build a neofetch-style profile card SVG: colored ASCII portrait + info panel.

Usage:
  python tools/gen_profile.py path/to/photo.jpg --preview
Options:
  --crop L,T,R,B   crop box as fractions of the image (default: face crop)
  --cols N         ASCII width in characters (default 46)
"""
import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

# dense -> sparse, indexed by darkness
RAMP = "@%#WM8&B$0QOZmwqpdbkhao*+~<>i!lI;:,\"^`'. "

THEMES = {
    "dark": dict(bg="#0d1117", stroke="#30363d", label="#58a6ff", value="#c9d1d9",
                 accent="#3fb950", head="#f778ba", dim="#8b949e", tone=(45, 210), invert=False),
    "light": dict(bg="#ffffff", stroke="#d0d7de", label="#0969da", value="#1f2328",
                  accent="#1a7f37", head="#bf3989", dim="#59636e", tone=(30, 140), invert=True),
}

FS = 9.0          # font-size, px
CW = FS * 0.60    # monospace advance
LH = FS * 1.02    # line height


def fetch_stats(user):
    """Live GitHub numbers; blanks if offline."""
    out = {}
    try:
        def get(url):
            req = urllib.request.Request(url, headers={"User-Agent": "profile-card"})
            return json.load(urllib.request.urlopen(req, timeout=15))

        u = get("https://api.github.com/users/" + user)
        out["repos"] = u["public_repos"]
        out["followers"] = u["followers"]
        rs = get("https://api.github.com/users/%s/repos?per_page=100" % user)
        out["stars"] = sum(r["stargazers_count"] for r in rs)
    except Exception as e:
        print("  ! github api unavailable (%s); using placeholders" % e, file=sys.stderr)
    return out


def uptime(since):
    d0 = datetime.fromisoformat(since).replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    y = now.year - d0.year - ((now.month, now.day) < (d0.month, d0.day))
    m = (now.month - d0.month) % 12
    return "%d years, %d months" % (y, m)


def ascii_art(path, crop, cols, tone, invert, gamma):
    im = Image.open(path)
    im = im.convert("RGBA") if im.mode in ("RGBA", "LA", "P") else im.convert("RGB")
    has_alpha = im.mode == "RGBA"
    W, H = im.size
    if crop == "auto" and has_alpha:
        # cutouts frame themselves: tightest box holding a visible pixel
        box = im.getchannel("A").point(lambda v: 255 if v > 40 else 0).getbbox()
        im = im.crop(box)
    elif crop == "auto":
        pass                    # no alpha to measure: use the whole photo
    else:
        l, t, r, b = crop
        im = im.crop((int(l * W), int(t * H), int(r * W), int(b * H)))
    if has_alpha:
        rgb = ImageEnhance.Contrast(im.convert("RGB")).enhance(1.25)
        rgb = ImageEnhance.Color(rgb).enhance(1.5)
        rgb.putalpha(im.getchannel("A"))
        im = rgb
    else:
        im = ImageEnhance.Contrast(im).enhance(1.35)
    cw, ch = im.size
    rows = max(1, round(cols * (ch / cw) * (CW / LH)))
    # Sharpen before the big downsample or eyes, mouth and jawline dissolve.
    im = im.filter(ImageFilter.UnsharpMask(radius=cw / cols * 0.9,
                                           percent=95, threshold=3))
    small = im.resize((cols, rows), Image.LANCZOS)

    def read(x, y):
        px = small.getpixel((x, y))
        if has_alpha:
            r_, g_, b_, a_ = px
            return (r_, g_, b_, a_)
        return px + (255,)

    def lum(r_, g_, b_):
        return (0.299 * r_ + 0.587 * g_ + 0.114 * b_) / 255.0

    # Stretch the ramp across the range the SUBJECT actually occupies. A photo
    # of a dark suit and dark hair only spans a slice of 0..1, and without this
    # most of the character ramp goes unused and the portrait reads as mush.
    vis = [lum(*read(x, y)[:3]) for y in range(rows) for x in range(cols)
           if read(x, y)[3] >= 128]
    vis.sort()
    # The top percentile is clipped hard on purpose: a white shirt or a
    # blown highlight would otherwise own the bright end of the range and
    # push the face -- the part anyone actually looks at -- into the mud.
    lo = vis[int(len(vis) * 0.02)] if vis else 0.0
    hi = vis[int(len(vis) * 0.88)] if vis else 1.0
    span = max(1e-3, hi - lo)

    grid = []
    for y in range(rows):
        line = []
        for x in range(cols):
            r_, g_, b_, a_ = read(x, y)
            if a_ < 128:                # outside the cutout: leave the card bare
                line.append((" ", "none"))
                continue
            v = min(1.0, max(0.0, (lum(r_, g_, b_) - lo) / span)) ** gamma
            d = v if invert else 1 - v
            ch_ = RAMP[min(len(RAMP) - 1, int(d * (len(RAMP) - 1)))]
            # Keep the pixel's hue but re-map its brightness onto the range
            # the card can actually show: scale the whole triple so its
            # brightest channel lands on the target. Without this the photo's
            # own (dim, indoor) range is what you get, and the portrait sinks
            # into the background.
            t0, t1 = tone
            target = t0 + t1 * v
            peak = max(r_, g_, b_, 1)
            col = "#%02x%02x%02x" % tuple(
                min(255, int(c * target / peak)) for c in (r_, g_, b_))
            line.append((ch_, col))
        grid.append(line)
    return grid


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def art_svg(grid, x0, y0):
    """One <text> per row; same-colour neighbours merged into a tspan run."""
    out = []
    for i, row in enumerate(grid):
        y = y0 + i * LH
        spans, run, col = [], "", row[0][1]
        for ch_, c in row:
            if c != col:
                spans.append((run, col))
                run, col = "", c
            run += ch_
        spans.append((run, col))
        parts, x = [], x0
        for run, c in spans:
            parts.append('<tspan x="%.1f" fill="%s">%s</tspan>' % (x, c, esc(run)))
            x += len(run) * CW
        out.append('<text y="%.1f">%s</text>' % (y, "".join(parts)))
    return "\n".join(out)


def panel_svg(lines, x0, y0, th, width_chars):
    out = []
    for i, ln in enumerate(lines):
        y = y0 + i * (LH * 1.55)
        kind = ln[0]
        if kind == "rule":
            title = ln[1]
            dashes = "-" * max(0, width_chars - len(title) - 3)
            out.append('<text x="%.1f" y="%.1f" fill="%s"><tspan fill="%s">%s</tspan> %s</text>'
                       % (x0, y, th["dim"], th["head"], esc(title), dashes))
        elif kind == "head":
            user, host = ln[1], ln[2]
            dashes = "-" * max(0, width_chars - len(user) - len(host) - 2)
            out.append('<text x="%.1f" y="%.1f">'
                       '<tspan fill="%s" font-weight="bold">%s</tspan>'
                       '<tspan fill="%s">@</tspan>'
                       '<tspan fill="%s" font-weight="bold">%s</tspan>'
                       '<tspan fill="%s"> %s</tspan></text>'
                       % (x0, y, th["accent"], esc(user), th["value"],
                          th["accent"], esc(host), th["dim"], dashes))
        else:  # ("kv", label, value)
            label, value = ln[1], ln[2]
            dots = "." * max(1, width_chars - len(label) - len(value) - 3)
            out.append('<text x="%.1f" y="%.1f">'
                       '<tspan fill="%s">%s:</tspan>'
                       '<tspan fill="%s"> %s </tspan>'
                       '<tspan fill="%s">%s</tspan></text>'
                       % (x0, y, th["label"], esc(label), th["dim"], dots,
                          th["value"], esc(value)))
    return "\n".join(out)


def build(grid, lines, th, panel_chars):
    pad = 18.0
    gap = 26.0
    art_w = len(grid[0]) * CW
    panel_w = panel_chars * CW
    art_h = len(grid) * LH
    panel_h = len(lines) * LH * 1.55
    W = pad * 2 + art_w + gap + panel_w
    H = pad * 2 + max(art_h, panel_h)
    y_art = pad + FS + max(0.0, (panel_h - art_h) / 2)
    y_pan = pad + FS
    font = ("'SFMono-Regular',Consolas,'Liberation Mono',"
            "'DejaVu Sans Mono',Menlo,monospace")
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="%.0f" height="%.0f" '
        'viewBox="0 0 %.0f %.0f" font-family="%s" font-size="%s">\n'
        '<rect width="100%%" height="100%%" rx="10" fill="%s" stroke="%s"/>\n'
        '<g xml:space="preserve">\n%s\n%s\n</g>\n</svg>\n'
        % (W, H, W, H, font, FS, th["bg"], th["stroke"],
           art_svg(grid, pad, y_art),
           panel_svg(lines, pad + art_w + gap, y_pan, th, panel_chars)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("photo")
    ap.add_argument("--crop", default="auto",
                    help="'auto' (uses the alpha channel) or L,T,R,B fractions")
    ap.add_argument("--cols", type=int, default=46)
    ap.add_argument("--user", default="mostafa842")
    ap.add_argument("--birth", default="2005-02-01")
    ap.add_argument("--gamma", type=float, default=1.0,
                    help="above 1 pushes midtones down, so a dark suit or dark "
                         "hair recedes instead of rendering as a solid block")
    ap.add_argument("--stats", action="store_true",
                    help="append live Repos/Stars/Followers rows")
    ap.add_argument("--themes", default="dark",
                    help="comma list: dark, light (the card carries its own "
                         "background, so one dark card suits both GitHub modes)")
    ap.add_argument("--preview", action="store_true")
    a = ap.parse_args()

    crop = "auto" if a.crop == "auto" else tuple(
        float(v) for v in a.crop.split(","))

    lines = [
        ("head", "mostafa", "serag"),
        ("kv", "OS", "Windows 11, Kali Linux"),
        ("kv", "Uptime", uptime(a.birth)),
        ("kv", "Host", "Damietta University, Egypt"),
        ("kv", "Kernel", "B.Sc. Computers & Artificial Intelligence"),
        ("kv", "IDE", "VS Code, Burp Suite, Git"),
        ("rule", "Languages"),
        ("kv", "Programming", "JavaScript, TypeScript, Python, C++"),
        ("kv", "Web", "Node.js, Express, React, HTML, CSS"),
        ("kv", "Data", "MongoDB, SQL, JSON, YAML"),
        ("kv", "Real", "Arabic (native), English"),
        ("rule", "Focus"),
        ("kv", "Security", "Web App Pentesting, OWASP Top 10"),
        ("kv", "Building", "CypherMind - AI cybersecurity learning"),
        ("kv", "Also", "Full-stack apps, RTL / Arabic-first UI"),
        ("rule", "Contact"),
        ("kv", "Email", "mostafaserag700@gmail.com"),
        ("kv", "GitHub", a.user),
    ]
    if a.stats:
        st = fetch_stats(a.user)
        lines += [
            ("rule", "GitHub Stats"),
            ("kv", "Repos", str(st.get("repos", "-"))),
            ("kv", "Stars", str(st.get("stars", "-"))),
            ("kv", "Followers", str(st.get("followers", "-"))),
        ]
    panel_chars = max((len(x[1]) + len(x[2]) + 4) if x[0] == "kv" else 46
                      for x in lines)

    ASSETS.mkdir(exist_ok=True)
    for name in [t.strip() for t in a.themes.split(",")]:
        th = THEMES[name]
        grid = ascii_art(a.photo, crop, a.cols, th["tone"], th["invert"], a.gamma)
        p = ASSETS / ("profile-%s.svg" % name)
        p.write_text(build(grid, lines, th, panel_chars), encoding="utf-8")
        print("  wrote %s" % p.relative_to(ROOT))
        if a.preview and name == "dark":
            (ASSETS / "preview.txt").write_text(
                "\n".join("".join(c for c, _ in row) for row in grid), encoding="utf-8")
            print("  wrote assets/preview.txt")


if __name__ == "__main__":
    main()
