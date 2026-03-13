document.getElementById('verifyBtn').addEventListener('click', async () => {
    const claim = document.getElementById('claimInput').value;
    const resultBox = document.getElementById('resultBox');
    const verdictText = document.getElementById('verdictText');
    const sourceLink = document.getElementById('sourceLink');

    if (!claim) return;

    // Show loading state
    resultBox.style.display = 'block';
    resultBox.className = 'neutral';
    verdictText.innerText = "Retrieving live data...";
    sourceLink.style.display = 'none';

    try {
        // Send the claim to your local FastAPI server
        const response = await fetch('http://127.0.0.1:8000/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ claim: claim })
        });

        const data = await response.json();

        // Update the UI based on the AI's verdict
        verdictText.innerText = `[VERDICT: ${data.verdict.toUpperCase()}]`;
        
        if (data.verdict.includes("Entailment")) {
            resultBox.className = 'entailment';
        } else if (data.verdict.includes("Contradiction")) {
            resultBox.className = 'contradiction';
        } else {
            resultBox.className = 'neutral';
        }

        if (data.source) {
            sourceLink.href = data.source;
            sourceLink.style.display = 'inline';
        }
        updateStats(data.verdict);

    } catch (error) {
        verdictText.innerText = "Error: Ensure FastAPI server is running.";
        resultBox.className = 'contradiction';
    }
});

// Load stats when the popup opens
document.addEventListener('DOMContentLoaded', () => {
    chrome.storage.local.get(['total', 'trueCount', 'falseCount'], (data) => {
        document.getElementById('stat-total').innerText = data.total || 0;
        document.getElementById('stat-true').innerText = data.trueCount || 0;
        document.getElementById('stat-false').innerText = data.falseCount || 0;
    });
});

// Helper function to update stats after a successful API call
function updateStats(verdict) {
    chrome.storage.local.get(['total', 'trueCount', 'falseCount'], (data) => {
        let total = (data.total || 0) + 1;
        let trueCount = data.trueCount || 0;
        let falseCount = data.falseCount || 0;

        if (verdict.includes("Entailment")) trueCount++;
        if (verdict.includes("Contradiction")) falseCount++;

        // Save back to storage and update UI
        chrome.storage.local.set({ total, trueCount, falseCount });
        document.getElementById('stat-total').innerText = total;
        document.getElementById('stat-true').innerText = trueCount;
        document.getElementById('stat-false').innerText = falseCount;
    });
}