const claimInput = document.getElementById('claimInput');
const clearBtn = document.getElementById('clearBtn');

claimInput.addEventListener('input', () => {
    clearBtn.style.display = claimInput.value.trim().length > 0 ? 'flex' : 'none';
});

clearBtn.addEventListener('click', () => {
    claimInput.value = '';
    clearBtn.style.display = 'none';
    document.getElementById('resultBox').style.display = 'none'; 
    document.getElementById('aiComparisonBox').style.display = 'none';
    claimInput.focus(); 
});

document.getElementById('verifyBtn').addEventListener('click', async () => {
    const rawClaim = document.getElementById('claimInput').value;
    if (!rawClaim) return;

    const cacheKey = "cache_" + rawClaim.trim().toLowerCase();

    const resultBox = document.getElementById('resultBox');
    const aiBox = document.getElementById('aiComparisonBox');
    const verdictText = document.getElementById('verdictText');
    const sourceLink = document.getElementById('sourceLink');

    resultBox.style.display = 'block';
    aiBox.style.display = 'none';
    resultBox.className = 'neutral';
    verdictText.className = 'loading-pulse';
    verdictText.innerText = "Executing parallel pipeline...";
    sourceLink.style.display = 'none';

    chrome.storage.local.get([cacheKey], async (result) => {
        if (result[cacheKey]) {
            displayResult(result[cacheKey].veriguard, result[cacheKey].secondary_ai, true);
            return; 
        }

        verdictText.innerText = "Retrieving ground-truth & calling Gemini...";
        try {
            const response = await fetch('http://localhost:8000/verify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ claim: rawClaim })
            });

            const data = await response.json();

            chrome.storage.local.set({ [cacheKey]: data });

            displayResult(data.veriguard, data.secondary_ai, false);
            updateStats(data.veriguard.verdict); 

        } catch (error) {
            verdictText.innerText = "Error: Ensure FastAPI server is running.";
            resultBox.className = 'contradiction';
        }
    });
});

function displayResult(vgData, aiData, isCached) {
    const resultBox = document.getElementById('resultBox');
    const verdictText = document.getElementById('verdictText');
    const sourceLink = document.getElementById('sourceLink');
    const aiBox = document.getElementById('aiComparisonBox');
    const aiVerdictText = document.getElementById('aiVerdictText');
    const aiReasonText = document.getElementById('aiReasonText');
    
    verdictText.className = '';

    let snippetBox = document.getElementById('snippetBox');
    if (!snippetBox) {
        snippetBox = document.createElement('div');
        snippetBox.id = 'snippetBox';
        snippetBox.style.marginTop = '10px';
        snippetBox.style.fontStyle = 'italic';
        snippetBox.style.color = '#ccc';
        resultBox.insertBefore(snippetBox, sourceLink);
    }

    let friendlyVerdict = "UNKNOWN";
    let statusIcon = "❓";

    if (vgData.verdict.includes("Entailment")) {
        resultBox.className = 'entailment';
        friendlyVerdict = "VERIFIED TRUE";
        statusIcon = "✅";
    } else if (vgData.verdict.includes("Contradiction")) {
        resultBox.className = 'contradiction';
        friendlyVerdict = "DEBUNKED (FALSE)";
        statusIcon = "❌";
    } else if (vgData.verdict.includes("Invalid")) {
        resultBox.className = 'neutral'; 
        resultBox.style.borderColor = "#ffb74d"; 
        resultBox.style.color = "#ffb74d";
        friendlyVerdict = "FORMAT ERROR";
        statusIcon = "🛑";
    } else {
        resultBox.className = 'neutral';
        friendlyVerdict = "UNVERIFIED";
        statusIcon = "⚠️";
    }

    const cacheBadge = isCached ? " ⚡ (0ms Edge Cache)" : "";
    verdictText.innerText = `${statusIcon} [${friendlyVerdict}]${cacheBadge}`;

    if (vgData.snippet) {
        snippetBox.innerText = `"${vgData.snippet}"`;
        snippetBox.style.display = 'block';
    } else {
        snippetBox.style.display = 'none';
    }

    if (vgData.source) {
        try {
            const domainName = new URL(vgData.source).hostname.replace('www.', '');
            sourceLink.innerText = `Read full report on ${domainName}`;
            sourceLink.href = vgData.source;
            sourceLink.style.display = 'inline-block';
            sourceLink.style.marginTop = '12px';
        } catch (e) {
            sourceLink.innerText = "View Source Article";
            sourceLink.href = vgData.source;
        }
    } else {
        sourceLink.style.display = 'none';
    }

    if (aiData) {
        aiBox.style.display = 'block';
        
        let aiFriendly = "UNVERIFIED";
        let aiColor = "#e0e0e0";
        if (aiData.verdict.includes("TRUE")) {
            aiFriendly = "TRUE";
            aiColor = "#81c784";
        } else if (aiData.verdict.includes("FALSE")) {
            aiFriendly = "FALSE";
            aiColor = "#e57373";
        }
        
        aiVerdictText.innerText = aiFriendly;
        aiVerdictText.style.color = aiColor;
        aiReasonText.innerText = aiData.reason || "";
    }

    chrome.notifications.create({
        type: "basic",
        iconUrl: "icon.png",
        title: `${statusIcon} ${friendlyVerdict} ${isCached ? '⚡' : ''}`,
        message: vgData.source ? `Source: ${new URL(vgData.source).hostname.replace('www.', '')}` : 'No whitelisted source found.',
        priority: 2
    });
}

document.addEventListener('DOMContentLoaded', () => {
    chrome.storage.local.get(['total', 'trueCount', 'falseCount'], (data) => {
        document.getElementById('stat-total').innerText = data.total || 0;
        document.getElementById('stat-true').innerText = data.trueCount || 0;
        document.getElementById('stat-false').innerText = data.falseCount || 0;
    });
});

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

document.addEventListener('DOMContentLoaded', () => {
    chrome.storage.local.get(['autoVerifyClaim'], (data) => {
        if (data.autoVerifyClaim) {
            document.getElementById('claimInput').value = data.autoVerifyClaim;
            document.getElementById('clearBtn').style.display = 'flex'; 
            chrome.storage.local.remove('autoVerifyClaim');
            document.getElementById('verifyBtn').click();
        }
    });
});