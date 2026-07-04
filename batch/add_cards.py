#!/usr/bin/env python3
"""Push a batch of flashcards straight to Anki via the server's anki_client.

Reads a JSON object from a file or stdin:

    {"deck_name": "Books::...",
     "cards": [{"card_type": "...", "front": "...", "back": "...", "tags": [...]}, ...],
     "images": [{"filename": "tt_fig1-1.jpg", "data": "<base64>"}, ...]}

then calls anki_client.add_notes (which ensures models/deck, stores any media,
and dedupes by front/text). Reference an image from a card by putting
<img src="FILENAME"> in its front/back. No FastAPI server involved. Usage:

    python3 add_cards.py cards.json
    python3 add_cards.py < cards.json
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "server"))

from anki_client import add_notes  # noqa: E402
from models import Flashcard, Image  # noqa: E402


async def main() -> None:
    raw = Path(sys.argv[1]).read_text() if len(sys.argv) > 1 else sys.stdin.read()
    payload = json.loads(raw)
    deck = payload["deck_name"]
    cards = [Flashcard(**c) for c in payload["cards"]]
    images = [Image(**i) for i in payload.get("images", [])]

    print(f"Deck: {deck}")
    print(f"Cards: {len(cards)} | Images: {len(images)}")
    added, errors = await add_notes(cards, deck, images or None)
    print(f"Added/updated: {added}")
    for e in errors:
        print("  error:", e)


if __name__ == "__main__":
    asyncio.run(main())
