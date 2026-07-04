import hashlib
import json
from pathlib import Path
import re
from typing import Iterator
import anthropic
from config import ANTHROPIC_API_KEY
from models import Flashcard, Image

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

FLASHCARD_TOOL = {
    "name": "create_flashcards",
    "description": "Submit the flashcards generated from the highlighted text.",
    "input_schema": {
        "type": "object",
        "properties": {
            "flashcards": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "card_type": {"type": "string", "enum": ["basic", "cloze"]},
                        "front": {"type": "string"},
                        "back": {"type": "string"},
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 2,
                            "maxItems": 4,
                        },
                    },
                    "required": ["card_type", "front", "back", "tags"],
                },
            }
        },
        "required": ["flashcards"],
    },
}

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


_ALLOWED_TAG = re.compile(
    r"<(/?)(code|pre|img|br|hr)(\s[^>]*)?>", re.IGNORECASE
)


def _escape_non_html(text: str) -> str:
    """Escape angle brackets that are not allowed HTML tags."""
    parts = []
    last = 0
    for m in _ALLOWED_TAG.finditer(text):
        # Escape any '<' between the last match and this one
        parts.append(text[last:m.start()].replace("<", "&lt;").replace(">", "&gt;"))
        parts.append(m.group(0))  # keep the allowed tag as-is
        last = m.end()
    parts.append(text[last:].replace("<", "&lt;").replace(">", "&gt;"))
    return "".join(parts)


def _detect_media_type(filename: str) -> str:
    if filename.endswith(".svg"):
        return "image/svg+xml"
    if filename.endswith(".png"):
        return "image/png"
    if filename.endswith(".gif"):
        return "image/gif"
    return "image/jpeg"


def generate_flashcards(
    selected_text: str,
    book_title: str,
    chapter_title: str,
    toc: str = "",
    images: list[Image] | None = None,
    feedback: str = "",
    surrounding_text: str = "",
    existing_tags: list[str] | None = None,
) -> list[Flashcard]:
    # Skip cache when feedback is present (regenerate should always produce fresh results)
    key = _cache_key(selected_text, book_title, chapter_title)
    if not feedback and key in _cache:
        return _cache[key]

    system = _build_system_prompt(book_title, chapter_title, toc, existing_tags)

    user_content: list[dict] = [*_image_blocks(images)]
    if surrounding_text:
        user_content.append({
            "type": "text",
            "text": (
                "Surrounding passage (context only - do NOT generate cards about this, "
                "use it to resolve pronouns and references in the highlight so cards stand alone):\n"
                f"{surrounding_text}"
            ),
        })
    user_content.append({"type": "text", "text": f"Highlight (generate cards from this):\n{selected_text}"})
    if feedback:
        user_content.append({"type": "text", "text": f"User feedback on previous generation — follow these instructions:\n{feedback}"})

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=8192,
        thinking={"type": "enabled", "budget_tokens": 3000},
        system=system,
        messages=[{"role": "user", "content": user_content}],
        tools=[FLASHCARD_TOOL],
        tool_choice={"type": "auto"},
    )

    tool_use = next(block for block in response.content if block.type == "tool_use")
    flashcards = [Flashcard(**card) for card in tool_use.input["flashcards"]]

    for card in flashcards:
        card.front = _escape_non_html(card.front).replace("\u2014", "-")
        card.back = _escape_non_html(card.back).replace("\u2014", "-")

    # Store in cache
    _cache[key] = flashcards

    return flashcards


def _build_system_prompt(
    book_title: str,
    chapter_title: str,
    toc: str,
    existing_tags: list[str] | None = None,
) -> list[dict]:
    system = [{
        "type": "text",
        "text": _get_prompt(),
        "cache_control": {"type": "ephemeral", "ttl": "1h"},
    }]
    if existing_tags:
        tags_str = ", ".join(existing_tags)[:3000]
        system.append({
            "type": "text",
            "text": (
                "Existing Anki tags in the user's deck. Prefer these hierarchies "
                "over inventing new ones so the deck stays coherent:\n"
                f"{tags_str}"
            ),
            "cache_control": {"type": "ephemeral"},
        })
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
    return system


def _image_blocks(images: list[Image] | None) -> list[dict]:
    if not images:
        return []
    blocks: list[dict] = [{
        "type": "text",
        "text": "Reference images from the selection (for context only, do not include <img> tags):",
    }]
    for img in images:
        blocks.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": _detect_media_type(img.filename),
                "data": img.data,
            },
        })
    return blocks


def regenerate_card(
    card: Flashcard,
    feedback: str,
    selected_text: str,
    book_title: str = "",
    chapter_title: str = "",
    toc: str = "",
    images: list[Image] | None = None,
    surrounding_text: str = "",
    existing_tags: list[str] | None = None,
) -> Flashcard:
    system = _build_system_prompt(book_title, chapter_title, toc, existing_tags)

    current = (
        f"Current card (needs improvement):\n"
        f"Type: {card.card_type}\n"
        f"Front: {card.front}\n"
        f"Back: {card.back}\n"
        f"Tags: {', '.join(card.tags)}"
    )
    instruction = (
        f"Improve ONLY this one card based on the feedback. "
        f"Return exactly ONE card by calling create_flashcards with a single-element flashcards array.\n\n"
        f"Feedback: {feedback}"
    )

    user_content: list[dict] = [*_image_blocks(images)]
    if surrounding_text:
        user_content.append({
            "type": "text",
            "text": f"Surrounding passage (context only):\n{surrounding_text}",
        })
    user_content.append({"type": "text", "text": f"Source highlight:\n{selected_text}"})
    user_content.append({"type": "text", "text": current})
    user_content.append({"type": "text", "text": instruction})

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        temperature=0.4,
        system=system,
        messages=[{"role": "user", "content": user_content}],
        tools=[FLASHCARD_TOOL],
        tool_choice={"type": "tool", "name": "create_flashcards"},
    )

    tool_use = next(block for block in response.content if block.type == "tool_use")
    cards = tool_use.input["flashcards"]
    if not cards:
        raise ValueError("No card returned")
    result = Flashcard(**cards[0])
    result.front = _escape_non_html(result.front).replace("\u2014", "-")
    result.back = _escape_non_html(result.back).replace("\u2014", "-")
    return result


def rephrase_text_stream(text: str) -> Iterator[str]:
    with client.messages.stream(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        system=[{
            "type": "text",
            "text": _get_rephrase_prompt(),
            "cache_control": {"type": "ephemeral", "ttl": "1h"},
        }],
        messages=[{"role": "user", "content": text}],
    ) as stream:
        for chunk in stream.text_stream:
            yield chunk
