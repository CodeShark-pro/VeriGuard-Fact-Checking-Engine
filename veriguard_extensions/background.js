chrome.runtime.onInstalled.addListener(() => {
    chrome.contextMenus.create({
        id: "verifyClaim",
        title: "Verify Fact: \"%s\"", 
        contexts: ["selection"]
    });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
    if (info.menuItemId === "verifyClaim") {
        const claim = info.selectionText;

        try {
            // Wait for the local AI to process the claim
            const response = await fetch('http://127.0.0.1:8000/verify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ claim: claim })
            });

            const data = await response.json();

            // Push the final verdict to the Windows Action Center
            chrome.notifications.create({
                type: "basic",
                iconUrl: "icon.png",
                title: `[${data.verdict.toUpperCase()}]`,
                message: `Source: ${data.source || 'No whitelisted source found.'}`,
                priority: 2
            });

        } catch (error) {
            chrome.notifications.create({
                type: "basic",
                iconUrl: "icon.png",
                title: "Connection Error",
                message: "Ensure your FastAPI server is running.",
                priority: 2
            });
        }
    }
});