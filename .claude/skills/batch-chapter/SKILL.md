---
name: batch-chapter
description: Read the chapter currently open in the debug Chrome session and batch-generate Anki flashcards for the whole chapter, pushing them straight to Anki. Use when the user says "batch the open chapter", "batch this chapter", or asks to make cards for a whole chapter they have open in Chrome.
---

# Batch a whole chapter into Anki cards

This is the batch path (whole-chapter ingestion), separate from the browser
extension (which handles highlight-while-reading). It does NOT use the FastAPI
server. You, the agent, formulate the cards; scripts only read the page and
push to Anki.

## Procedure

1. **Confirm the debug browser is up.** `curl -s http://localhost:9222/json/version`.
   If it fails, tell the user to run `batch/launch-chrome.sh`, open the chapter,
   and re-invoke. Do not try to launch Chrome yourself.

2. **Read the open chapter:**
   ```sh
   python3 batch/cdp_read.py
   ```
   Returns JSON: `{url, book_title, chapter_title, deck_name, text}`. Use
   `--match <url-substring>` if several tabs are open. Read the full `text`.

3. **Confirm scope with the user** before generating: show the detected book,
   chapter, deck_name, and rough card count you intend. One quick line.

4. **Check existing tags** so you reuse hierarchies instead of inventing new ones:
   `curl -s http://127.0.0.1:8765 -X POST -d '{"action":"getTags","version":6}'`.

5. **Formulate cards following `server/prompt.txt`** — read it and obey it
   (atomic / one fact per card, self-contained, escape non-HTML angle brackets,
   `<code>`/`<pre>` for code, no em dashes, 2-4 tags with a broad first tag and
   `::` hierarchies). Skip tool/version trivia and UI steps. Skip facts already
   covered by existing cards in the deck.

   **Match card style to the material:**
   - **Technical / reference chapters** (protocols, mechanisms, APIs, syntax,
     numbers — e.g. CCNA, Cilium, a language): card aggressively, including
     why/mechanism cards. SRS shines here.
   - **Concept / argument-heavy chapters** (management, org design, opinion —
     e.g. Team Topologies): **definitions-and-named-concepts only.** Card the
     named taxonomy, laws, and crisp definitions; SKIP soft "why"/argument cards
     whose answer is an essayish paragraph. These books are internalized by
     reading and applying, not by daily review, so a small high-signal deck beats
     a wholesale dump. When unsure whether a chapter is concept-heavy, prefer the
     stricter definitions-only default.

6. **Figures (optional but preferred for diagram-heavy chapters).** Extract them:
   ```sh
   python3 batch/cdp_images.py <scratchpad>/figs --prefix <booktoken>_
   ```
   Then **view each saved image** (Read the files) and analyze them — do NOT
   blind-attach by caption. Keep only genuine diagrams that aid recall
   (topology, architecture, process flow); skip tables-as-images, screenshots,
   and decorative/summary graphics. Put a kept figure on the relevant card's
   **back** as context via `<img src="FILENAME">` (per prompt.txt: never ask
   "what does this diagram show"). Use the prefixed filename from the manifest.

7. **Write the cards file and push:**
   ```sh
   python3 batch/add_cards.py /path/to/cards.json
   ```
   where `cards.json` is
   `{"deck_name": "<from step 2>", "cards": [ ... ], "images": [ ... ]}`.
   Each `images` entry is `{"filename": "<prefixed>", "data": "<base64 from manifest>"}`
   and only needs the figures you actually referenced. Write the file to the
   session scratchpad, not the repo. `add_notes` dedupes by front/text and
   stores media, so re-running is safe.

8. **Verify** with a `findNotes` count on the deck (and `getMediaFilesNames` if
   you attached figures) and report added/updated + any errors.

## Notes

- The deck name from `cdp_read.py` matches the extension's `_make_deck_name`,
  so batch and highlight cards land in the same hierarchy.
- O'Reilly extraction is fully supported; other reading sites fall back to
  title + main text with a flat deck name.
