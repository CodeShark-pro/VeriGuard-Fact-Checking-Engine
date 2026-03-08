from ddgs import DDGS
from sentence_transformers import CrossEncoder


claim = "The RBI increased the repo rate to 7.5% today."
# We simplify the search query to get maximum results
search_query = "RBI repo rate 7.5% today" 

#  Whitelist
whitelist = ["reuters.com", "thehindu.com", "apnews.com", "pib.gov.in", "indianexpress.com", "timesofindia.indiatimes.com"]

print(f"Searching the web for: '{search_query}'...\n")

snippet = ""
source_url = ""


with DDGS() as ddgs:
    # Grab the top 10 results
    results = list(ddgs.text(search_query, max_results=10))
    
    # Loop through results and strictly enforce the whitelist
    for res in results:
        url = res.get('href', '').lower()
        if any(trusted_domain in url for trusted_domain in whitelist):
            snippet = res.get('body', '')
            source_url = url
            break 

if snippet:
    print(f"✅ Trusted Source Found: {source_url}")
    print(f"Top retrieved snippet:\n'{snippet}'\n")

    # AI Verification Layer
    print("Loading Cross-Encoder NLI Model (Runs 100% locally)...")
    model = CrossEncoder('cross-encoder/nli-deberta-v3-small')
    
    # Calculate the math
    scores = model.predict([(snippet, claim)])
    
    # DeBERTa-v3 output order: [Contradiction, Entailment, Neutral]
    labels = ['Contradiction (False)', 'Entailment (True)', 'Neutral (Unverified)']
    winner = labels[scores[0].argmax()]
    
    print(f"=============================")
    print(f"FINAL VERDICT: {winner}")
    print(f"=============================")

else:
    print("❌ No whitelisted sources reported on this claim.")