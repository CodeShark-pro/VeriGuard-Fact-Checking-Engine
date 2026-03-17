document.getElementById('verifyBtn').addEventListener('click', async () => {
    const rawClaim = document.getElementById('claimInput').value;
    if (!rawClaim) return;

    // 1. Clean the claim to create a reliable cache key
    const cacheKey = "cache_" + rawClaim.trim().toLowerCase();

    const resultBox = document.getElementById('resultBox');
    const verdictText = document.getElementById('verdictText');
    const sourceLink = document.getElementById('sourceLink');

    // UI Loading State
    resultBox.style.display = 'block';
    resultBox.className = 'neutral';
    verdictText.innerText = "Querying Edge Cache...";
    sourceLink.style.display = 'none';

    // 2. Check the Local Storage Cache first
    chrome.storage.local.get([cacheKey], async (result) => {
        if (result[cacheKey]) {
            // CACHE HIT
            displayResult(result[cacheKey].verdict, result[cacheKey].source, true);
            return; 
        }

        // CACHE MISS: Call FastAPI
        verdictText.innerText = "Retrieving live ground-truth data...";
        try {
            const response = await fetch('http://127.0.0.1:8000/verify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ claim: rawClaim })
            });

            const data = await response.json();

            // Save to cache
            const cacheData = { verdict: data.verdict, source: data.source };
            chrome.storage.local.set({ [cacheKey]: cacheData });

            // Display result and update dashboard
            displayResult(data.verdict, data.source, false);
            updateStats(data.verdict); 

        } catch (error) {
            verdictText.innerText = "Error: Ensure FastAPI server is running.";
            resultBox.className = 'contradiction';
        }
    });
});

// Helper function to handle the UI and Notifications
function displayResult(verdict, source, isCached) {
    const resultBox = document.getElementById('resultBox');
    const verdictText = document.getElementById('verdictText');
    const sourceLink = document.getElementById('sourceLink');

    const cacheBadge = isCached ? " ⚡ (0ms Edge Cache)" : "";
    verdictText.innerText = `[VERDICT: ${verdict.toUpperCase()}]${cacheBadge}`;

    if (verdict.includes("Entailment")) {
        resultBox.className = 'entailment';
    } else if (verdict.includes("Contradiction")) {
        resultBox.className = 'contradiction';
    } else {
        resultBox.className = 'neutral';
    }

    if (source) {
        sourceLink.href = source;
        sourceLink.style.display = 'inline';
    }

    // Push the Windows/System notification
    chrome.notifications.create({
        type: "basic",
        iconUrl: "icon.png",
        title: `[${verdict.toUpperCase()}]${isCached ? ' ⚡' : ''}`,
        message: `Source: ${source || 'No whitelisted source found.'}`,
        priority: 2
    });
}

// Load stats when the popup opens
document.addEventListener('DOMContentLoaded', () => {
    chrome.storage.local.get(['total', 'trueCount', 'falseCount'], (data) => {
        document.getElementById('stat-total').innerText = data.total || 0;
        document.getElementById('stat-true').innerText = data.trueCount || 0;
        document.getElementById('stat-false').innerText = data.falseCount || 0;
    });
});

// Helper function to update dashboard stats
function updateStats(verdict) {
    chrome.storage.local.get(['total', 'trueCount', 'falseCount'], (data) => {
        let total = (data.total || 0) + 1;
        let trueCount = data.trueCount || 0;
        let falseCount = data.falseCount || 0;

        if (verdict.includes("Entailment")) trueCount++;
        if (verdict.includes("Contradiction")) falseCount++;

        chrome.storage.local.set({ total, trueCount, falseCount });
        document.getElementById('stat-total').innerText = total;
        document.getElementById('stat-true').innerText = trueCount;
        document.getElementById('stat-false').innerText = falseCount;
    });
}

// AUTO-RUN LOGIC FOR RIGHT-CLICK MENU
document.addEventListener('DOMContentLoaded', () => {
    chrome.storage.local.get(['autoVerifyClaim'], (data) => {
        if (data.autoVerifyClaim) {
            // Fill the text box
            document.getElementById('claimInput').value = data.autoVerifyClaim;
            // Delete it from storage 
            chrome.storage.local.remove('autoVerifyClaim');
            // Click the Verify button
            document.getElementById('verifyBtn').click();
        }
    });
});