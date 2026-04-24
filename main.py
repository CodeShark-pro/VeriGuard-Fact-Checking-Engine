import os
from fastapi import FastAPI
from pydantic import BaseModel
from duckduckgo_search import DDGS
import warnings
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import httpx
import re
import asyncio

load_dotenv()

MONGO_DETAILS = os.getenv("MONGO_URI", "").replace('"', '').replace("'", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").replace('"', '').replace("'", "").strip()
HF_API_KEY = os.getenv("HF_API_KEY", "").strip()

if not MONGO_DETAILS:
    MONGO_DETAILS = "mongodb://localhost:27017"

client = AsyncIOMotorClient(MONGO_DETAILS)
database = client.veriguard
claim_collection = database.claims

warnings.filterwarnings("ignore")

app = FastAPI(title="VeriGuard API", description="Autonomous Fact-Checking Engine (HF Edge)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

whitelist = [
    "reuters.com", "apnews.com", "afp.com", "bloomberg.com", "upi.com",
    "bbc.com", "bbc.co.uk", "npr.org", "nytimes.com", "wsj.com",
    "theguardian.com", "ft.com", "aljazeera.com", "washingtonpost.com",
    "thehindu.com", "indianexpress.com", "timesofindia.indiatimes.com",
    "ndtv.com", "hindustantimes.com", "livemint.com", "business-standard.com",
    "theprint.in", "scroll.in", "indiatoday.in", "moneycontrol.com",
    "snopes.com", "politifact.com", "factcheck.org", "fullfact.org",
    "leadstories.com", "altnews.in", "boomlive.in", "newschecker.in",
    "nature.com", "science.org", "thelancet.com", "nejm.org",
    "ieee.org", "smithsonianmag.com", "nationalgeographic.com",
    "en.wikipedia.org", "britannica.com", "investopedia.com", "history.com",
    "pib.gov.in", "who.int", "un.org", "worldbank.org", "imf.org",
    "nasa.gov", "cdc.gov", "rbi.org.in",
    "ourworldindata.org", "pewresearch.org", "statista.com", "gallup.com",
    "isro.gov.in", "eci.gov.in", "uidai.gov.in", "india.gov.in",
    "eff.org", "cisa.gov", "wired.com", "techcrunch.com",
    "dw.com", "france24.com", "pbs.org", "cbc.ca", 
    "nih.gov", "mayoclinic.org", "clevelandclinic.org"
]

@app.on_event("startup")
def startup_event():
    print("VeriGuard Server Online! Routing NLP to Hugging Face Inference API.")

class ClaimRequest(BaseModel):
    claim: str

def is_question(text: str) -> bool:
    text = text.strip().lower()
    if text.endswith('?'):
        return True
    question_patterns = r"^(who|what|where|when|why|how|is|are|do|does|did|can|could|should|would|will)\b"
    if re.match(question_patterns, text):
        return True
    return False

async def call_hf_deberta(snippet: str, claim: str):
    """Hits the Hugging Face API for the DeBERTa-v3 Cross-Encoder."""
    if not HF_API_KEY:
        return "Neutral (Unverified)"

    url = "https://api-inference.huggingface.co/models/cross-encoder/nli-deberta-v3-small"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    
    # HF format for cross-encoder sentence pairs
    payload = {"inputs": {"text": snippet, "text_pair": claim}}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            data = response.json()

        # Handle HF "Cold Start" (if the model is asleep on their servers)
        if isinstance(data, dict) and "error" in data:
            print(f"HF API Warming Up: {data.get('estimated_time', 'Unknown')} seconds.")
            return "Neutral (Unverified)"

        # Find the label with the highest mathematical score
        predictions = data[0] if isinstance(data, list) else data
        best_prediction = max(predictions, key=lambda x: x['score'])
        label = best_prediction['label'].lower()

        # Map DeBERTa-v3 output labels to VeriGuard UI labels
        if "entail" in label or label == "label_1":
            return "Entailment (True)"
        elif "contradict" in label or label == "label_0":
            return "Contradiction (False)"
        else:
            return "Neutral (Unverified)"

    except Exception as e:
        print(f"HF API Error: {e}")
        return "Neutral (Unverified)"

async def check_global_cache(claim_text: str):
    try:
        cached_result = await claim_collection.find_one({"claim": claim_text})
        if cached_result:
            cached_result["_id"] = str(cached_result["_id"])
        return cached_result
    except Exception as e:
        print(f"WARNING: Cache read failed: {e}")
        return None

async def save_to_cache(claim_text: str, verdict: str, source_url: str, snippet: str, ai_verdict: str, ai_reason: str):
    try:
        new_entry = {
            "claim": claim_text,
            "verdict": verdict,
            "source": source_url,
            "snippet": snippet,
            "ai_verdict": ai_verdict,
            "ai_reason": ai_reason
        }
        await claim_collection.insert_one(new_entry)
        print(f"SUCCESS: Saved claim to MongoDB: {claim_text[:50]}...")
    except Exception as e:
        print(f"ERROR: Failed to save to MongoDB: {e}")

async def scrape_article_text(url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            response = await client.get(url, headers=headers, follow_redirects=True)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                paragraphs = [p.get_text().strip() for p in soup.find_all('p') if len(p.get_text().strip()) > 40]
                extracted_text = " ".join(paragraphs[:3])
                return extracted_text
    except Exception:
        return ""
    return ""


async def call_gemini_ai(claim: str):
    if not GEMINI_API_KEY:
        return {"verdict": "UNVERIFIED", "reason": "API key missing in .env"}
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
        prompt = f"You are a strict fact-checker. Respond EXACTLY with VERDICT | REASON. VERDICT must be TRUE, FALSE, or UNVERIFIED. REASON is one sentence. NO markdown. Claim: {claim}"
        
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            
        if response.status_code != 200:
            if response.status_code in [502, 503, 504]:
                return {"verdict": "UNVERIFIED", "reason": "Gemini API service is temporarily unavailable."}
            return {"verdict": "UNVERIFIED", "reason": f"Gemini API Error (HTTP {response.status_code})"}
            
        data = response.json()
        
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError):
            return {"verdict": "UNVERIFIED", "reason": "Blocked by Gemini Safety Filters"}
            
        text = text.replace("**", "").replace("`", "").replace("[", "").replace("]", "")
        
        if '|' in text:
            parts = text.split('|', 1)
        elif '-' in text:
            parts = text.split('-', 1)
        else:
            parts = text.split(' ', 1)
            
        if len(parts) >= 2:
            v = parts[0].strip().upper()
            r = parts[1].strip()
            if "TRUE" in v: v = "TRUE"
            elif "FALSE" in v: v = "FALSE"
            else: v = "UNVERIFIED"
            return {"verdict": v, "reason": r}
            
        return {"verdict": "UNVERIFIED", "reason": "Unparseable AI Output"}
    except Exception as e:
        return {"verdict": "UNVERIFIED", "reason": f"Request Failed"}


async def run_veriguard_pipeline(claim: str, normalized_claim: str):
    snippet = ""
    source_url = ""
    search_keywords = claim

    with DDGS() as ddgs:
        results = list(ddgs.text(search_keywords, max_results=10))
        for res in results:
            url = res.get('href', '').lower()
            if any(trusted in url for trusted in whitelist):
                source_url = res.get('href', '')
                scraped_text = await scrape_article_text(source_url)
                if scraped_text and len(scraped_text) > 50:
                    snippet = scraped_text
                else:
                    snippet = res.get('body', '')
                break

    if not snippet:
        return {
            "verdict": "Neutral (Unverified)",
            "source": None,
            "snippet": "No data found in whitelisted sources."
        }

    # Replaced local model.predict() with API call
    winner = await call_hf_deberta(snippet, claim)

    return {
        "verdict": winner,
        "source": source_url,
        "snippet": snippet
    }


@app.post("/verify")
async def verify_claim(request: ClaimRequest):
    normalized_claim = request.claim.strip().lower()
    
    if is_question(normalized_claim):
        return {
            "veriguard": {
                "verdict": "Invalid (Not a Claim)",
                "source": None,
                "snippet": "VeriGuard checks factual statements, not questions. Please rewrite this as a declarative claim."
            },
            "secondary_ai": {
                "verdict": "N/A",
                "reason": "Input is a question."
            },
            "is_cached_globally": False
        }

    cached_data = await check_global_cache(normalized_claim)
    if cached_data:
        print(f"CACHE HIT: Found result for '{normalized_claim[:30]}...'")
        return {
            "veriguard": {
                "verdict": cached_data["verdict"],
                "source": cached_data["source"],
                "snippet": cached_data["snippet"],
            },
            "secondary_ai": {
                "verdict": cached_data.get("ai_verdict", "UNVERIFIED"),
                "reason": cached_data.get("ai_reason", "Cached before AI integration.")
            },
            "is_cached_globally": True
        }

    print(f"DEBUG: Starting pipeline for '{request.claim[:30]}...'")
    veriguard_task = run_veriguard_pipeline(request.claim, normalized_claim)
    gemini_task = call_gemini_ai(request.claim)

    vg_result, ai_result = await asyncio.gather(veriguard_task, gemini_task)
    print(f"DEBUG: Pipeline completed. Veriguard: {vg_result['verdict']}, AI: {ai_result['verdict']}")

    # If the NLI model is uncertain (Neutral/Unverified), use Gemini as a fallback.
    # Map Gemini's binary TRUE/FALSE back to the NLI label vocabulary so the
    # frontend receives a consistent verdict string.
    if vg_result["verdict"] == "Neutral (Unverified)":
        gemini_verdict = ai_result.get("verdict", "UNVERIFIED")
        if gemini_verdict == "FALSE":
            vg_result["verdict"] = "Contradiction (False)"
        elif gemini_verdict == "TRUE":
            vg_result["verdict"] = "Entailment (True)"

    await save_to_cache(
        normalized_claim,
        vg_result["verdict"],
        vg_result["source"],
        vg_result["snippet"],
        ai_result["verdict"],
        ai_result["reason"]
    )

    return {
        "veriguard": vg_result,
        "secondary_ai": ai_result,
        "is_cached_globally": False
    }