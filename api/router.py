"""
router.py -- Phase 1: Vector-Based Persona Matching (Vercel Serverless Ready)

This module implements the persona matching logic:
- Fetches text embeddings from the Hugging Face Inference API (all-MiniLM-L6-v2).
- Calculates cosine similarity in pure Python (no ChromaDB/PyTorch needed).
- Filters matches using the provided similarity threshold.
"""

import os
import time
import requests

# The default bot personas
BOT_PERSONAS = {
    "Bot_A": (
        "I believe AI and crypto will solve all human problems. I am highly optimistic "
        "about technology, Elon Musk, and space exploration. I dismiss regulatory concerns."
    ),
    "Bot_B": (
        "I believe late-stage capitalism and tech monopolies are destroying society. "
        "I am highly critical of AI, social media, and billionaires. I value privacy and nature."
    ),
    "Bot_C": (
        "I strictly care about markets, interest rates, trading algorithms, and making money. "
        "I speak in finance jargon and view everything through the lens of ROI."
    ),
}

HF_API_URL = "https://api-inference.huggingface.co/models/sentence-transformers/all-MiniLM-L6-v2"

def get_hf_embedding(text: str, token: str = None) -> list:
    """
    Retrieves the text embedding from Hugging Face Inference API.
    Handles automatic model loading wait times.
    """
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    elif os.getenv("HF_TOKEN"):
        headers["Authorization"] = f"Bearer {os.getenv('HF_TOKEN')}"

    # Try up to 5 times if model is loading
    for attempt in range(5):
        try:
            response = requests.post(
                HF_API_URL,
                headers=headers,
                json={"inputs": text, "options": {"wait_for_model": True}},
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                # Sometimes HF returns a 2D array if inputs was wrapped in a list
                if isinstance(result, list):
                    if len(result) > 0 and isinstance(result[0], list):
                        return result[0]
                    return result
                raise ValueError(f"Unexpected HF response format: {result}")
            
            # Handle model loading
            res_json = response.json()
            if "estimated_time" in res_json:
                wait_time = min(res_json.get("estimated_time", 5), 5)
                time.sleep(wait_time)
                continue
                
            raise ValueError(f"HF API Error ({response.status_code}): {response.text}")
            
        except requests.exceptions.RequestException as e:
            if attempt == 4:
                raise e
            time.sleep(1)
            
    raise RuntimeError("Failed to retrieve embeddings from Hugging Face API: Model loading timed out.")

def cosine_similarity(v1: list, v2: list) -> float:
    """Calculates the cosine similarity between two numeric vectors."""
    dot_product = sum(x * y for x, y in zip(v1, v2))
    magnitude1 = sum(x * x for x in v1) ** 0.5
    magnitude2 = sum(x * x for x in v2) ** 0.5
    if not magnitude1 or not magnitude2:
        return 0.0
    return dot_product / (magnitude1 * magnitude2)

def route_post_to_bots(post_content: str, threshold: float = 0.20, personas: dict = None, hf_token: str = None) -> list:
    """
    Stateless routing function. Embeds the post and matches against bot personas.
    
    Args:
        post_content: Content of the post.
        threshold: Cosine similarity cutoff.
        personas: Persona dictionary mapping bot ID to persona description.
        hf_token: Optional Hugging Face Token.
        
    Returns:
        List of dicts: [{"bot_id": str, "similarity": float}]
    """
    if not personas:
        personas = BOT_PERSONAS

    # 1. Fetch embedding for post
    post_vector = get_hf_embedding(post_content, token=hf_token)
    
    # 2. Fetch embeddings for all bot personas and calculate similarities
    matched_bots = []
    
    for bot_id, persona_text in personas.items():
        persona_vector = get_hf_embedding(persona_text, token=hf_token)
        similarity = cosine_similarity(post_vector, persona_vector)
        
        if similarity >= threshold:
            matched_bots.append({
                "bot_id": bot_id,
                "similarity": round(similarity, 4)
            })
            
    # Sort matches by similarity score descending
    matched_bots.sort(key=lambda x: x["similarity"], reverse=True)
    return matched_bots

if __name__ == "__main__":
    # Test locally
    import dotenv
    dotenv.load_dotenv()
    test_post = "OpenAI just released a new model that might replace junior developers."
    print("Testing routing...")
    try:
        matches = route_post_to_bots(test_post)
        print("Matches:", matches)
    except Exception as e:
        print("Error during test routing:", e)
