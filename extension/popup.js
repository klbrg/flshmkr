const SERVER = "http://127.0.0.1:8000";

const $ = (sel) => document.querySelector(sel);
const show = (id) => {
  document.querySelectorAll(".state").forEach((el) => el.classList.add("hidden"));
  $(`#${id}`).classList.remove("hidden");
};

const DEFAULT_FEEDBACK = "shorter and simpler question/answer";

let flashcards = [];
let images = [];
let lastContext = null;
// Per-card image inclusion: cardImages[cardIndex][imageIndex] = true/false
let cardImages = [];

// --- Card rendering ---

function renderCards() {
  const container = $("#cards");
  container.innerHTML = "";

  flashcards.forEach((card, i) => {
    const frontLabel = card.card_type === "cloze" ? "Text" : "Front";
    const backLabel = card.card_type === "cloze" ? "Extra" : "Back";

    const div = document.createElement("div");
    div.className = "card";
    div.innerHTML = `
      <div class="card-header">
        <select data-i="${i}">
          <option value="basic" ${card.card_type === "basic" ? "selected" : ""}>Basic</option>
          <option value="cloze" ${card.card_type === "cloze" ? "selected" : ""}>Cloze</option>
        </select>
        <button data-del="${i}" title="Delete card">&times;</button>
      </div>
      <div class="field-label">${frontLabel}</div>
      <textarea data-field="front" data-i="${i}">${card.front}</textarea>
      <div class="field-label">${backLabel}</div>
      <textarea data-field="back" data-i="${i}">${card.back}</textarea>
    `;
    if (images.length) {
      const imgDiv = document.createElement("div");
      imgDiv.className = "card-images";
      images.forEach((img, j) => {
        const label = document.createElement("label");
        label.className = "image-toggle";
        const cb = document.createElement("input");
        cb.type = "checkbox";
        cb.checked = cardImages[i]?.[j] ?? true;
        cb.addEventListener("change", () => { cardImages[i][j] = cb.checked; });
        const thumb = document.createElement("img");
        thumb.src = `data:image/png;base64,${img.data}`;
        thumb.title = img.filename;
        label.appendChild(cb);
        label.appendChild(thumb);
        imgDiv.appendChild(label);
      });
      div.appendChild(imgDiv);
    }
    container.appendChild(div);
  });

  // Bind events
  container.querySelectorAll("select").forEach((sel) =>
    sel.addEventListener("change", (e) => {
      flashcards[e.target.dataset.i].card_type = e.target.value;
      renderCards();
    })
  );
  container.querySelectorAll("textarea").forEach((ta) =>
    ta.addEventListener("input", (e) => {
      flashcards[e.target.dataset.i][e.target.dataset.field] = e.target.value;
    })
  );
  container.querySelectorAll("[data-del]").forEach((btn) =>
    btn.addEventListener("click", (e) => {
      const idx = parseInt(e.target.dataset.del);
      flashcards.splice(idx, 1);
      cardImages.splice(idx, 1);
      renderCards();
    })
  );
}

// --- Image previews ---

function renderImages() {
  const container = $("#image-previews");
  container.innerHTML = "";
  if (!images.length) {
    container.classList.add("hidden");
    return;
  }
  container.classList.remove("hidden");
  images.forEach((img) => {
    const el = document.createElement("img");
    el.src = `data:image/png;base64,${img.data}`;
    el.title = img.filename;
    container.appendChild(el);
  });
}

// --- Server calls ---

async function generateCards(context) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);

  try {
    const resp = await fetch(`${SERVER}/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(context),
      signal: controller.signal,
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `Server error ${resp.status}`);
    }
    return resp.json();
  } catch (e) {
    if (e.name === "AbortError") throw new Error("Request timed out — try again");
    throw e;
  } finally {
    clearTimeout(timeout);
  }
}

async function sendToAnki() {
  // Append selected image tags to card backs
  const cardsToSend = flashcards.map((card, i) => {
    const imgTags = images
      .filter((_, j) => cardImages[i]?.[j])
      .map((img) => `<img src="${img.filename}">`)
      .join("");
    if (!imgTags) return card;
    return { ...card, back: card.back + imgTags };
  });

  const resp = await fetch(`${SERVER}/add-to-anki`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      flashcards: cardsToSend,
      deck_name: $("#deck-name").value,
      images,
    }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `Server error ${resp.status}`);
  }
  return resp.json();
}

// --- Main flow ---

async function init() {
  const { pendingContext } = await chrome.storage.local.get("pendingContext");

  if (!pendingContext?.selected_text) {
    show("empty");
    return;
  }

  // Clear pending data and badge
  await chrome.storage.local.remove("pendingContext");
  chrome.action.setBadgeText({ text: "" });

  show("loading");
  lastContext = pendingContext;

  try {
    const result = await generateCards(lastContext);
    flashcards = result.flashcards;
    images = result.images || [];
    cardImages = flashcards.map(() => images.map(() => true));
    $("#book-title").value = lastContext.book_title || "";
    $("#chapter-title").value = lastContext.chapter_title || "";
    $("#deck-name").value = result.deck_name;
    renderCards();
    renderImages();
    $("#feedback").value = DEFAULT_FEEDBACK;
    show("preview");
  } catch (e) {
    $("#confirm-msg").textContent = `Error: ${e.message}`;
    $("#confirm-msg").classList.add("error-text");
    show("confirmation");
  }
}

// --- Event listeners ---

$("#add-card").addEventListener("click", () => {
  flashcards.push({ card_type: "basic", front: "", back: "", tags: [] });
  cardImages.push(images.map(() => true));
  renderCards();
});

$("#regenerate").addEventListener("click", async () => {
  if (!lastContext) return;
  const feedback = $("#feedback").value.trim();
  const ctx = { ...lastContext };
  if (feedback) ctx.feedback = feedback;

  show("loading");
  try {
    const result = await generateCards(ctx);
    flashcards = result.flashcards;
    images = result.images || [];
    cardImages = flashcards.map(() => images.map(() => true));
    renderCards();
    renderImages();
    $("#feedback").value = DEFAULT_FEEDBACK;
    show("preview");
  } catch (e) {
    $("#confirm-msg").textContent = `Error: ${e.message}`;
    $("#confirm-msg").classList.add("error-text");
    show("confirmation");
  }
});

$("#send-to-anki").addEventListener("click", async () => {
  const btn = $("#send-to-anki");
  btn.disabled = true;
  btn.textContent = "Sending…";

  try {
    const result = await sendToAnki();
    let msg = `Added ${result.added} card(s) to Anki.`;
    if (result.errors.length) {
      msg += "\n" + result.errors.join("\n");
    }
    $("#confirm-msg").textContent = msg;
    $("#confirm-msg").classList.remove("error-text");
    show("confirmation");
  } catch (e) {
    btn.disabled = false;
    btn.textContent = "Send to Anki";
    $("#confirm-msg").textContent = `Error: ${e.message}`;
    $("#confirm-msg").classList.add("error-text");
    show("confirmation");
  }
});

$("#done").addEventListener("click", () => window.close());

init();
