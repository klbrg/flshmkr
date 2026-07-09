#!/usr/bin/env python3
"""Extract chapters of 'Practical Linear Algebra for Data Science' (O'Reilly,
ISBN 9781098120603) from the authenticated debug-Chrome tab, via the content API.

Math is MathML with a precise spoken-form `alttext`; each <math> is replaced by
a ⟨…⟩ marker holding that spoken form, which the carding agent renders to LaTeX.
Code blocks are preserved as fenced blocks. Output: pla/<chNN>.json {title,text}.

Usage: python3 extract.py ch01 ch02 ...
"""
import json
import os
import sys

sys.path.insert(0, "/Users/p950bkv/Projects/Personal/flshmkr/batch")
from cdp_read import _list_tabs, _pick_tab, _evaluate  # noqa: E402

ISBN = "9781098120603"
OUT = "/Users/p950bkv/.claude/jobs/802442b3/tmp/pla"

EXTRACT_JS = r"""
(async () => {
  const isbn = '%s', file = '%s';
  const meta = await (await fetch(`https://learning.oreilly.com/api/v2/epub-chapters/urn:orm:book:${isbn}:chapter:${file}.html/`)).json();
  const html = await (await fetch(meta.content_url)).text();
  const doc = new DOMParser().parseFromString(html, 'text/html');
  // math -> spoken-form marker (precise; agent converts to LaTeX)
  doc.querySelectorAll('math').forEach(m => {
    const alt = (m.getAttribute('alttext') || '').trim();
    m.replaceWith(document.createTextNode(alt ? ' ⟨' + alt + '⟩ ' : ' '));
  });
  // code blocks -> fenced
  doc.querySelectorAll('pre').forEach(p => {
    p.replaceWith(document.createTextNode('\n```\n' + (p.textContent||'').trim() + '\n```\n'));
  });
  // drop figures/images (no usable diagrams; keep a marker)
  doc.querySelectorAll('img, svg, figure').forEach(e => e.replaceWith(document.createTextNode(' [figure] ')));
  const title = (doc.querySelector('h1, [data-type="title"]')?.textContent || meta.title || '').trim();
  const holder = document.createElement('div');
  holder.style.position = 'fixed'; holder.style.left = '-99999px';
  holder.appendChild(doc.body);
  document.body.appendChild(holder);
  const text = holder.innerText;
  holder.remove();
  return JSON.stringify({title, text: text.trim(), has_mathml: meta.has_mathml});
})()
"""


def main():
    tab = _pick_tab(_list_tabs(9222), "practical-linear-algebra")
    ws = tab["webSocketDebuggerUrl"]
    for file in sys.argv[1:]:
        path = f"{OUT}/{file}.json"
        if os.path.exists(path) and len(json.load(open(path)).get("text", "")) > 800:
            print(f"{file}: already extracted, skipping"); continue
        raw = _evaluate(ws, EXTRACT_JS % (ISBN, file))
        d = json.loads(raw) if isinstance(raw, str) else raw
        n = len(d.get("text", ""))
        if n < 500:
            sys.exit(f"{file}: suspiciously short ({n} chars) - aborting")
        json.dump(d, open(path, "w"), ensure_ascii=False)
        print(f"{file}: {d['title'][:55]!r} {n} chars, math={d.get('has_mathml')}")


if __name__ == "__main__":
    main()
