# CLAUDE.md

## Project overview

flshmkr is a Chrome extension + FastAPI backend that converts highlighted text from O'Reilly Learning and Microsoft Learn into Anki flashcards using Claude AI. It also includes a text rephrasing feature (Michael W. Lucas style).

## Architecture

- **`server/`** — Python 3.12+ FastAPI backend
  - `app.py` — 3 endpoints: `/generate`, `/add-to-anki`, `/rephrase`
  - `claude_client.py` — Claude API integration with caching (SHA256) and prompt hot-reloading
  - `anki_client.py` — AnkiConnect protocol (async), auto-creates/migrates card models
  - `models.py` — Pydantic request/response models
  - `config.py` — Env config (ANTHROPIC_API_KEY, SERVER_PORT, ANKI_CONNECT_URL)
  - `prompt.txt` / `rephrase_prompt.txt` — System prompts (hot-reloaded on change)
  - `card.css` — Shared Anki card styling
- **`extension/`** — Chrome Extension (Manifest V3, vanilla JS)
  - `content.js` — Page context extraction, rephrase overlay (Shadow DOM)
  - `background.js` — Context menu + keyboard shortcut handling
  - `popup.html/js/css` — Card preview/editor UI
- **`batch/`** — Whole-chapter batch ingestion (agent-driven, no server)
  - `launch-chrome.sh` — open Chrome with a debug port on a dedicated profile
  - `cdp_read.py` — read the open chapter via Chrome DevTools (stdlib only)
  - `cdp_images.py` — extract chapter figures (scrolls to load lazy images,
    fetches them in-page as base64); the agent views and selectively attaches them
  - `add_cards.py` — push a cards JSON (with optional `images`) to Anki via `anki_client`

## Two ways to make cards

- **Highlight-while-reading** — the extension + server: select text on a page,
  preview/edit in the sidebar, add. Best for cherry-picking facts.
- **Batch a whole chapter** — `batch/` + the agent. Run `batch/launch-chrome.sh`,
  open a chapter, then tell Claude Code "batch the open chapter" (or run the
  `batch-chapter` skill). The agent reads the chapter, formulates cards per
  `server/prompt.txt`, and pushes them. Procedure lives in
  `.claude/skills/batch-chapter/SKILL.md`. Deck names match the extension's,
  so both paths land in the same hierarchy.

## Running

**Server:**
```sh
cd server && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8000
```

**Extension:** Load `extension/` as unpacked extension in `chrome://extensions` (developer mode).

## Environment

Requires `.env` in `server/` with `ANTHROPIC_API_KEY`. Optional: `SERVER_PORT` (default 8000), `ANKI_CONNECT_URL` (default http://127.0.0.1:8765).

## Key conventions

- No frameworks on the frontend — vanilla JS only
- CORS restricted to `chrome-extension://` origins
- Prompts are `.txt` files with live-reload; edit them directly
- Flashcard caching uses SHA256 of text+book+chapter; feedback clears cache
- Anki deck hierarchy uses `::` separators (e.g., `azure::aks::concepts-network`)
- Card types: "basic" (front/back) and "cloze" ({{c1::deletions}})
