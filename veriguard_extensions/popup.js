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
    verdictText.className = 'loading-pulse';
    verdictText.innerText = "Querying Edge Cache...";
    sourceLink.style.display = 'none';

    // 2. Check the Local Storage Cache first
    chrome.storage.local.get([cacheKey], async (result) => {
        if (result[cacheKey]) {
            // CACHE HIT
            displayResult(result[cacheKey].verdict, result[cacheKey].source, true, result[cacheKey].snippet);
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
            const cacheData = { verdict: data.verdict, source: data.source, snippet: data.snippet };
            chrome.storage.local.set({ [cacheKey]: cacheData });

            // Display result and update dashboard
            displayResult(data.verdict, data.source, false, data.snippet);
            updateStats(data.verdict); 

        } catch (error) {
            verdictText.innerText = "Error: Ensure FastAPI server is running.";
            resultBox.className = 'contradiction';
        }
    });
});

// Helper function to handle the UI and Notifications
function displayResult(verdict, source, isCached, snippet = null) {
    const resultBox = document.getElementById('resultBox');
    const verdictText = document.getElementById('verdictText');
    const sourceLink = document.getElementById('sourceLink');
    verdictText.className = '';
    
    // We will create a new div for the snippet if it doesn't exist yet
    let snippetBox = document.getElementById('snippetBox');
    if (!snippetBox) {
        snippetBox = document.createElement('div');
        snippetBox.id = 'snippetBox';
        snippetBox.style.marginTop = '10px';
        snippetBox.style.fontStyle = 'italic';
        snippetBox.style.color = '#ccc';
        resultBox.insertBefore(snippetBox, sourceLink);
    }

    // 1. Translate Academic Jargon to Human UX
    let friendlyVerdict = "UNKNOWN";
    let statusIcon = "❓";

    if (verdict.includes("Entailment")) {
        resultBox.className = 'entailment';
        friendlyVerdict = "VERIFIED TRUE";
        statusIcon = "✅";
    } else if (verdict.includes("Contradiction")) {
        resultBox.className = 'contradiction';
        friendlyVerdict = "DEBUNKED (FALSE)";
        statusIcon = "❌";
    } else {
        resultBox.className = 'neutral';
        friendlyVerdict = "UNVERIFIED";
        statusIcon = "⚠️";
    }

    const cacheBadge = isCached ? " ⚡ (0ms Edge Cache)" : "";
    verdictText.innerText = `${statusIcon} [${friendlyVerdict}]${cacheBadge}`;

    // 2. Display the actual "True Statement" context
    if (snippet) {
        snippetBox.innerText = `"${snippet}"`;
        snippetBox.style.display = 'block';
    } else {
        snippetBox.style.display = 'none';
    }

    // 3. Smart Domain Formatting for the Link
    if (source) {
        try {
            // Extracts "reuters.com" from a long URL
            const domainName = new URL(source).hostname.replace('www.', '');
            sourceLink.innerText = `Read full report on ${domainName}`;
            sourceLink.href = source;
            sourceLink.style.display = 'inline-block';
            sourceLink.style.marginTop = '12px';
        } catch (e) {
            sourceLink.innerText = "View Source Article";
            sourceLink.href = source;
        }
    } else {
        sourceLink.style.display = 'none';
    }

    // Push the Windows/System notification
    chrome.notifications.create({
        type: "basic",
        iconUrl: "icon.png",
        title: `${statusIcon} ${friendlyVerdict} ${isCached ? '⚡' : ''}`,
        message: source ? `Source: ${new URL(source).hostname.replace('www.', '')}` : 'No whitelisted source found.',
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