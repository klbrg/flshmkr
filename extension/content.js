// Cache: ISBN → { metadata, toc }
const cache = {};

// Extract book ISBN from the page URL
// URL pattern: https://learning.oreilly.com/library/view/book-name/ISBN/file.xhtml
function parseOreillyUrl() {
  const match = window.location.pathname.match(
    /\/library\/view\/[^/]+\/(\d{13}[^/]*)\//
  );
  if (match) return match[1];
  return null;
}

async function fetchBookMetadata(isbn) {
  try {
    const resp = await fetch(
      `https://learning.oreilly.com/api/v2/epubs/urn:orm:book:${isbn}/`
    );
    if (!resp.ok) return null;
    return await resp.json();
  } catch {
    return null;
  }
}

async function fetchToc(isbn) {
  try {
    const resp = await fetch(
      `https://learning.oreilly.com/api/v2/epubs/urn:orm:book:${isbn}/table-of-contents/`
    );
    if (!resp.ok) return "";
    const data = await resp.json();
    return JSON.stringify(data);
  } catch {
    return "";
  }
}

async function getBookData(isbn) {
  if (cache[isbn]) return cache[isbn];

  const [metadata, toc] = await Promise.all([
    fetchBookMetadata(isbn),
    fetchToc(isbn),
  ]);

  cache[isbn] = { metadata, toc };
  return cache[isbn];
}

// Find current chapter title from TOC by matching the current URL file
function getCurrentChapter(tocData) {
  try {
    const fileMatch = window.location.pathname.match(/\/([^/]+\.x?html)/);
    if (!fileMatch) return "";
    const currentFile = fileMatch[1];

    const toc = typeof tocData === "string" ? JSON.parse(tocData) : tocData;

    function search(items) {
      if (!Array.isArray(items)) return "";
      for (const item of items) {
        const href = item.href || item.url || "";
        if (href.includes(currentFile)) return item.label || item.title || "";
        const found = search(item.children || item.items || []);
        if (found) return found;
      }
      return "";
    }

    return search(toc);
  } catch {
    return "";
  }
}

// Extract <img> elements from the current selection range
function getSelectionImages() {
  const sel = window.getSelection();
  if (!sel || sel.rangeCount === 0) return [];

  const imgs = [];
  for (let i = 0; i < sel.rangeCount; i++) {
    const frag = sel.getRangeAt(i).cloneContents();
    frag.querySelectorAll("img").forEach((img) => {
      if (img.src) imgs.push(img.src);
    });
  }
  return imgs;
}

// Fetch an image URL and return { filename, data } with base64-encoded content
async function fetchImageAsBase64(url) {
  try {
    const resp = await fetch(url);
    const blob = await resp.blob();
    const buf = await blob.arrayBuffer();
    const bytes = new Uint8Array(buf);
    let binary = "";
    for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
    const base64 = btoa(binary);

    // Generate a short hash from the URL for a stable filename
    let hash = 0;
    for (let i = 0; i < url.length; i++) {
      hash = ((hash << 5) - hash + url.charCodeAt(i)) | 0;
    }
    const hex = Math.abs(hash).toString(16).padStart(8, "0");
    const ext = blob.type.includes("svg") ? "svg" : blob.type.includes("png") ? "png" : "jpg";
    const filename = `flshmkr_${hex}.${ext}`;

    return { filename, data: base64 };
  } catch {
    return null;
  }
}

// Extract context from learn.microsoft.com pages
// Produces deck hierarchy: Microsoft Learn::azure/aks/concepts-network
function parseMicrosoftLearn() {
  // Strip locale prefix (e.g. /en-us/) and join remaining path segments
  const pathParts = window.location.pathname
    .replace(/^\/[a-z]{2}(-[a-z]{2,})?\//i, "/")
    .split("/")
    .filter(Boolean);

  const formatSegment = (s) => {
    const words = s.split("-").join(" ");
    return words.length <= 3
      ? words.toUpperCase()
      : words.replace(/\b\w/g, (c) => c.toUpperCase());
  };

  const formatted = pathParts.map(formatSegment);

  return {
    book_title: formatted[0] || "Microsoft Learn",
    chapter_title: formatted.slice(1).join("::"),
    toc: "",
  };
}

function removeRephraseOverlay() {
  const existing = document.getElementById("flshmkr-rephrase-host");
  if (existing) existing.remove();
}

const REPHRASE_STYLES = `
  .overlay {
    max-width: 450px;
    min-width: 280px;
    background: #fff;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.15);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 14px;
    line-height: 1.6;
    color: #222;
    z-index: 2147483647;
    padding: 16px 20px 12px;
  }
  .text {
    white-space: pre-wrap;
    margin-bottom: 12px;
  }
  .error { color: #c0392b; }
  .loading {
    display: flex;
    align-items: center;
    gap: 10px;
    color: #666;
  }
  .spinner {
    width: 16px;
    height: 16px;
    border: 2px solid #e0e0e0;
    border-top-color: #2563eb;
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
  }
  button {
    border: none;
    border-radius: 4px;
    padding: 5px 12px;
    cursor: pointer;
    font-size: 13px;
    font-family: inherit;
  }
  .copy-btn { background: #2563eb; color: #fff; }
  .copy-btn:hover { background: #1d4ed8; }
  .close-btn { background: #f3f4f6; color: #555; }
  .close-btn:hover { background: #e5e7eb; }
`;

function getOverlayPosition() {
  const sel = window.getSelection();
  let top = window.scrollY + 100;
  let left = window.innerWidth / 2 - 225;
  if (sel && sel.rangeCount > 0) {
    const rect = sel.getRangeAt(0).getBoundingClientRect();
    top = window.scrollY + rect.bottom + 12;
    left = Math.max(16, Math.min(rect.left, window.innerWidth - 480));
  }
  return { top, left };
}

function createOverlayHost(pos) {
  removeRephraseOverlay();
  const host = document.createElement("div");
  host.id = "flshmkr-rephrase-host";
  host.style.cssText = `position:absolute;top:${pos.top}px;left:${pos.left}px;z-index:2147483647;`;
  const shadow = host.attachShadow({ mode: "closed" });
  const style = document.createElement("style");
  style.textContent = REPHRASE_STYLES;
  shadow.appendChild(style);
  document.body.appendChild(host);
  return { host, shadow };
}

function showRephraseLoading() {
  const pos = getOverlayPosition();
  const { shadow } = createOverlayHost(pos);

  const card = document.createElement("div");
  card.className = "overlay";
  card.innerHTML = '<div class="loading"><div class="spinner"></div>Rephrasing\u2026</div>';
  shadow.appendChild(card);
}

function showRephraseOverlay(text, isError) {
  const pos = getOverlayPosition();
  const { host, shadow } = createOverlayHost(pos);

  const card = document.createElement("div");
  card.className = "overlay";

  const textDiv = document.createElement("div");
  textDiv.className = isError ? "text error" : "text";
  textDiv.textContent = text;
  card.appendChild(textDiv);

  const actions = document.createElement("div");
  actions.className = "actions";

  if (!isError) {
    const copyBtn = document.createElement("button");
    copyBtn.className = "copy-btn";
    copyBtn.textContent = "Copy";
    copyBtn.addEventListener("click", () => {
      navigator.clipboard.writeText(text);
      copyBtn.textContent = "Copied!";
      setTimeout(() => { copyBtn.textContent = "Copy"; }, 1500);
    });
    actions.appendChild(copyBtn);
  }

  const closeBtn = document.createElement("button");
  closeBtn.className = "close-btn";
  closeBtn.textContent = "\u00d7";
  closeBtn.addEventListener("click", removeRephraseOverlay);
  actions.appendChild(closeBtn);

  card.appendChild(actions);
  shadow.appendChild(card);

  // Dismiss on Escape
  const onKey = (e) => {
    if (e.key === "Escape") {
      removeRephraseOverlay();
      document.removeEventListener("keydown", onKey);
    }
  };
  document.addEventListener("keydown", onKey);

  // Dismiss on click outside
  const onClick = (e) => {
    if (!host.contains(e.target)) {
      removeRephraseOverlay();
      document.removeEventListener("click", onClick);
    }
  };
  setTimeout(() => document.addEventListener("click", onClick), 100);
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.action === "showRephraseLoading") {
    showRephraseLoading();
    return;
  }

  if (msg.action === "showRephrase") {
    if (msg.error) {
      showRephraseOverlay(msg.error, true);
    } else {
      showRephraseOverlay(msg.rephrased_text, false);
    }
    return;
  }

  if (msg.action === "getSelectedText") {
    sendResponse({ selectedText: window.getSelection()?.toString()?.trim() || "" });
    return;
  }

  if (msg.action === "getContext") {
    const selectedText = window.getSelection()?.toString()?.trim() || "";
    const imgUrls = getSelectionImages();

    const buildResponse = async (base) => {
      const images = (await Promise.all(imgUrls.map(fetchImageAsBase64))).filter(Boolean);
      return { ...base, images };
    };

    const host = window.location.hostname;

    // Microsoft Learn path
    if (host === "learn.microsoft.com") {
      const ctx = parseMicrosoftLearn();
      buildResponse({ selected_text: selectedText, ...ctx }).then(sendResponse);
      return true;
    }

    // O'Reilly path
    const isbn = parseOreillyUrl();
    if (isbn) {
      getBookData(isbn).then(async ({ metadata, toc }) => {
        const bookTitle = metadata?.title || document.title;
        const chapterTitle = getCurrentChapter(toc);
        const resp = await buildResponse({
          selected_text: selectedText,
          book_title: bookTitle,
          chapter_title: chapterTitle,
          toc,
        });
        sendResponse(resp);
      });
      return true;
    }

    // Generic fallback
    buildResponse({
      selected_text: selectedText,
      book_title: document.title,
      chapter_title: "",
      toc: "",
    }).then(sendResponse);
    return true;
  }
  return true;
});
