# VeriGuard: Autonomous Claim Verification via Retrieval-Augmented Architecture

 VeriGuard is an automated engine that actively searches for trusted live data to verify claims. Built to combat zero-day disinformation, it replaces standard text generation with a deterministic Retrieval-Augmented Classification (RAC) pipeline.Instead of generating text like a standard RAG model, it strictly classifies a claim as mathematically true or false[cite: 8].

## The Problem

The penetration of AI-generated disinformation poses a severe challenge to digital information integrity[cite: 4]. Standard machine learning classifiers rely on static training data and fail against zero-day events[cite: 5, 13]. Meanwhile, probabilistic Large Language Models (LLMs) are prone to hallucinating fake sources when tasked with fact-checking.

## The Solution

VeriGuard introduces a zero-cost Open-Source Intelligence (OSINT) pipeline that completely drops the "Generation" aspect of AI. The system integrates a FastAPI backend that extracts factual claims using spaCy, queries a whitelisted Open-Source Intelligence (OSINT) search API for real-time data, and applies a highly efficient Cross-Encoder Natural Language Inference (NLI) model (DeBERTa-v3) to mathematically determine textual entailment.

## Key Features

- **Zero-Day OSINT Retrieval:** Bypasses static memory by actively scraping real-time ground-truth data from a strict domain whitelist (e.g., Reuters, PIB, Wikipedia)[cite: 19].
- **Hallucination-Free Verification:** Uses a localized Natural Language Inference (NLI) model to calculate mathematical entailment[cite: 20].
- **Strict Boolean Outputs:** Returns absolute, deterministic verdicts (Entailment, Contradiction, Neutral) alongside the exact corroborating URL[cite: 20, 21].
- **Edge-Level Chrome Extension:** Integrates directly into the browser via a Manifest V3 extension, featuring right-click context menu verification and push notifications.
- **Client-Side Caching:** Hashes and stores verified claims locally (`chrome.storage.local`) to serve repeat queries in 0ms without hitting the backend server.

## Technology Stack

- **Backend:** Python, FastAPI (Asynchronous framework) [cite: 26]
- **AI/Machine Learning:** Hugging Face `sentence-transformers`, DeBERTa-v3-small Cross-Encoder
- **Natural Language Processing (NLP):** `spaCy` (for factual extraction)
- **Search / Scraping:** `duckduckgo-search` (Zero-cost pipeline)
- **Frontend:** HTML/CSS/JS, Chrome Manifest V3 API

## Local Installation & Setup

### 1. Start the Backend API

Ensure you have Python installed, then install the required dependencies:

```bash
pip install fastapi uvicorn spacy sentence-transformers duckduckgo-search motor python-dotenv httpx beautifulsoup4
python -m spacy download en_core_web_sm
```

Run the FastAPI server:

```bash
uvicorn main:app --reload
```

### 2. Load the Chrome Extension

1. Open Google Chrome or any Chromium-based browser (Edge, Brave).
2. Navigate to `chrome://extensions/` in your address bar.
3. Turn on **Developer mode** using the toggle in the top right corner.
4. Click the **Load unpacked** button.
5. Select the `veriguard_extensions` folder located within this repository.

### 3. How to Use

1. **Find a Claim:** Browse any article, social media post, or webpage.
2. **Highlight:** Select the factual claim you want to verify.
3. **Right-Click:** Right-click the highlighted text to open the browser context menu.
4. **Verify:** Select the **"Verify Claim"** option from the menu.
5. **Results:** A notification or pop-up will appear displaying the verdict (True/False/Unverified), context, and the corroborating source URL.
