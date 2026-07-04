chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "generate-flashcards",
    title: "Generate Flashcards",
    contexts: ["selection"],
    documentUrlPatterns: [
      "https://learning.oreilly.com/*",
      "https://learn.microsoft.com/*",
      "https://git-scm.com/*",
    ],
  });
});

async function sendToActiveTab(msg) {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) return;
  try {
    await chrome.tabs.sendMessage(tab.id, msg);
  } catch (e) {
    console.error("flshmkr: sendMessage failed", e);
  }
}

chrome.action.onClicked.addListener(async (tab) => {
  if (!tab) return;
  try {
    await chrome.tabs.sendMessage(tab.id, { action: "toggleSidebar" });
  } catch (e) {
    console.error("flshmkr: toggle failed (is the page supported?)", e);
  }
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== "generate-flashcards") return;
  if (!tab) return;
  try {
    await chrome.tabs.sendMessage(tab.id, {
      action: "generateFromSelection",
      selectionText: info.selectionText || "",
    });
  } catch (e) {
    console.error("flshmkr: generate trigger failed", e);
  }
});

chrome.commands.onCommand.addListener(async (command) => {
  if (command === "toggle-sidebar") {
    await sendToActiveTab({ action: "toggleSidebar" });
    return;
  }

  if (command !== "rephrase-selection") return;

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) return;

  try {
    const { selectedText } = await chrome.tabs.sendMessage(tab.id, {
      action: "getSelectedText",
    });
    if (!selectedText) return;

    chrome.tabs.sendMessage(tab.id, { action: "showRephraseLoading" });

    const resp = await fetch("http://127.0.0.1:8000/rephrase", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: selectedText }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(err.detail || resp.statusText);
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      if (chunk) {
        chrome.tabs.sendMessage(tab.id, { action: "appendRephrase", chunk });
      }
    }
    chrome.tabs.sendMessage(tab.id, { action: "finishRephrase" });
  } catch (e) {
    console.error("flshmkr: rephrase failed", e);
    chrome.tabs.sendMessage(tab.id, {
      action: "showRephraseError",
      error: e.message,
    });
  }
});
