// Create the right-click menu
chrome.runtime.onInstalled.addListener(() => {
    chrome.contextMenus.create({
        id: "verifyClaim",
        title: "Verify Fact: \"%s\"", 
        contexts: ["selection"]
    });
});

// Listen for the right-click
chrome.contextMenus.onClicked.addListener((info, tab) => {
    if (info.menuItemId === "verifyClaim") {
        // 1. Save the highlighted text to local storage
        chrome.storage.local.set({ "autoVerifyClaim": info.selectionText }, () => {
            // 2. Programmatically force the extension popup to open!
            chrome.action.openPopup();
        });
    }
});