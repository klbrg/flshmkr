import hashlib
import json
from pathlib import Path
import re
import anthropic
from config import ANTHROPIC_API_KEY
from models import Flashcard, Image

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Cache: hash of (selected_text, book_title, chapter_title) → flashcards
_cache: dict[str, list[Flashcard]] = {}

_prompt_path = Path(__file__).parent / "prompt.txt"
_prompt_mtime = 0.0
_prompt_text = ""

_rephrase_prompt_path = Path(__file__).parent / "rephrase_prompt.txt"
_rephrase_prompt_mtime = 0.0
_rephrase_prompt_text = ""


def _get_prompt() -> str:
    global _prompt_mtime, _prompt_text
    mtime = _prompt_path.stat().st_mtime
    if mtime != _prompt_mtime:
        _prompt_text = _prompt_path.read_text()
        _prompt_mtime = mtime
        _cache.clear()
    return _prompt_text


def _get_rephrase_prompt() -> str:
    global _rephrase_prompt_mtime, _rephrase_prompt_text
    mtime = _rephrase_prompt_path.stat().st_mtime
    if mtime != _rephrase_prompt_mtime:
        _rephrase_prompt_text = _rephrase_prompt_path.read_text()
        _rephrase_prompt_mtime = mtime
    return _rephrase_prompt_text



def _cache_key(selected_text: str, book_title: str, chapter_title: str) -> str:
    raw = f"{selected_text}|{book_title}|{chapter_title}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _trim_toc(toc: str, chapter_title: str) -> str:
    """Extract only the current chapter's section from the full TOC."""
    if not toc or not chapter_title:
        return toc

    try:
        data = json.loads(toc)

        def find_chapter(items):
            if not isinstance(items, list):
                return None
            for item in items:
                label = item.get("label") or item.get("title") or ""
                if chapter_title.lower() in label.lower():
                    return item
                found = find_chapter(item.get("children") or item.get("items") or [])
                if found:
                    return found
            return None

        chapter = find_chapter(data if isinstance(data, list) else data.get("children", data.get("items", [])))
        if chapter:
            return json.dumps(chapter)
    except (json.JSONDecodeError, TypeError):
        pass

    return toc


def _detect_media_type(filename: str) -> str:
    if filename.endswith(".svg"):
        return "image/svg+xml"
    if filename.endswith(".png"):
        return "image/png"
    if filename.endswith(".gif"):
        return "image/gif"
    return "image/jpeg"


def generate_flashcards(
    selected_text: str, book_title: str, chapter_title: str, toc: str = "", images: list[Image] | None = None, feedback: str = ""
) -> list[Flashcard]:
    # Skip cache when feedback is present (regenerate should always produce fresh results)
    key = _cache_key(selected_text, book_title, chapter_title)
    if not feedback and key in _cache:
        return _cache[key]

    # Build system prompt: base instructions (cached) + book context (cached separately)
    system = [{"type": "text", "text": _get_prompt()}]

    context_parts = []
    if book_title:
        context_parts.append(f"Book: {book_title}")
    if chapter_title:
        context_parts.append(f"Chapter: {chapter_title}")
    if toc:
        trimmed = _trim_toc(toc, chapter_title)
        context_parts.append(f"Chapter outline:\n{trimmed}")

    if context_parts:
        system.append({
            "type": "text",
            "text": "\n".join(context_parts),
            "cache_control": {"type": "ephemeral"},
        })
    else:
        system[0]["cache_control"] = {"type": "ephemeral"}

    # Build user message: text + any images from the selection
    user_content: list[dict] = []
    if images:
        user_content.append({"type": "text", "text": "Reference images from the selection (for context only, do not include <img> tags):"})
        for img in images:
            user_content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": _detect_media_type(img.filename),
                    "data": img.data,
                },
            })
    user_content.append({"type": "text", "text": selected_text})
    if feedback:
        user_content.append({"type": "text", "text": f"User feedback on previous generation — follow these instructions:\n{feedback}"})

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": user_content}],
    )

    raw = response.content[0].text
    # Strip markdown code fences if present
    raw = re.sub(r"^```(?:json)?\s*\n?", "", raw)
    raw = re.sub(r"\n?```\s*$", "", raw)

    data = json.loads(raw)
    flashcards = [Flashcard(**card) for card in data["flashcards"]]

    # Store in cache
    _cache[key] = flashcards

    return flashcards


def rephrase_text(text: str) -> str:
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        system=_get_rephrase_prompt(),
        messages=[{"role": "user", "content": text}],
    )
    return response.content[0].text
