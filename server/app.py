import re
import anthropic
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models import (
    GenerateRequest,
    GenerateResponse,
    AddToAnkiRequest,
    AddToAnkiResponse,
    RephraseRequest,
    RephraseResponse,
)
from claude_client import generate_flashcards, rephrase_text
from anki_client import add_notes

app = FastAPI(title="flshmkr")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^chrome-extension://.*$",
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
    try:
        flashcards = generate_flashcards(
            req.selected_text, req.book_title, req.chapter_title, req.toc, req.images, req.feedback
        )
    except anthropic.RateLimitError:
        raise HTTPException(status_code=429, detail="Rate limited — wait a moment and try again")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Claude API error: {e}")

    deck_name = _make_deck_name(req.book_title, req.chapter_title)
    return GenerateResponse(flashcards=flashcards, deck_name=deck_name, images=req.images)


@app.post("/add-to-anki", response_model=AddToAnkiResponse)
async def add_to_anki(req: AddToAnkiRequest):
    try:
        added, errors = await add_notes(req.flashcards, req.deck_name, req.images)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=f"AnkiConnect error: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Connection error: {e}")

    return AddToAnkiResponse(added=added, errors=errors)


@app.post("/rephrase", response_model=RephraseResponse)
async def rephrase(req: RephraseRequest):
    try:
        rephrased = rephrase_text(req.text)
    except anthropic.RateLimitError:
        raise HTTPException(status_code=429, detail="Rate limited — wait a moment and try again")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Claude API error: {e}")

    return RephraseResponse(rephrased_text=rephrased)
