import os
from fastapi import FastAPI
from pydantic import BaseModel
from ddgs import DDGS
from sentence_transformers import CrossEncoder
import warnings
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import httpx
import re

load_dotenv()

MONGO_DETAILS = os.getenv("MONGO_URI")

if not MONGO_DETAILS:
    print("WARNING: Could not find MONGO_URI in .env file!")

client = AsyncIOMotorClient(MONGO_DETAILS)
database = client.veriguard
claim_collection = database.claims

# Suppress Windows symlink warnings
warnings.filterwarnings("ignore")

app = FastAPI(title="VeriGuard API", description="Autonomous Fact-Checking Engine")

# Allow the Chrome Extension to talk to this local server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

# 1. Global variables
model = None
# The Expanded VeriGuard Whitelist
whitelist = [
    # Breaking News & Govt
    "reuters.com", "thehindu.com", "apnews.com", "pib.gov.in", "indianexpress.com", "timesofindia.indiatimes.com",
    # Static Knowledge & Fact-Checking
    "wikipedia.org", "britannica.com", "snopes.com", "politifact.com"
]

# 2. Load AI model into memory when the server starts
@app.on_event("startup")
def load_model():
    global model
    print("Initializing VeriGuard...")
    print("Loading DeBERTa-v3 model into RAM (this takes a few seconds)...")
    model = CrossEncoder('cross-encoder/nli-deberta-v3-small')
    print("✅ Model loaded! Server is ready for requests.")

# 3. Define the data structure we expect from the frontend
class ClaimRequest(BaseModel):
    claim: str

# 5. Caching functions
async def check_global_cache(claim_text: str):
    cached_result = await claim_collection.find_one({"claim": claim_text})
    if cached_result:
        cached_result["_id"] = str(cached_result["_id"])
    return cached_result

async def save_to_cache(claim_text: str, verdict: str, source_url: str, snippet: str):
    new_entry = {
        "claim": claim_text,
        "verdict": verdict,
        "source": source_url,
        "snippet": snippet
    }
    await claim_collection.insert_one(new_entry)

async def scrape_article_text(url: str) -> str:
    try:
        # We use a 5-second timeout so a slow website doesn't freeze your engine
        async with httpx.AsyncClient(timeout=5.0) as client:
            # We must use a User-Agent so news sites don't block us thinking we are a bot
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            response = await client.get(url, headers=headers, follow_redirects=True)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Find all paragraph tags
                paragraphs = soup.find_all('p')
                # Combine the first 3 paragraphs to give DeBERTa solid context
                extracted_text = " ".join([p.get_text().strip() for p in paragraphs[:3]])
                return extracted_text
    except Exception as e:
        print(f"Scraping error: {e}")
        return ""
    return ""

def is_question(text: str) -> bool:
    text = text.strip().lower()
    # Check 1: Does it end with a question mark?
    if text.endswith('?'):
        return True
    
    # Check 2: Does it start with a common question word?
    question_patterns = r"^(who|what|where|when|why|how|is|are|do|does|did|can|could|should|would|will)\b"
    if re.match(question_patterns, text):
        return True
        
    return False


@app.post("/verify")
async def verify_claim(request: ClaimRequest):
    normalized_claim = request.claim.strip().lower()
    
    if is_question(normalized_claim):
        return {
            "claim": request.claim,
            "verdict": "Invalid (Not a Claim)",
            "source": None,
            "snippet": "VeriGuard checks factual statements, not questions. Please rewrite this as a declarative claim (e.g., instead of 'Is the sky blue?', type 'The sky is blue.').",
            "is_cached_globally": False
        }
        
    cached_data = await check_global_cache(normalized_claim)
    if cached_data:
        return {
            "claim": request.claim,
            "verdict": cached_data["verdict"],
            "source": cached_data["source"],
            "snippet": cached_data["snippet"],
            "is_cached_globally": True
        }

    claim = request.claim
    snippet = ""
    source_url = ""
    
    with DDGS() as ddgs:
        results = list(ddgs.text(claim, max_results=10))
        for res in results:
            url = res.get('href', '').lower()
            if any(trusted in url for trusted in whitelist):
                source_url = res.get('href', '')
                
                # 1. Try to scrape the actual article text
                scraped_text = await scrape_article_text(source_url)
                
                # 2. If our scraper got good text, use it. Otherwise, fallback to DDG's snippet.
                if scraped_text and len(scraped_text) > 50:
                    snippet = scraped_text
                else:
                    snippet = res.get('body', '')
                    
                break
                
    if not snippet:
        unverified_verdict = "Neutral (Unverified)"
        unverified_snippet = "No data found in whitelisted sources."
        await save_to_cache(normalized_claim, unverified_verdict, None, unverified_snippet)
        
        return {
            "claim": claim,
            "verdict": unverified_verdict,
            "source": None,
            "snippet": unverified_snippet,
            "is_cached_globally": False
        }
        
    scores = model.predict([(snippet, claim)])
    labels = ['Contradiction (False)', 'Entailment (True)', 'Neutral (Unverified)']
    winner = labels[scores[0].argmax()]
    
    await save_to_cache(normalized_claim, winner, source_url, snippet)
    
    return {
        "claim": claim,
        "verdict": winner,
        "source": source_url,
        "snippet": snippet,
        "is_cached_globally": False
    }