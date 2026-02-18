const SERVER = "http://127.0.0.1:8000";

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "generate-flashcards",
    title: "Generate Flashcards",
    contexts: ["selection"],
    documentUrlPatterns: [
      "https://learning.oreilly.com/*",
      "https://learn.microsoft.com/*",
    ],
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== "generate-flashcards") return;

  try {
    const response = await chrome.tabs.sendMessage(tab.id, {
      action: "getContext",
    });

    // Use selection from context menu if content script missed it
    if (!response.selected_text && info.selectionText) {
      response.selected_text = info.selectionText;
    }

    await chrome.storage.local.set({ pendingContext: response });
    chrome.action.openPopup();
  } catch (e) {
    console.error("flshmkr: failed to get context", e);
  }
});

chrome.commands.onCommand.addListener(async (command) => {
  if (command !== "rephrase-selection") return;

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) return;

  try {
    // Get selected text from the content script
    const { selectedText } = await chrome.tabs.sendMessage(tab.id, {
      action: "getSelectedText",
    });
    if (!selectedText) return;

    chrome.tabs.sendMessage(tab.id, { action: "showRephraseLoading" });

    const resp = await fetch(`${SERVER}/rephrase`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: selectedText }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(err.detail || resp.statusText);
    }

    const data = await resp.json();
    chrome.tabs.sendMessage(tab.id, {
      action: "showRephrase",
      rephrased_text: data.rephrased_text,
    });
  } catch (e) {
    console.error("flshmkr: rephrase failed", e);
    chrome.tabs.sendMessage(tab.id, {
      action: "showRephrase",
      error: e.message,
    });
  }
});
