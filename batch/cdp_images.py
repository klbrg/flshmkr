#!/usr/bin/env python3
"""Extract figure images from the chapter open in the debug Chrome session.

Scrolls the page to materialize O'Reilly's lazy-loaded <img> elements, fetches
each image inside the page context (so your auth cookies apply), saves the bytes
to an output directory, and writes a manifest.json describing them.

The agent then VIEWS the saved images (they are real files on disk) to decide
which figures are worth attaching and to which card - rather than blindly
mapping by filename. Worthwhile figures get referenced from a card via
<img src="FILENAME"> and their base64 passed to add_cards.py in the "images"
array.

Usage:
    python3 cdp_images.py OUTDIR [--port 9222] [--match learning.oreilly.com] [--prefix book_]

Prints the manifest path and one line per image (filename WxH). Each manifest
entry has: figref, filename (prefixed), data (base64), w, h, src.
"""
import argparse
import base64
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from batch.cdp_read import _list_tabs, _pick_tab, _evaluate  # noqa: E402

# Scroll to force lazy images to load, then fetch each <img> in-page as base64.
JS = r"""
(async () => {
  const sleep = (ms) => new Promise(r => setTimeout(r, ms));
  const h = document.body.scrollHeight;
  for (let y = 0; y <= h; y += 600) { window.scrollTo(0, y); await sleep(40); }
  window.scrollTo(0, 0); await sleep(200);

  const root = document.querySelector('#sbo-rt-content') || document.querySelector('main') || document.body;
  const out = [];
  for (const im of root.querySelectorAll('img')) {
    const src = im.currentSrc || im.src || '';
    if (!src) continue;
    let data = '';
    try {
      const buf = new Uint8Array(await (await (await fetch(src)).blob()).arrayBuffer());
      let bin = '';
      for (let i = 0; i < buf.length; i++) bin += String.fromCharCode(buf[i]);
      data = btoa(bin);
    } catch (e) { continue; }
    out.push({ src, alt: im.alt || '', w: im.naturalWidth, h: im.naturalHeight, data });
  }
  return JSON.stringify(out);
})()
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("--port", type=int, default=9222)
    ap.add_argument("--match", default=None)
    ap.add_argument("--prefix", default="", help="prepended to Anki filenames to avoid cross-book collisions")
    args = ap.parse_args()

    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)

    tab = _pick_tab(_list_tabs(args.port), args.match)
    raw = _evaluate(tab["webSocketDebuggerUrl"], JS)
    imgs = json.loads(raw) if isinstance(raw, str) else raw

    manifest = []
    for im in imgs:
        m = re.search(r"/([^/]+?)\.(jpe?g|png|gif|svg)", im["src"], re.I)
        figref = m.group(1) if m else "img"
        ext = (m.group(2) if m else "jpg").lower().replace("jpeg", "jpg")
        filename = f"{args.prefix}{figref}.{ext}"
        (out / filename).write_bytes(base64.b64decode(im["data"]))
        manifest.append({
            "figref": figref, "filename": filename,
            "data": im["data"], "w": im["w"], "h": im["h"], "src": im["src"],
        })

    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"saved {len(manifest)} images to {out}")
    for r in manifest:
        print(f"  {r['filename']}  {r['w']}x{r['h']}")


if __name__ == "__main__":
    main()
