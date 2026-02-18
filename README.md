# flshmkr

Chrome extension + local server that turns highlighted text on O'Reilly Learning and Microsoft Learn into Anki flashcards using Claude. Also rephrases selected text in Michael W. Lucas's writing style.

## How it works

**Flashcards:** Right-click highlighted text → "Generate Flashcards" → Claude generates atomic, minimum-information flashcards → review/edit in popup → send to Anki via AnkiConnect.

**Rephrase:** Select text → `Cmd+Shift+K` (`Ctrl+Shift+K` on Windows/Linux) → Claude rephrases it in MWL's voice in a floating overlay. Code snippets get explained instead of rewritten. Factual errors get called out.

## Setup

### Prerequisites

- Python 3.12+
- [Anki](https://apps.ankiweb.net/) with [AnkiConnect](https://ankiweb.net/shared/info/2055492159) plugin
- Anthropic API key

### Server

```sh
cd server
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `server/.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

Start the server:

```sh
uvicorn app:app --host 127.0.0.1 --port 8000
```

### Extension

1. Open `chrome://extensions`
2. Enable "Developer mode"
3. Click "Load unpacked" → select the `extension/` directory

## Supported sites

- `learning.oreilly.com` — extracts book title, chapter, and TOC for context
- `learn.microsoft.com` — builds deck hierarchy from URL path

## Project structure

```
server/
  app.py              FastAPI endpoints (/generate, /rephrase, /add-to-anki)
  claude_client.py    Claude API calls (flashcard generation, rephrase)
  anki_client.py      AnkiConnect integration
  models.py           Pydantic models
  config.py           Environment config
  prompt.txt          Flashcard generation system prompt
  rephrase_prompt.txt Rephrase system prompt
  card.css            Anki card styling

extension/
  manifest.json       Chrome extension manifest (MV3)
  background.js       Context menu + keyboard shortcut handlers
  content.js          Page context extraction + rephrase overlay
  popup.html/js/css   Flashcard review/edit popup
```

## Configuration

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Required. Anthropic API key. |
| `SERVER_PORT` | `8000` | Server port. |
| `ANKI_CONNECT_URL` | `http://127.0.0.1:8765` | AnkiConnect endpoint. |
