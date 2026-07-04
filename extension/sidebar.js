// Shadow-DOM flashcard sidebar. Slides in from the right with a floating toggle button.
(function () {
  "use strict";
  if (window.__flshmkrSidebarInjected) return;
  window.__flshmkrSidebarInjected = true;

  const SERVER = "http://127.0.0.1:8000";
  const STATE_KEY = "flshmkr-sidebar-open";
  const DEFAULT_FEEDBACK = "shorter and simpler question/answer";

  // --- Host + Shadow DOM ---
  const host = document.createElement("div");
  host.id = "flshmkr-sidebar-host";
  host.style.all = "initial";
  const shadow = host.attachShadow({ mode: "open" });

  const style = document.createElement("style");
  style.textContent = `
    :host, * { box-sizing: border-box; }
    :host {
      --bg: #ffffff;
      --surface: #ffffff;
      --surface-alt: #f5f5f5;
      --border: #e0e0e0;
      --border-strong: #111111;
      --text: #111111;
      --muted: #6b7280;
      --accent: #d80000;
      --accent-hover: #ff1a1a;
      --accent-soft: #fff5f5;
      --warn: #d97706;
      --warn-bg: #fff8e7;
      --warn-border: #d97706;
      --danger: #d80000;
      --cloze: #ffe97a;
      --radius: 4px;
      --radius-sm: 3px;
      --mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
      --sans: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, sans-serif;
    }

    .sb {
      position: fixed;
      top: 0; right: 0; bottom: 0;
      width: 480px;
      background: var(--bg);
      color: var(--text);
      font: 13px/1.45 var(--mono);
      z-index: 2147483646;
      display: flex;
      flex-direction: column;
      transform: translateX(100%);
      transition: transform 0.22s ease;
      border-left: 3px solid #111111;
    }
    .sb.open { transform: translateX(0); }

    .sb-header {
      padding: 10px 16px;
      border-bottom: 2px solid #111111;
      background: #ffffff;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-shrink: 0;
    }
    .sb-brand {
      font-weight: 700;
      font-size: 12px;
      letter-spacing: 1px;
      text-transform: uppercase;
    }
    .sb-close {
      background: transparent;
      border: none;
      color: #111111;
      cursor: pointer;
      font-size: 20px;
      line-height: 1;
      padding: 2px 6px;
      opacity: 0.6;
      transition: opacity 0.12s ease, color 0.12s ease;
    }
    .sb-close:hover { opacity: 1; color: var(--accent); }

    .sb-body { flex: 1; overflow-y: auto; padding: 16px; }

    .toggle {
      position: fixed;
      top: 50%;
      right: 0;
      transform: translateY(-50%);
      width: 22px;
      height: 56px;
      background: #ffffff;
      color: #111111;
      border: 2px solid #111111;
      border-right: none;
      border-radius: 4px 0 0 4px;
      box-shadow: -2px 2px 0 0 #111111;
      cursor: pointer;
      z-index: 2147483647;
      font-size: 18px;
      font-weight: 900;
      padding: 0;
      transition: right 0.22s ease, background 0.12s ease, transform 0.06s ease, box-shadow 0.06s ease;
    }
    .toggle:hover { background: #f5f5f5; }
    .toggle:active { transform: translateY(calc(-50% + 2px)) translateX(-2px); box-shadow: 0 0 0 0 #111111; }
    .toggle.open { right: 480px; }

    .state { display: block; }
    .hidden { display: none !important; }
    .muted { color: var(--muted); font-size: 11px; }
    .spacer { flex: 1; }

    #loading { text-align: center; padding: 48px 0; }
    .spinner {
      width: 28px; height: 28px;
      border: 3px solid #e0e0e0;
      border-top-color: var(--accent);
      border-radius: 50%;
      animation: spin 0.7s linear infinite;
      margin: 0 auto 12px;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    .meta {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin-bottom: 16px;
    }
    .meta label:nth-child(3) { grid-column: span 2; }
    .meta label { display: flex; flex-direction: column; gap: 4px; }
    .meta label span {
      font-family: var(--mono);
      font-weight: 700;
      font-size: 10px;
      color: #111111;
      text-transform: uppercase;
      letter-spacing: 0.6px;
    }

    input[type="text"], textarea {
      width: 100%;
      padding: 7px 10px;
      border: 1.5px solid #bdbdbd;
      border-radius: 3px;
      font-size: 12.5px;
      font-family: var(--mono);
      color: #111111;
      background: #ffffff;
      transition: border-color 0.12s ease, box-shadow 0.12s ease;
    }
    input[type="text"]:focus, textarea:focus {
      outline: none;
      border-color: #111111;
      box-shadow: 2px 2px 0 0 var(--accent);
    }
    textarea { resize: vertical; line-height: 1.5; }

    .card {
      background: #fdfcf7;
      border: 1.5px solid #c8c4b8;
      border-radius: 4px;
      padding: 12px;
      margin-bottom: 12px;
      box-shadow: 2px 2px 0 0 #d4d4d4;
      transition: box-shadow 0.15s, border-color 0.15s;
    }
    .card:focus-within { border-color: #111111; box-shadow: 2px 2px 0 0 var(--accent); }

    .card-header { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
    .card-header select {
      padding: 4px 8px;
      border: 1.5px solid #bdbdbd;
      border-radius: 3px;
      background: #ffffff;
      font-size: 10.5px;
      font-family: var(--mono);
      font-weight: 700;
      color: #111111;
      cursor: pointer;
      text-transform: uppercase;
      letter-spacing: 0.4px;
    }
    .card-number {
      font-family: var(--mono);
      font-size: 10.5px;
      font-weight: 700;
      color: #ffffff;
      background: var(--accent);
      padding: 2px 7px;
      border-radius: 3px;
      letter-spacing: 0.4px;
    }
    .card-delete {
      margin-left: auto;
      background: transparent;
      border: none;
      padding: 4px 6px;
      cursor: pointer;
      color: #111111;
      opacity: 0.5;
      font-size: 18px;
      line-height: 1;
      transition: opacity 0.12s ease, color 0.12s ease;
    }
    .card-delete:hover { opacity: 1; color: var(--accent); }

    .field { margin-bottom: 10px; }
    .field-label {
      font-family: var(--mono);
      font-size: 10px;
      font-weight: 700;
      color: #111111;
      text-transform: uppercase;
      letter-spacing: 0.6px;
      margin-bottom: 4px;
    }
    .field textarea { min-height: 40px; }

    .preview {
      margin-top: 4px;
      padding: 9px 11px;
      background: #f7f7f5;
      border-radius: 3px;
      font-family: var(--sans);
      font-size: 13px;
      line-height: 1.5;
      color: #111111;
      border-left: 3px solid #111111;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .preview:empty::before { content: "Empty"; color: var(--muted); font-style: italic; font-family: var(--mono); }
    .preview code {
      background: #ffffff;
      border: 1px solid #d4d4d4;
      padding: 1px 4px;
      border-radius: 3px;
      font-family: var(--mono);
      font-size: 11.5px;
    }
    .preview pre {
      background: #111111;
      color: #f5f5f5;
      padding: 10px 12px;
      border-radius: 3px;
      margin: 6px 0;
      overflow-x: auto;
      font-family: var(--mono);
      font-size: 11.5px;
    }
    .preview pre code { background: transparent; border: none; padding: 0; color: inherit; }
    .preview .cloze { background: var(--cloze); padding: 0 3px; border-radius: 2px; font-weight: 600; }

    .tags-editor { margin-top: 10px; padding-top: 10px; border-top: 1px dashed var(--border); }
    .tags-input {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      padding: 4px;
      border: 1.5px solid #bdbdbd;
      border-radius: 3px;
      background: #ffffff;
      min-height: 32px;
      align-items: center;
      transition: border-color 0.12s ease, box-shadow 0.12s ease;
    }
    .tags-input:focus-within { border-color: #111111; box-shadow: 2px 2px 0 0 var(--accent); }
    .tag-chip {
      display: inline-flex;
      align-items: center;
      gap: 3px;
      background: var(--accent);
      color: #ffffff;
      font-family: var(--mono);
      font-size: 10.5px;
      font-weight: 700;
      padding: 2px 4px 2px 7px;
      border-radius: 3px;
      letter-spacing: 0.3px;
    }
    .tag-chip button {
      background: transparent;
      border: none;
      color: #ffffff;
      cursor: pointer;
      padding: 0 2px;
      font-size: 12px;
      line-height: 1;
      opacity: 0.7;
      box-shadow: none;
    }
    .tag-chip button:hover { opacity: 1; }
    .tag-input {
      border: none;
      outline: none;
      padding: 3px 4px;
      font-size: 11.5px;
      background: transparent;
      flex: 1;
      min-width: 80px;
      color: #111111;
      font-family: var(--mono);
    }

    .warnings { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; }
    .warning {
      display: inline-flex;
      align-items: center;
      gap: 3px;
      background: var(--warn-bg);
      color: var(--warn);
      border: 1.5px solid var(--warn-border);
      font-family: var(--mono);
      font-size: 10px;
      font-weight: 700;
      padding: 1px 7px;
      border-radius: 3px;
      text-transform: uppercase;
      letter-spacing: 0.3px;
      cursor: help;
    }

    .card-regen {
      display: flex;
      gap: 6px;
      margin-top: 10px;
      padding-top: 10px;
      border-top: 1px dashed var(--border);
    }
    .card-regen input {
      flex: 1;
      padding: 6px 10px;
      border: 1.5px solid #bdbdbd;
      border-radius: 3px;
      font-size: 11.5px;
      font-family: var(--mono);
      background: #ffffff;
      transition: border-color 0.12s ease, box-shadow 0.12s ease;
    }
    .card-regen input:focus { outline: none; border-color: #111111; box-shadow: 2px 2px 0 0 var(--accent); }
    .card-regen button {
      padding: 4px 12px;
      font-size: 10px;
      background: #ffffff;
      color: #111111;
      border: 2px solid #111111;
      border-radius: 3px;
      box-shadow: 2px 2px 0 0 #111111;
      cursor: pointer;
      font-family: var(--mono);
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.4px;
      transition: transform 0.06s ease, box-shadow 0.06s ease, background 0.12s ease;
    }
    .card-regen button:hover:not(:disabled) { background: #f5f5f5; }
    .card-regen button:active:not(:disabled) { transform: translate(2px, 2px); box-shadow: 0 0 0 0 #111111; }
    .card-regen button:disabled { opacity: 0.5; cursor: wait; }
    .card.regenerating { opacity: 0.6; pointer-events: none; }

    .card-images {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 8px;
      padding-top: 8px;
      border-top: 1px dashed var(--border);
    }
    .image-toggle {
      display: flex;
      align-items: center;
      gap: 4px;
      cursor: pointer;
      padding: 2px 5px;
      border-radius: 3px;
    }
    .image-toggle:hover { background: #f5f5f5; }
    .image-toggle img {
      max-width: 38px;
      max-height: 38px;
      border: 2px solid #111111;
      border-radius: 3px;
      object-fit: contain;
    }
    .image-toggle input[type="checkbox"] { margin: 0; accent-color: var(--accent); }

    #image-previews {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 10px;
      padding: 10px;
      border: 2px solid #111111;
      border-radius: 4px;
      background: #ffffff;
    }
    #image-previews img {
      max-width: 64px;
      max-height: 64px;
      border: 2px solid #111111;
      border-radius: 3px;
      object-fit: contain;
    }

    .regen-all { display: flex; gap: 8px; margin-top: 14px; align-items: flex-start; }
    .regen-all textarea { flex: 1; min-height: 36px; font-size: 12px; }

    .actions {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 16px;
      padding-top: 14px;
      border-top: 2px solid #111111;
    }
    .shortcut-hint {
      font-family: var(--mono);
      font-size: 11px;
      font-weight: 700;
      padding: 2px 7px;
      background: #111111;
      color: #ffffff;
      border-radius: 3px;
      letter-spacing: 0.3px;
    }

    button {
      padding: 7px 14px;
      border: 2px solid #111111;
      border-radius: 3px;
      cursor: pointer;
      font-size: 11px;
      font-family: var(--mono);
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.6px;
      box-shadow: 2px 2px 0 0 #111111;
      transition: transform 0.06s ease, box-shadow 0.06s ease, background 0.12s ease;
    }
    button:disabled { opacity: 0.5; cursor: not-allowed; box-shadow: 2px 2px 0 0 #111111; }
    button:active:not(:disabled) { transform: translate(2px, 2px); box-shadow: 0 0 0 0 #111111; }

    .primary { background: var(--accent); color: #ffffff; }
    .primary:hover:not(:disabled) { background: var(--accent-hover); }

    .secondary { background: #ffffff; color: #111111; }
    .secondary:hover:not(:disabled) { background: #f5f5f5; }

    .ghost {
      background: #ffffff;
      color: #111111;
      border: 2px dashed #111111;
      box-shadow: none;
    }
    .ghost:hover:not(:disabled) { background: #f5f5f5; border-style: solid; }
    .ghost:active:not(:disabled) { transform: none; box-shadow: none; }

    #confirmation { text-align: center; padding: 32px 0; }
    #confirm-msg { margin-bottom: 18px; white-space: pre-wrap; font-family: var(--mono); font-size: 13px; }
    .confirm-actions { display: flex; gap: 10px; justify-content: center; }
    .error-text { color: var(--accent); font-weight: 700; }
  `;
  shadow.appendChild(style);

  const sb = document.createElement("div");
  sb.className = "sb";
  sb.innerHTML = `
    <div class="sb-header">
      <span class="sb-brand">flshmkr</span>
      <button class="sb-close" title="Close">&times;</button>
    </div>
    <div class="sb-body">
      <div id="loading" class="state hidden">
        <div class="spinner"></div>
        <p class="muted">Generating flashcards…</p>
      </div>
      <div id="empty" class="state">
        <p class="muted">Select text on an O'Reilly or MS Learn page, then right-click → <strong>Generate Flashcards</strong>.</p>
      </div>
      <div id="preview" class="state hidden">
        <div class="meta">
          <label><span>Book</span><input type="text" id="book-title"></label>
          <label><span>Chapter</span><input type="text" id="chapter-title"></label>
          <label><span>Deck</span><input type="text" id="deck-name"></label>
        </div>
        <div id="cards"></div>
        <div id="image-previews" class="hidden"></div>
        <div class="regen-all">
          <textarea id="feedback" placeholder="Feedback for regenerating all cards…"></textarea>
          <button id="regenerate" class="secondary">Regenerate all</button>
        </div>
        <div class="actions">
          <button id="add-card" class="ghost">+ Add card</button>
          <div class="spacer"></div>
          <span class="shortcut-hint muted">⌘↵</span>
          <button id="send-to-anki" class="primary">Send to Anki</button>
        </div>
      </div>
      <div id="confirmation" class="state hidden">
        <p id="confirm-msg"></p>
        <div class="confirm-actions">
          <button id="retry" class="secondary hidden">Retry</button>
          <button id="done" class="primary">Done</button>
        </div>
      </div>
    </div>
  `;
  shadow.appendChild(sb);

  const toggle = document.createElement("button");
  toggle.className = "toggle";
  toggle.textContent = "‹";
  toggle.title = "Toggle flshmkr sidebar";
  shadow.appendChild(toggle);

  document.documentElement.appendChild(host);

  // --- Open/close state ---

  let isOpen = false;
  try { isOpen = localStorage.getItem(STATE_KEY) === "true"; } catch {}

  function applyOpen() {
    sb.classList.toggle("open", isOpen);
    toggle.classList.toggle("open", isOpen);
    toggle.textContent = isOpen ? "›" : "‹";
    try { localStorage.setItem(STATE_KEY, isOpen ? "true" : "false"); } catch {}
  }
  applyOpen();

  toggle.addEventListener("click", () => { isOpen = !isOpen; applyOpen(); });
  shadow.querySelector(".sb-close").addEventListener("click", () => { isOpen = false; applyOpen(); });

  window.addEventListener("keydown", (e) => {
    const realTarget = (e.composedPath && e.composedPath()[0]) || e.target;
    if (realTarget && realTarget.matches && realTarget.matches('input, textarea, [contenteditable="true"]')) return;
    if (e.metaKey || e.ctrlKey || e.altKey || e.shiftKey) return;
    if (e.key !== "ä") return;
    e.preventDefault();
    e.stopImmediatePropagation();
    isOpen = !isOpen;
    applyOpen();
  }, true);

  // --- Card state ---

  const $ = (sel) => shadow.querySelector(sel);
  const showState = (id) => {
    shadow.querySelectorAll(".state").forEach((el) => el.classList.add("hidden"));
    $(`#${id}`).classList.remove("hidden");
  };

  let flashcards = [];
  let images = [];
  let lastContext = null;
  let cardImages = [];
  let cardFeedback = [];

  // --- HTML rendering & lint ---

  const ALLOWED_TAG = /<(\/?)(code|pre|img|br|hr)(\s[^>]*)?>/gi;

  function renderFieldHtml(text) {
    const stash = [];
    let marked = text.replace(ALLOWED_TAG, (m) => {
      stash.push(m);
      return `\x00${stash.length - 1}\x00`;
    });
    marked = marked.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    marked = marked.replace(/\x00(\d+)\x00/g, (_, i) => stash[parseInt(i)]);
    marked = marked.replace(
      /\{\{c\d+::([^}]*?)(?:::[^}]*?)?\}\}/g,
      '<span class="cloze">$1</span>'
    );
    return marked;
  }

  function lintCard(card) {
    const warnings = [];
    const all = `${card.front}\n${card.back}`;
    const clozeCount = (all.match(/\{\{c\d+::/g) || []).length;

    if (card.card_type === "cloze" && clozeCount === 0) {
      warnings.push({ tag: "no cloze", tip: "Cloze card with no {{c1::…}} deletion" });
    }
    if (card.card_type === "basic" && clozeCount > 0) {
      warnings.push({ tag: "cloze in basic", tip: "Basic card contains cloze syntax" });
    }
    if (clozeCount > 1) {
      warnings.push({ tag: "multi-cloze", tip: "Multiple deletions hurt recall - split into overlapping cards" });
    }
    if (card.back.length > 220) {
      warnings.push({ tag: "long back", tip: "Back over 220 chars - likely compound. Split." });
    }
    const sentences = card.back.replace(/<[^>]+>/g, "").split(/[.!?]\s+[A-Z]/g);
    if (sentences.length > 2) {
      warnings.push({ tag: "compound", tip: "Back has multiple sentences - likely two facts" });
    }
    if (/\b(as mentioned|above|previously|as noted)\b/i.test(all)) {
      warnings.push({ tag: "not self-contained", tip: "Card references other content - rewrite to stand alone" });
    }
    if (/\u2014/.test(all)) {
      warnings.push({ tag: "em dash", tip: "Replace \u2014 with -" });
    }
    if (!card.tags || card.tags.length < 2) {
      warnings.push({ tag: "tags", tip: "Needs at least 2 tags (high-level + hierarchical)" });
    }
    if (!card.front.trim() || !card.back.trim()) {
      if (!(card.card_type === "cloze" && !card.back.trim() && clozeCount > 0)) {
        warnings.push({ tag: "empty", tip: "Front or back is empty" });
      }
    }
    return warnings;
  }

  function renderWarnings(card) {
    const wrap = document.createElement("div");
    wrap.className = "warnings";
    lintCard(card).forEach((w) => {
      const el = document.createElement("span");
      el.className = "warning";
      el.textContent = w.tag;
      el.title = w.tip;
      wrap.appendChild(el);
    });
    return wrap;
  }

  function renderTagsEditor(card, i) {
    const wrap = document.createElement("div");
    wrap.className = "tags-editor";

    const label = document.createElement("div");
    label.className = "field-label";
    label.textContent = "Tags";
    wrap.appendChild(label);

    const input = document.createElement("div");
    input.className = "tags-input";

    const textInput = document.createElement("input");
    textInput.type = "text";
    textInput.className = "tag-input";

    const renderChips = () => {
      input.querySelectorAll(".tag-chip").forEach((el) => el.remove());
      (card.tags || []).forEach((t, j) => {
        const chip = document.createElement("span");
        chip.className = "tag-chip";
        chip.textContent = t;
        const x = document.createElement("button");
        x.textContent = "\u00d7";
        x.addEventListener("click", () => {
          card.tags.splice(j, 1);
          renderChips();
          updateCardUi(i);
        });
        chip.appendChild(x);
        input.insertBefore(chip, textInput);
      });
      textInput.placeholder = card.tags?.length ? "" : "add tag";
    };

    textInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === ",") {
        e.preventDefault();
        const val = textInput.value.trim().replace(/,$/, "");
        if (val) {
          card.tags = card.tags || [];
          card.tags.push(val);
          textInput.value = "";
          renderChips();
          updateCardUi(i);
        }
      } else if (e.key === "Backspace" && !textInput.value && card.tags?.length) {
        card.tags.pop();
        renderChips();
        updateCardUi(i);
      }
    });

    input.appendChild(textInput);
    renderChips();
    wrap.appendChild(input);
    return wrap;
  }

  function updateCardUi(i) {
    const cardEl = shadow.querySelector(`.card[data-i="${i}"]`);
    if (!cardEl) return;
    const card = flashcards[i];
    cardEl.querySelector('[data-preview="front"]').innerHTML = renderFieldHtml(card.front);
    cardEl.querySelector('[data-preview="back"]').innerHTML = renderFieldHtml(card.back);
    const warnHost = cardEl.querySelector(".card-header .warnings");
    if (warnHost) warnHost.replaceWith(renderWarnings(card));
  }

  function renderCards() {
    const container = $("#cards");
    container.innerHTML = "";

    flashcards.forEach((card, i) => {
      const frontLabel = card.card_type === "cloze" ? "Text" : "Front";
      const backLabel = card.card_type === "cloze" ? "Extra" : "Back";

      const div = document.createElement("div");
      div.className = "card";
      div.dataset.i = i;

      const header = document.createElement("div");
      header.className = "card-header";

      const num = document.createElement("span");
      num.className = "card-number";
      num.textContent = `#${i + 1}`;
      header.appendChild(num);

      const sel = document.createElement("select");
      sel.innerHTML = `
        <option value="basic" ${card.card_type === "basic" ? "selected" : ""}>Basic</option>
        <option value="cloze" ${card.card_type === "cloze" ? "selected" : ""}>Cloze</option>
      `;
      sel.addEventListener("change", () => {
        flashcards[i].card_type = sel.value;
        renderCards();
      });
      header.appendChild(sel);

      header.appendChild(renderWarnings(card));

      const del = document.createElement("button");
      del.className = "card-delete";
      del.textContent = "\u00d7";
      del.title = "Delete card";
      del.addEventListener("click", () => {
        flashcards.splice(i, 1);
        cardImages.splice(i, 1);
        cardFeedback.splice(i, 1);
        renderCards();
      });
      header.appendChild(del);
      div.appendChild(header);

      [["front", frontLabel], ["back", backLabel]].forEach(([key, labelText]) => {
        const field = document.createElement("div");
        field.className = "field";
        const fl = document.createElement("div");
        fl.className = "field-label";
        fl.textContent = labelText;
        field.appendChild(fl);

        const ta = document.createElement("textarea");
        ta.value = card[key];
        ta.addEventListener("input", () => {
          flashcards[i][key] = ta.value;
          updateCardUi(i);
        });
        field.appendChild(ta);

        const preview = document.createElement("div");
        preview.className = "preview";
        preview.dataset.preview = key;
        preview.innerHTML = renderFieldHtml(card[key]);
        field.appendChild(preview);

        div.appendChild(field);
      });

      div.appendChild(renderTagsEditor(card, i));

      if (images.length) {
        const imgDiv = document.createElement("div");
        imgDiv.className = "card-images";
        images.forEach((img, j) => {
          const label = document.createElement("label");
          label.className = "image-toggle";
          const cb = document.createElement("input");
          cb.type = "checkbox";
          cb.checked = cardImages[i]?.[j] ?? true;
          cb.addEventListener("change", () => { cardImages[i][j] = cb.checked; });
          const thumb = document.createElement("img");
          thumb.src = `data:image/png;base64,${img.data}`;
          thumb.title = img.filename;
          label.appendChild(cb);
          label.appendChild(thumb);
          imgDiv.appendChild(label);
        });
        div.appendChild(imgDiv);
      }

      const regen = document.createElement("div");
      regen.className = "card-regen";
      const regenInput = document.createElement("input");
      regenInput.type = "text";
      regenInput.placeholder = "How to improve this card…";
      regenInput.value = cardFeedback[i] || "";
      regenInput.addEventListener("input", () => { cardFeedback[i] = regenInput.value; });
      const regenBtn = document.createElement("button");
      regenBtn.textContent = "Improve";
      const runRegen = async () => {
        const fb = regenInput.value.trim();
        if (!fb) { regenInput.focus(); return; }
        regenBtn.disabled = true;
        regenBtn.textContent = "…";
        div.classList.add("regenerating");
        try {
          const improved = await regenerateSingleCard(card, fb);
          flashcards[i] = improved;
          cardFeedback[i] = "";
          renderCards();
        } catch (e) {
          regenBtn.textContent = "Retry";
          regenBtn.disabled = false;
          div.classList.remove("regenerating");
          regenInput.title = e.message;
        }
      };
      regenBtn.addEventListener("click", runRegen);
      regenInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") { e.preventDefault(); runRegen(); }
      });
      regen.appendChild(regenInput);
      regen.appendChild(regenBtn);
      div.appendChild(regen);

      container.appendChild(div);
    });
  }

  function renderImages() {
    const container = $("#image-previews");
    container.innerHTML = "";
    if (!images.length) {
      container.classList.add("hidden");
      return;
    }
    container.classList.remove("hidden");
    images.forEach((img) => {
      const el = document.createElement("img");
      el.src = `data:image/png;base64,${img.data}`;
      el.title = img.filename;
      container.appendChild(el);
    });
  }

  // --- Server calls ---

  async function generateCards(context) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30000);
    try {
      const resp = await fetch(`${SERVER}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(context),
        signal: controller.signal,
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || `Server error ${resp.status}`);
      }
      return resp.json();
    } catch (e) {
      if (e.name === "AbortError") throw new Error("Request timed out — try again");
      throw e;
    } finally {
      clearTimeout(timeout);
    }
  }

  async function regenerateSingleCard(card, feedback) {
    const resp = await fetch(`${SERVER}/regenerate-card`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        card,
        feedback,
        selected_text: lastContext?.selected_text || "",
        book_title: lastContext?.book_title || "",
        chapter_title: lastContext?.chapter_title || "",
        toc: lastContext?.toc || "",
        images: lastContext?.images || [],
        surrounding_text: lastContext?.surrounding_text || "",
      }),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `Server error ${resp.status}`);
    }
    const data = await resp.json();
    return data.card;
  }

  async function sendToAnki() {
    const cardsToSend = flashcards.map((card, i) => {
      const imgTags = images
        .filter((_, j) => cardImages[i]?.[j])
        .map((img) => `<img src="${img.filename}">`)
        .join("");
      if (!imgTags) return card;
      return { ...card, back: card.back + imgTags };
    });

    const resp = await fetch(`${SERVER}/add-to-anki`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        flashcards: cardsToSend,
        deck_name: $("#deck-name").value,
        images,
      }),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `Server error ${resp.status}`);
    }
    return resp.json();
  }

  // --- Flow ---

  async function startGeneration(ctx) {
    lastContext = ctx;
    showState("loading");
    try {
      const result = await generateCards(ctx);
      flashcards = result.flashcards;
      images = result.images || [];
      cardImages = flashcards.map(() => images.map(() => true));
      cardFeedback = flashcards.map(() => "");
      $("#book-title").value = ctx.book_title || "";
      $("#chapter-title").value = ctx.chapter_title || "";
      $("#deck-name").value = result.deck_name;
      renderCards();
      renderImages();
      $("#feedback").value = DEFAULT_FEEDBACK;
      showState("preview");
    } catch (e) {
      $("#confirm-msg").textContent = `Error: ${e.message}`;
      $("#confirm-msg").classList.add("error-text");
      $("#retry").classList.add("hidden");
      showState("confirmation");
    }
  }

  async function runSendToAnki() {
    const btn = $("#send-to-anki");
    if (btn.disabled) return;
    btn.disabled = true;
    btn.textContent = "Sending…";
    try {
      const result = await sendToAnki();
      let msg = `Added ${result.added} card(s) to Anki.`;
      if (result.errors.length) msg += "\n" + result.errors.join("\n");
      $("#confirm-msg").textContent = msg;
      $("#confirm-msg").classList.remove("error-text");
      $("#retry").classList.add("hidden");
      showState("confirmation");
      flashcards = [];
      images = [];
      cardImages = [];
      cardFeedback = [];
      lastContext = null;
      $("#cards").innerHTML = "";
      $("#image-previews").innerHTML = "";
      $("#image-previews").classList.add("hidden");
      $("#book-title").value = "";
      $("#chapter-title").value = "";
      $("#deck-name").value = "";
      $("#feedback").value = "";
    } catch (e) {
      const hint = /failed to fetch|network|anki/i.test(e.message)
        ? "\n\nIs Anki running with AnkiConnect installed?"
        : "";
      $("#confirm-msg").textContent = `Error: ${e.message}${hint}`;
      $("#confirm-msg").classList.add("error-text");
      $("#retry").classList.remove("hidden");
      showState("confirmation");
    } finally {
      btn.disabled = false;
      btn.textContent = "Send to Anki";
    }
  }

  $("#add-card").addEventListener("click", () => {
    flashcards.push({ card_type: "basic", front: "", back: "", tags: [] });
    cardImages.push(images.map(() => true));
    cardFeedback.push("");
    renderCards();
  });

  $("#regenerate").addEventListener("click", async () => {
    if (!lastContext) return;
    const feedback = $("#feedback").value.trim();
    const ctx = { ...lastContext };
    if (feedback) ctx.feedback = feedback;
    showState("loading");
    try {
      const result = await generateCards(ctx);
      flashcards = result.flashcards;
      images = result.images || [];
      cardImages = flashcards.map(() => images.map(() => true));
      cardFeedback = flashcards.map(() => "");
      renderCards();
      renderImages();
      $("#feedback").value = DEFAULT_FEEDBACK;
      showState("preview");
    } catch (e) {
      $("#confirm-msg").textContent = `Error: ${e.message}`;
      $("#confirm-msg").classList.add("error-text");
      $("#retry").classList.add("hidden");
      showState("confirmation");
    }
  });

  $("#send-to-anki").addEventListener("click", runSendToAnki);
  $("#retry").addEventListener("click", () => {
    $("#retry").classList.add("hidden");
    showState("preview");
    runSendToAnki();
  });
  $("#done").addEventListener("click", () => {
    showState(flashcards.length ? "preview" : "empty");
  });

  // Cmd/Ctrl+Enter to send
  shadow.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      if (!$("#preview").classList.contains("hidden")) runSendToAnki();
    }
  });

  // Keep page shortcuts (O'Reilly's j/k navigation etc.) from hijacking typing.
  ["keydown", "keyup", "keypress"].forEach((evt) => {
    host.addEventListener(evt, (e) => e.stopPropagation());
  });

  // --- Public API ---

  window.__flshmkrSidebar = {
    open() { isOpen = true; applyOpen(); },
    close() { isOpen = false; applyOpen(); },
    toggle() { isOpen = !isOpen; applyOpen(); },
    openWithContext(ctx) { isOpen = true; applyOpen(); startGeneration(ctx); },
  };
})();
