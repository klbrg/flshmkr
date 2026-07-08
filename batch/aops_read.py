#!/usr/bin/env python3
"""Read an Art of Problem Solving ebook section from the debug Chrome session.

Navigates the AoPS tab to the given section URL (or reads the current one),
waits for the section body, and extracts the text with every LaTeX image
(<img class="latex"/"latexcenter">, alt = the LaTeX source) inlined as its
alt text, so formulas survive extraction. Prints JSON:

    {url, book_title, section_title, text, prev, next}

`prev`/`next` are the section-nav hrefs (e.g. /ebooks/intro-algebra-ebook/c1s2),
useful for walking a whole chapter. Stdlib only. Usage:

    python3 aops_read.py [url] [--port 9222]
"""
import argparse
import json
import sys
import time
import urllib.request

from cdp_read import _evaluate, _list_tabs, _pick_tab

EXTRACT_JS = r"""
(() => {
  const body = document.querySelector('.ebk-section-body');
  if (!body) return JSON.stringify({error: 'no .ebk-section-body (not loaded or not an ebook page)'});
  const clone = body.cloneNode(true);
  clone.querySelectorAll('img.latex, img.latexcenter').forEach(img => {
    const alt = img.getAttribute('alt') || '';
    const repl = img.className.includes('latexcenter') ? '\n' + alt + '\n' : ' ' + alt + ' ';
    img.replaceWith(document.createTextNode(repl));
  });
  // keep any other images visible as placeholders (figures)
  clone.querySelectorAll('img').forEach(img => {
    img.replaceWith(document.createTextNode('[figure: ' + (img.getAttribute('alt') || img.src || '') + ']'));
  });
  const holder = document.createElement('div');
  holder.style.position = 'fixed'; holder.style.left = '-99999px';
  holder.appendChild(clone);
  document.body.appendChild(holder);
  const text = clone.innerText;
  holder.remove();
  const nav = {};
  for (const a of document.querySelectorAll('a[href*="/ebooks/"]')) {
    const t = (a.innerText || '').trim();
    if (t === '<' && !nav.prev) nav.prev = a.getAttribute('href');
    if (t === '>') nav.next = a.getAttribute('href');   // last one = section-level next
  }
  const title = document.title.split(' - ')[0].trim();  // e.g. "1.1 Numbers"
  return JSON.stringify({url: location.href, book_title: document.title.split(' - ').slice(1).join(' - ').trim(),
                         section_title: title, text: text.trim(), prev: nav.prev || '', next: nav.next || ''});
})()
"""


def read_section(port: int, url: str | None) -> dict:
    tab = _pick_tab(_list_tabs(port), "artofproblemsolving.com")
    if url:
        _evaluate(tab["webSocketDebuggerUrl"], f"location.href = {json.dumps(url)}")
        for _ in range(40):
            time.sleep(0.5)
            probe = _evaluate(
                tab["webSocketDebuggerUrl"],
                "JSON.stringify((() => { const b = document.querySelector('.ebk-section-body');"
                " return {u: location.href, ready: !!b && !b.querySelector('img[src*=\"ludicrous\"]')"
                " && (b.innerText || '').length > 100}; })())",
            )
            try:
                p = json.loads(probe)
            except (TypeError, ValueError):
                continue
            if url.split("/")[-1] in p.get("u", "") and p.get("ready"):
                break
        else:
            sys.exit(f"section body never appeared for {url}")
        time.sleep(1)  # let latex images land in the DOM
    raw = _evaluate(tab["webSocketDebuggerUrl"], EXTRACT_JS)
    data = json.loads(raw) if isinstance(raw, str) else raw
    if data.get("error"):
        sys.exit(data["error"])
    return data


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("url", nargs="?", default=None)
    ap.add_argument("--port", type=int, default=9222)
    args = ap.parse_args()
    print(json.dumps(read_section(args.port, args.url), ensure_ascii=False))


if __name__ == "__main__":
    main()
