# Profile card generator

Turns a photo into the neofetch-style card at the top of the profile README:
a colour-per-character ASCII portrait on the left, an info panel on the right.
It writes an **SVG**, not a code block — GitHub markdown can't render ANSI colour,
but it does render SVG images.

```bash
# 1. cut the background out once (local, offline after the first model download)
python tools/cutout.py assets/photo.jpg            # -> assets/photo-cutout.png
# 2. build the card (this is the exact command behind the committed SVG)
python tools/gen_profile.py assets/photo-cutout.png --crop 0.38,0.12,0.99,0.72 --cols 84
```

A raw photo works too, but the result is muddy: ASCII density tracks brightness,
so a bright sky or a building behind you renders just as loudly as your face.
With a cutout, everything outside the subject is left blank and the portrait
reads the way the reference profile's does.

Outputs `assets/profile-dark.svg` and, with `--preview`, a plain-text
`assets/preview.txt` so you can eyeball the crop without opening the SVG.

The card paints its own dark background, so the single dark SVG looks right in
both GitHub themes — same as the profile this is modelled on. `--themes light`
exists, but a photo rendered as dark ink on white reads as a negative; it is
not what you want unless you go find a much higher-contrast portrait.

## Options

| Flag | Default | What it does |
| --- | --- | --- |
| `--crop` | `auto` | `auto` trims a cutout to its own bounding box. For a raw photo pass `L,T,R,B` fractions and tighten until `preview.txt` is mostly face and shoulders. |
| `--cols N` | `46` | Portrait width in characters. More = finer detail and a wider card. 80 is what makes the face legible here; below ~60 it turns to mush. |
| `--gamma N` | `1.0` | Above 1 pushes midtones down, so a dark suit recedes instead of rendering as a solid block. It costs face detail fast — 1.2 was already too much here. |
| `--themes` | `dark` | Comma list of `dark` / `light`. |
| `--birth YYYY-MM-DD` | `2005-02-01` | Feeds the `Uptime:` line. |
| `--stats` | off | Appends live Repos / Stars / Followers rows, fetched from the GitHub API at build time. Off by default: a card that advertises a zero star count is worse than a card that says nothing about it. |
| `--user` | `mostafa842` | Whose numbers `--stats` fetches. |

Tuning the crop is most of the game, and it is a straight trade: the wider you
frame, the fewer characters the face gets. The committed crop is head, shoulders
and suit — far enough back to read as a portrait rather than a close-up — and 84
columns is what that framing needs to stay legible. Crop tighter and you can
drop the column count; crop wider and you must raise it. Run with `--preview`,
look at `assets/preview.txt`, adjust, repeat.

The level stretch clips the top 12% of brightness (in `ascii_art`). That is
deliberate: the white shirt would otherwise take the bright end of the ramp and
leave the face flat.

The panel text lives in `lines = [...]` inside `main()` — plain tuples,
`("kv", label, value)` for a row and `("rule", title)` for a section header.
Re-run the script after editing; the stats rows refresh from the GitHub API
every time (and fall back to `-` if you're offline).

## Publishing

The card only shows up on your GitHub profile if this lives in a repo named
after your account:

```bash
gh repo create mostafa842 --public --description "Profile README"   # once
git init && git add . && git commit -m "profile readme"
git remote add origin https://github.com/mostafa842/mostafa842.git
git push -u origin main
```

Keep `README.md`, `assets/` and `tools/` together — the README references the
SVGs by relative path.
