# VeriGuard: Autonomous Claim Verification via Retrieval-Augmented Architecture

[cite_start] VeriGuard is an automated engine that actively searches for trusted live data to verify claims[cite: 7]. Built to combat zero-day disinformation, it replaces standard text generation with a deterministic Retrieval-Augmented Classification (RAC) pipeline. [cite_start] Instead of generating text like a standard RAG model, it strictly classifies a claim as mathematically true or false[cite: 8].

## 🚨 The Problem

[cite_start]The penetration of AI-generated disinformation poses a severe challenge to digital information integrity[cite: 4]. [cite_start]Standard machine learning classifiers rely on static training data and fail against zero-day events[cite: 5, 13]. [cite_start]Meanwhile, probabilistic Large Language Models (LLMs) are prone to hallucinating fake sources when tasked with fact-checking[cite: 14].

## 💡 The Solution

VeriGuard introduces a zero-cost Open-Source Intelligence (OSINT) pipeline that completely drops the "Generation" aspect of AI. [cite_start]The system integrates a FastAPI backend that extracts factual claims using spaCy, queries a whitelisted Open-Source Intelligence (OSINT) search API for real-time data, and applies a highly efficient Cross-Encoder Natural Language Inference (NLI) model (DeBERTa-v3) to mathematically determine textual entailment[cite: 9].

## ✨ Key Features

- [cite_start]**Zero-Day OSINT Retrieval:** Bypasses static memory by actively scraping real-time ground-truth data from a strict domain whitelist (e.g., Reuters, PIB, Wikipedia)[cite: 19].
- [cite_start]**Hallucination-Free Verification:** Uses a localized Natural Language Inference (NLI) model to calculate mathematical entailment[cite: 20].
- [cite_start]**Strict Boolean Outputs:** Returns absolute, deterministic verdicts (Entailment, Contradiction, Neutral) alongside the exact corroborating URL[cite: 20, 21].
- **Edge-Level Chrome Extension:** Integrates directly into the browser via a Manifest V3 extension, featuring right-click context menu verification and push notifications.
- **Client-Side Caching:** Hashes and stores verified claims locally (`chrome.storage.local`) to serve repeat queries in 0ms without hitting the backend server.

## 🛠️ Technology Stack

- [cite_start]**Backend:** Python, FastAPI (Asynchronous framework) [cite: 26]
- **AI/Machine Learning:** Hugging Face `sentence-transformers`, DeBERTa-v3-small Cross-Encoder
- **Natural Language Processing (NLP):** `spaCy` (for factual extraction)
- **Search / Scraping:** `duckduckgo-search` (Zero-cost pipeline)
- **Frontend:** HTML/CSS/JS, Chrome Manifest V3 API

## ⚙️ Local Installation & Setup

### 1. Start the Backend API

Ensure you have Python installed, then install the required dependencies:

```bash
pip install fastapi uvicorn spacy sentence-transformers duckduckgo-search
python -m spacy download en_core_web_sm
```
