import os
from fastapi import FastAPI
from pydantic import BaseModel
from ddgs import DDGS
from sentence_transformers import CrossEncoder
import warnings
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Securely grab the connection string
MONGO_DETAILS = os.getenv("MONGO_URI")

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


@app.post("/verify")
async def verify_claim(request: ClaimRequest):
    normalized_claim = request.claim.strip().lower()
    
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
                snippet = res.get('body', '')
                source_url = res.get('href', '')
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