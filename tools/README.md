# Profile card generator

Turns a photo into the neofetch-style card at the top of the profile README:
a colour-per-character ASCII portrait on the left, an info panel on the right.
It writes an **SVG**, not a code block — GitHub markdown can't render ANSI colour,
but it does render SVG images.

```bash
# 1. cut the background out once (local, offline after the first model download)
python tools/cutout.py assets/photo.jpg            # -> assets/photo-cutout.png
# 2. build the card (this is the exact command behind the committed SVG)
python tools/gen_profile.py assets/photo-cutout.png --crop 0.50,0.10,0.99,0.62 --cols 75
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
| `--cols N` | `46` | Portrait width in characters. More = finer detail, and (at a fixed `ART_FS`) a wider card. 75 is what the committed crop needs; at 64 the face visibly mushes. |
| `--mono` | off | Greyscale portrait. Hue was carrying much of the separation between skin, hair and collar, so mono also applies `MONO_CONTRAST` to widen the grey range; without it the face flattens into mid-greys. |
| `--gamma N` | `1.0` | Above 1 pushes midtones down, so a dark suit recedes instead of rendering as a solid block. It costs face detail fast — 1.2 was already too much here. |
| `--themes` | `dark` | Comma list of `dark` / `light`. |
| `--birth YYYY-MM-DD` | `2005-02-01` | Feeds the `Uptime:` line. |
| `--stats` | off | Appends live Repos / Stars / Followers rows, fetched from the GitHub API at build time. Off by default: a card that advertises a zero star count is worse than a card that says nothing about it. |
| `--user` | `Av0gadro` | Whose numbers `--stats` fetches. |

Tuning the crop is most of the game, and it is a straight trade: the wider you
frame, the fewer characters the face gets. The committed crop is head and
shoulders, stopping above the suit — the card is laid out side by side, so any
torso the crop keeps is height the portrait spends without gaining face.

Two edges are load-bearing. `l = 0.50` is just left of the hairline and exists
to cut the book spine at the photo's left edge; below about 0.47 it comes back,
and above about 0.52 the hair starts clipping. `b = 0.62` is the collar. Run
with `--preview`, look at `assets/preview.txt`, adjust, repeat.

The level stretch clips the top 12% of brightness (in `ascii_art`). That is
deliberate: the white shirt would otherwise take the bright end of the ramp and
leave the face flat.

## Font sizes

`ART_FS` and `PANEL_FS` at the top of `gen_profile.py` are separate on purpose.
GitHub shows the card at its natural width inside a README column of roughly
880px, so the emitted font size is what the reader actually gets — nobody zooms
in. A single shared size makes you choose between a legible panel and a card too
wide to fit; splitting them lets the portrait stay dense (`ART_FS = 7.5`) while
the panel is comfortably readable (`PANEL_FS = 15`).

Raising `PANEL_FS` widens the card by `panel_chars x 0.6` px per point, so keep
the total under ~890px — check the `width=` in the generated SVG. If it grows
past that, shorten the longest panel value rather than shrinking the font again.

`PROW` is the panel's row pitch in line heights. 1.55 suited a 9px panel; at
18px that reads as a canyon, so it is 1.45.

The portrait's on-screen size is `--cols x ART_FS x 0.6`, and detail and size
are separate knobs: to shrink the photo without losing the face, drop `ART_FS`
and keep the column count high rather than cutting columns. The characters stop
being individually readable, which does not matter — at this size the art works
as halftone, and more cells means a sharper face. Going the other way (64
columns at a larger `ART_FS`) covers the same pixels and looks worse.

The panel text lives in `lines = [...]` inside `main()` — plain tuples,
`("kv", label, value)` for a row and `("rule", title)` for a section header.
Re-run the script after editing; the stats rows refresh from the GitHub API
every time (and fall back to `-` if you're offline).

## Publishing

The card only shows up on your GitHub profile if this lives in a repo named
after your account:

```bash
gh repo create Av0gadro --public --description "Profile README"   # once
git init && git add . && git commit -m "profile readme"
git remote add origin https://github.com/Av0gadro/Av0gadro.git
git push -u origin main
```

Keep `README.md`, `assets/` and `tools/` together — the README references the
SVGs by relative path.
