---
name: batch-book
description: Card a WHOLE prose book into Anki from a downloaded/extracted source (Legimus/MTM DAISY audiobook, a local .epub, or O'Reilly) — split into chapters, fan out carding agents in waves, push and sync per wave. Use when the user gives a whole book (a Legimus book id like CAxxxxx, an .epub in Downloads, an O'Reilly URL, or "card this book") and wants the whole thing, not the single chapter open in Chrome.
---

# Batch a whole prose book into Anki

This is the whole-book path. It is separate from `batch-chapter` (the single chapter open in the
debug Chrome) and from math (use `flashcard-math` + the SymPy gate). You extract the text once,
then fan out one carding agent per chapter in waves, pushing and syncing after each wave.

## Procedure

1. **Extract the full book text.** Method depends on the source — see the `web-extraction-pipeline`
   memory for the exact recipe:
   - **Legimus / MTM** (`webbspelaren.mtm.se/#book-player?book=<ID>`): the player is audio-first
     and shows no prose, but the full text is fetchable from the DAISY content endpoint
     (`dodp-prod.azurewebsites.net/resource/<ID>?dodSessionId=<SID>&resourcePath=<file>`). Read the
     `dodSessionId` from the open reader tab; fetch `ncc.html` for the TOC, then the single content
     HTML. `curl` it with a `Referer: https://webbspelaren.mtm.se/` header.
   - **Local `.epub`** (e.g. `~/Downloads`): `unzip`, find the `.opf`, walk the `<spine>` → chapter
     XHTML files. Real data in newer apkg-style is elsewhere; for epub the spine is authoritative.
   - **O'Reilly**: content API from an authenticated tab (handles lazy-load / split chapters).
   Save the FULL text to the session scratchpad.

2. **Split into per-chapter text files** in the scratchpad (by heading inner text). Get the real
   chapter titles; skip front/back matter (cover, colophon, index/register, "Innehåll").

3. **Confirm scope with the user** — book title, chapter count, deck name, rough card total. For a
   large or version-sensitive book (tax/law), confirm depth (full vs curated) and, for changing
   figures, verify current values (WebSearch) and pass them into the agent briefs. Do NOT silently
   dump 1500 cards.

4. **Card in waves of ~5-6 chapters** (see `batch-concurrency` memory — ~5/wave; more starves the
   shared tools). Spawn one **`flashcard-prose`** agent per chapter, each reading its local text
   file, writing a validated cards JSON (deck verbatim, tags, NO push). Give each a per-chapter
   topic emphasis and the card language (match the source/user). `general-purpose` also works if
   `flashcard-prose` is unavailable.

5. **Push each wave, then sync.** Via AnkiConnect: `createDeck`, then `addNote` per card
   (basic → model `flshmkr Basic`, fields Front/Back; cloze → `flshmkr Cloze`, fields Text/Extra;
   `options.allowDuplicate:false`), then `sync`. Prefer inline `addNote` over `batch/add_cards.py`
   for per-wave pushes — `add_cards.py`'s findNotes dedup breaks on LaTeX backslashes. Report the
   per-chapter counts for the wave.

6. **Repeat** for the remaining waves. Report the book total when done.

## Conventions
- Deck: `Books::<Title>::Kapitel NN. <Titel>` (zero-padded chapter number). First tag = the broad
  subject (e.g. `vanor`, `förhandling`, `allmänbildning`, `aktiebolag`). See `anki-deck-conventions`.
- Cards are original paraphrases; never name the book/author; obey `server/prompt.txt`.
- **Sync after EVERY wave** so progress is safe across devices, and so a crash never loses a wave.

## Keeping the collection sustainable
A big book can add 1000+ cards. To avoid overwhelming the daily queue, keep only 1-2 decks "active"
(~10 new cards/day, review cap ~120 → 10-15 min/day) and archive the rest **suspended** under an
`Arkiv::` parent. New cards only surface when you study their deck, so a parked deck is inert.
Rotate one deck in (unsuspend + set new/day) when an active one matures. Adding a note field
(e.g. an L1 gloss) changes the schema and forces a one-way full sync — the user must click Sync in
the GUI and choose "Upload to AnkiWeb" once.
