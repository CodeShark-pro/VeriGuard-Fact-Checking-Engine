import os
import urllib.parse

import requests
from dotenv import load_dotenv
from sentence_transformers import CrossEncoder


def main():
    load_dotenv()

    api_key = os.getenv("GOOGLE_API_KEY")
    cx = os.getenv("SEARCH_ENGINE_ID")

    if not api_key or not cx:
        raise SystemExit(
            "Missing environment variables. Ensure GOOGLE_API_KEY and SEARCH_ENGINE_ID are set in your .env or environment."
        )

    claim = "The RBI increased the repo rate to 7.5% today."

    print(f"Searching whitelisted sources for: '{claim}'...\n")

    query = urllib.parse.quote_plus(claim)
    url = f"https://www.googleapis.com/customsearch/v1?q={query}&key={api_key}&cx={cx}"

    response = requests.get(url, timeout=10)

    try:
        results = response.json()
    except ValueError:
        raise SystemExit("Failed to decode JSON from Google Custom Search response.")

    if response.status_code != 200:
        print("Google Custom Search API request failed:")
        print(f"  status_code={response.status_code}")
        print(f"  response={results}")
        return

    # Extract the first snippet of text from the search results
    if "items" in results and results["items"]:
        snippet = results["items"][0].get("snippet", "")
        print(f"Top retrieved snippet:\n'{snippet}'\n")
    else:
        print("No results found. Check your API key, Search Engine ID, and that Custom Search is enabled for your project.")
        return

    if snippet:
        print("Loading Cross-Encoder NLI Model (this takes a few seconds the first time)...")
        model = CrossEncoder("cross-encoder/nli-deberta-v3-small")

        scores = model.predict([(snippet, claim)])

        print(f"\nRaw Model Math: {scores[0]}")

        labels = ["Contradiction (False)", "Entailment (True)", "Neutral (Unverified)"]
        winner = labels[int(scores[0].argmax())]

        print(f"=============================")
        print(f"FINAL VERDICT: {winner}")
        print(f"=============================")


if __name__ == "__main__":
    main()
