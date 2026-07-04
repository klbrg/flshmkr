#!/usr/bin/env python3
"""Read the currently-open chapter from a Chrome DevTools session.

Connects to Chrome's remote debugging port (default 9222), finds the active
reading tab (O'Reilly / MS Learn / git-scm, else the first page tab), extracts
the chapter text + metadata, and prints a JSON object:

    {url, book_title, chapter_title, deck_name, text}

Stdlib only - no websocket-client dependency. Usage:

    python3 cdp_read.py [--port 9222] [--match learning.oreilly.com]
"""
import argparse
import base64
import json
import os
import re
import socket
import struct
import sys
import urllib.request

READING_HOSTS = ("learning.oreilly.com", "learn.microsoft.com", "git-scm.com")

# JS evaluated in the page. Mirrors the extension's content.js extraction for
# O'Reilly; falls back to a generic title + main-text grab elsewhere.
EXTRACT_JS = r"""
(async () => {
  const out = { url: location.href, book_title: document.title, chapter_title: "", toc: "" };
  const m = location.pathname.match(/\/library\/view\/[^/]+\/(\d{13}[^/]*)\//);
  const isbn = m ? m[1] : null;
  if (isbn) {
    try {
      const meta = await (await fetch(`https://learning.oreilly.com/api/v2/epubs/urn:orm:book:${isbn}/`)).json();
      out.book_title = meta?.title || document.title;
    } catch (e) {}
    let toc = "";
    try {
      toc = JSON.stringify(await (await fetch(`https://learning.oreilly.com/api/v2/epubs/urn:orm:book:${isbn}/table-of-contents/`)).json());
    } catch (e) {}
    out.toc = toc;
    try {
      const fileMatch = location.pathname.match(/\/([^/]+\.x?html)/);
      const currentFile = fileMatch ? fileMatch[1] : "";
      const search = (items) => {
        if (!Array.isArray(items)) return "";
        for (const it of items) {
          const href = it.href || it.url || "";
          if (currentFile && href.includes(currentFile)) return it.label || it.title || "";
          const f = search(it.children || it.items || []);
          if (f) return f;
        }
        return "";
      };
      out.chapter_title = search(toc ? JSON.parse(toc) : []);
    } catch (e) {}
  }
  const sel = document.querySelector('#sbo-rt-content') || document.querySelector('main')
           || document.querySelector('article') || document.body;
  out.text = (sel.innerText || "").trim();
  return JSON.stringify(out);
})()
"""


def _list_tabs(port: int) -> list[dict]:
    with urllib.request.urlopen(f"http://localhost:{port}/json", timeout=5) as r:
        return json.load(r)


def _pick_tab(tabs: list[dict], match: str | None) -> dict:
    pages = [t for t in tabs if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]
    if not pages:
        sys.exit("No debuggable page tabs found. Is a chapter open in the debug Chrome?")
    if match:
        for t in pages:
            if match in t.get("url", ""):
                return t
        sys.exit(f"No tab whose URL contains {match!r}.")
    for t in pages:
        if any(h in t.get("url", "") for h in READING_HOSTS):
            return t
    return pages[0]


def _evaluate(ws_url: str, expression: str) -> object:
    host_port, path = ws_url.split("/devtools/", 1)
    host, port = host_port.replace("ws://", "").split(":")
    path = "/devtools/" + path
    sock = socket.create_connection((host, int(port)))
    key = base64.b64encode(os.urandom(16)).decode()
    sock.sendall(
        f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nUpgrade: websocket\r\n"
        f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n\r\n".encode()
    )
    buf = b""
    while b"\r\n\r\n" not in buf:
        buf += sock.recv(4096)

    def send(data: bytes) -> None:
        hdr = bytearray([0x81])
        mask = os.urandom(4)
        n = len(data)
        if n < 126:
            hdr.append(0x80 | n)
        elif n < 65536:
            hdr.append(0x80 | 126)
            hdr += struct.pack(">H", n)
        else:
            hdr.append(0x80 | 127)
            hdr += struct.pack(">Q", n)
        hdr += mask
        sock.sendall(bytes(hdr) + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def recv() -> bytes:
        def rd(n: int) -> bytes:
            out = b""
            while len(out) < n:
                chunk = sock.recv(n - len(out))
                if not chunk:
                    raise ConnectionError("socket closed")
                out += chunk
            return out
        rd(1)
        n = rd(1)[0] & 0x7F
        if n == 126:
            n = struct.unpack(">H", rd(2))[0]
        elif n == 127:
            n = struct.unpack(">Q", rd(8))[0]
        return rd(n)

    send(json.dumps({
        "id": 1, "method": "Runtime.evaluate",
        "params": {"expression": expression, "returnByValue": True, "awaitPromise": True},
    }).encode())
    while True:
        data = json.loads(recv().decode("utf-8", "replace"))
        if data.get("id") == 1:
            sock.close()
            res = data.get("result", {}).get("result", {})
            return res.get("value")


def _clean(s: str) -> str:
    return re.sub(r'[:"]+', "", s).strip()


def make_deck_name(book_title: str, chapter_title: str) -> str:
    """Replicates server/app.py _make_deck_name so batch and extension agree."""
    if "::" in chapter_title:
        parts = []
        if book_title:
            parts.append(_clean(book_title))
        parts.extend(_clean(seg) for seg in chapter_title.split("::") if _clean(seg))
        return "::".join(parts) if parts else "Default"
    parts = ["Books"]
    if book_title:
        parts.append(_clean(book_title))
    if chapter_title:
        parts.append(_clean(chapter_title))
    return "::".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=9222)
    ap.add_argument("--match", default=None, help="substring to pick a tab by URL")
    args = ap.parse_args()

    tab = _pick_tab(_list_tabs(args.port), args.match)
    raw = _evaluate(tab["webSocketDebuggerUrl"], EXTRACT_JS)
    data = json.loads(raw) if isinstance(raw, str) else raw
    data["deck_name"] = make_deck_name(data.get("book_title", ""), data.get("chapter_title", ""))
    data.pop("toc", None)  # large; not needed downstream
    print(json.dumps(data, ensure_ascii=False))


if __name__ == "__main__":
    main()
