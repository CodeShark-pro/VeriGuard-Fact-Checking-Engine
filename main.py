from fastapi import FastAPI
from pydantic import BaseModel
from ddgs import DDGS
from sentence_transformers import CrossEncoder
import warnings
from fastapi.middleware.cors import CORSMiddleware

# Suppress the annoying Windows symlink warnings
warnings.filterwarnings("ignore")

app = FastAPI(title="VeriGuard API", description="Autonomous Fact-Checking OSINT Engine")

# Allow the Chrome Extension to talk to this local server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (including your extension)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

# 1. Global variables
model = None
whitelist = ["reuters.com", "thehindu.com", "apnews.com", "pib.gov.in", "indianexpress.com", "timesofindia.indiatimes.com"]

# 2. Load the AI model into memory when the server starts
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

# 4. The Verification Endpoint
@app.post("/verify")
async def verify_claim(request: ClaimRequest):
    claim = request.claim
    
    # Retrieval Layer
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
                
    # If no trusted sources report on it
    if not snippet:
        return {
            "claim": claim,
            "verdict": "Unverified",
            "source": None,
            "snippet": "No data found in whitelisted sources."
        }
        
    # Verification Layer
    scores = model.predict([(snippet, claim)])
    labels = ['Contradiction (False)', 'Entailment (True)', 'Neutral (Unverified)']
    winner = labels[scores[0].argmax()]
    
    # Return the final JSON payload
    return {
        "claim": claim,
        "verdict": winner,
        "source": source_url,
        "snippet": snippet
    }