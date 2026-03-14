from pathlib import Path

import httpx
from config import ANKI_CONNECT_URL
from models import Flashcard, Image

CARD_CSS = (Path(__file__).parent / "card.css").read_text()

BASIC_FRONT = """\
<div class=card>
<p>{{Front}}</p>
<hr>
</div>"""

BASIC_BACK = """\
<div class=card>
<p>{{Front}}</p>
<hr>
<div class=back>
<p>{{Back}}</p>
</div>
</div>"""

CLOZE_FRONT = """\
<div class=card>
<p>{{cloze:Text}}</p>
</div>"""

CLOZE_BACK = """\
<div class=card>
<p>{{cloze:Text}}</p>
<hr>
<div class=extra>
{{Extra}}
</div>
</div>"""

BASIC_MODEL = {
    "modelName": "flshmkr Basic",
    "inOrderFields": ["Front", "Back"],
    "css": CARD_CSS,
    "cardTemplates": [
        {
            "Name": "Card 1",
            "Front": BASIC_FRONT,
            "Back": BASIC_BACK,
        }
    ],
}

CLOZE_MODEL = {
    "modelName": "flshmkr Cloze",
    "inOrderFields": ["Text", "Extra"],
    "css": CARD_CSS,
    "isCloze": True,
    "cardTemplates": [
        {
            "Name": "Cloze",
            "Front": CLOZE_FRONT,
            "Back": CLOZE_BACK,
        }
    ],
}


async def _invoke(action: str, **params) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            ANKI_CONNECT_URL,
            json={"action": action, "version": 6, "params": params},
        )
        result = resp.json()
        if result.get("error"):
            raise RuntimeError(result["error"])
        return result


async def ensure_models() -> None:
    result = await _invoke("modelNames")
    existing = set(result.get("result", []))

    for model in (BASIC_MODEL, CLOZE_MODEL):
        name = model["modelName"]
        if name not in existing:
            await _invoke("createModel", **model)
        else:
            await _invoke(
                "updateModelStyling",
                model={"name": name, "css": CARD_CSS},
            )
            templates = {
                t["Name"]: {"Front": t["Front"], "Back": t["Back"]}
                for t in model["cardTemplates"]
            }
            await _invoke(
                "updateModelTemplates",
                model={"name": name, "templates": templates},
            )

    await _migrate_notes()


async def _migrate_notes() -> None:
    """Migrate Basic/Cloze notes in Books decks to flshmkr models."""
    migrations = [
        ("Basic", "flshmkr Basic"),
        ("Cloze", "flshmkr Cloze"),
    ]

    for old_model, new_model in migrations:
        result = await _invoke(
            "findNotes", query=f'"deck:Books" "note:{old_model}"'
        )
        note_ids = result.get("result", [])
        if not note_ids:
            continue

        info = await _invoke("notesInfo", notes=note_ids)
        for note in info.get("result", []):
            fields = {k: v["value"] for k, v in note["fields"].items()}
            await _invoke(
                "updateNoteModel",
                note={
                    "id": note["noteId"],
                    "modelName": new_model,
                    "fields": fields,
                    "tags": note["tags"],
                },
            )


async def ensure_deck(deck_name: str) -> None:
    await _invoke("createDeck", deck=deck_name)


async def store_images(images: list[Image]) -> None:
    for img in images:
        await _invoke("storeMediaFile", filename=img.filename, data=img.data)


async def add_notes(
    flashcards: list[Flashcard], deck_name: str, images: list[Image] | None = None
) -> tuple[int, list[str]]:
    await ensure_models()
    await ensure_deck(deck_name)

    if images:
        await store_images(images)

    # Find images not referenced by Claude in any card
    all_content = " ".join(c.front + c.back for c in flashcards)
    missing = [img for img in (images or []) if img.filename not in all_content]
    if missing:
        missing_html = "<br>" + "".join(f'<img src="{img.filename}">' for img in missing)
        # Append to the back of the last card
        flashcards[-1].back += missing_html

    added = 0
    updated = 0
    errors = []

    for i, card in enumerate(flashcards):
        tags = list({*card.tags, "flshmkr"})

        if card.card_type == "cloze":
            model = "flshmkr Cloze"
            fields = {"Text": card.front, "Extra": card.back}
            search_field = "Text"
        else:
            model = "flshmkr Basic"
            fields = {"Front": card.front, "Back": card.back}
            search_field = "Front"

        # Check for existing note with the same front/text in this deck
        search_val = fields[search_field].replace('"', '\\"')
        query = f'"deck:{deck_name}" "note:{model}" "{search_field}:{search_val}"'

        try:
            found = await _invoke("findNotes", query=query)
            existing_ids = found.get("result", [])

            if existing_ids:
                # Update the first matching note
                await _invoke(
                    "updateNoteFields",
                    note={"id": existing_ids[0], "fields": fields},
                )
                updated += 1
            else:
                await _invoke(
                    "addNote",
                    note={
                        "deckName": deck_name,
                        "modelName": model,
                        "fields": fields,
                        "tags": tags,
                    },
                )
                added += 1
        except Exception as e:
            errors.append(f"Card {i + 1}: {e}")

    return added + updated, errors
