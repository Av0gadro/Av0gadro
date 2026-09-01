#!/usr/bin/env python3
"""Cut the background out of a photo so the ASCII portrait reads cleanly.

    python tools/cutout.py assets/photo.jpg [out.png]

Runs rembg locally (pip install rembg onnxruntime). The first run downloads the
u2net model (~176 MB) into ~/.u2net; every run after that is offline.
"""
import sys
from pathlib import Path

from PIL import Image
from rembg import remove

src = Path(sys.argv[1])
dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_name(src.stem + "-cutout.png")
out = remove(Image.open(src))
out.save(dst)
print("wrote %s  %sx%s" % (dst, *out.size))
