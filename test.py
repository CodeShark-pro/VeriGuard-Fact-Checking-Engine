import os
import requests
from dotenv import load_dotenv
from sentence_transformers import CrossEncoder

# 1. Load your secret keys securely from the .env file
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
CX = os.getenv("SEARCH_ENGINE_ID")

# 2. The Claim we want to verify
claim = "The RBI increased the repo rate to 7.5% today."

# 3. Search Google (The Retrieval Layer)
print(f"Searching whitelisted sources for: '{claim}'...\n")
url = f"https://www.googleapis.com/customsearch/v1?q={claim}&key={API_KEY}&cx={CX}"

response = requests.get(url)
results = response.json()

# Extract the first snippet of text from the search results
if "items" in results:
    snippet = results["items"][0]["snippet"]
    print(f"Top retrieved snippet:\n'{snippet}'\n")
else:
    print("No results found. Check your API key and Search Engine ID.")
    snippet = ""

# 4. The NLI Math (The AI Verification Layer)
if snippet:
    print("Loading Cross-Encoder NLI Model (this takes a few seconds the first time)...")
    # This downloads a tiny, highly accurate model to your local machine
    model = CrossEncoder('cross-encoder/nli-deberta-v3-small')
    
    # Calculate the semantic relationship between the snippet and the claim
    scores = model.predict([(snippet, claim)])
    
    # DeBERTa-v3 outputs 3 scores in this exact order: [Contradiction, Entailment, Neutral]
    print(f"\nRaw Model Math: {scores[0]}")
    
    # Determine which score is mathematically the highest
    labels = ['Contradiction (False)', 'Entailment (True)', 'Neutral (Unverified)']
    winner = labels[scores[0].argmax()]
    
    print(f"=============================")
    print(f"FINAL VERDICT: {winner}")
    print(f"=============================")