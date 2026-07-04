import re
import anthropic
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from models import (
    GenerateRequest,
    GenerateResponse,
    AddToAnkiRequest,
    AddToAnkiResponse,
    RephraseRequest,
    RegenerateCardRequest,
    RegenerateCardResponse,
)
from claude_client import generate_flashcards, rephrase_text_stream, regenerate_card
from anki_client import add_notes, get_tags


async def _safe_get_tags() -> list[str]:
    try:
        return await get_tags()
    except Exception:
        return []

app = FastAPI(title="flshmkr")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^(chrome-extension://.*|https://learning\.oreilly\.com|https://learn\.microsoft\.com|https://git-scm\.com)$",
    allow_methods=["POST"],
    allow_headers=["*"],
)


def _make_deck_name(book_title: str, chapter_title: str) -> str:
    def clean(s: str) -> str:
        return re.sub(r"[:\"]+", "", s).strip()


    # Chapter titles with :: are pre-formatted deck hierarchies (e.g. Microsoft Learn)
    if "::" in chapter_title:
        parts = []
        if book_title:
            parts.append(clean(book_title))
        parts.extend(clean(seg) for seg in chapter_title.split("::") if clean(seg))
        return "::".join(parts) if parts else "Default"

    parts = ["Books"]
    if book_title:
        parts.append(clean(book_title))
    if chapter_title:
        parts.append(clean(chapter_title))
    return "::".join(parts)


@app.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    existing_tags = await _safe_get_tags()
    try:
        flashcards = generate_flashcards(
            req.selected_text,
            req.book_title,
            req.chapter_title,
            req.toc,
            req.images,
            req.feedback,
            req.surrounding_text,
            existing_tags,
        )
    except anthropic.RateLimitError:
        raise HTTPException(status_code=429, detail="Rate limited — wait a moment and try again")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Claude API error: {e}")

    deck_name = _make_deck_name(req.book_title, req.chapter_title)
    return GenerateResponse(flashcards=flashcards, deck_name=deck_name, images=req.images)


@app.post("/regenerate-card", response_model=RegenerateCardResponse)
async def regenerate_card_endpoint(req: RegenerateCardRequest):
    existing_tags = await _safe_get_tags()
    try:
        card = regenerate_card(
            req.card, req.feedback, req.selected_text,
            req.book_title, req.chapter_title, req.toc, req.images,
            req.surrounding_text, existing_tags,
        )
    except anthropic.RateLimitError:
        raise HTTPException(status_code=429, detail="Rate limited — wait a moment and try again")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Claude API error: {e}")

    return RegenerateCardResponse(card=card)


@app.post("/add-to-anki", response_model=AddToAnkiResponse)
async def add_to_anki(req: AddToAnkiRequest):
    try:
        added, errors = await add_notes(req.flashcards, req.deck_name, req.images)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=f"AnkiConnect error: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Connection error: {e}")

    return AddToAnkiResponse(added=added, errors=errors)


@app.post("/rephrase")
async def rephrase(req: RephraseRequest):
    def iter_chunks():
        try:
            for chunk in rephrase_text_stream(req.text):
                yield chunk
        except anthropic.RateLimitError:
            yield "\n[error: rate limited, try again]"
        except Exception as e:
            yield f"\n[error: {e}]"

    return StreamingResponse(iter_chunks(), media_type="text/plain; charset=utf-8")
