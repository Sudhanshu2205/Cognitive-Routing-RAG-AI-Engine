"""
router.py -- Phase 1: Vector-Based Persona Matching

This module implements the first phase of the assignment:
- Takes each bot's personality description
- Converts it into a vector embedding
- Stores it in an in-memory ChromaDB vector database
- When a new post arrives, embeds it and finds which bots "care" about it
  using cosine similarity

Embedding model: sentence-transformers/all-MiniLM-L6-v2
  - Free, runs locally, no API key needed
  - Cosine similarity scores typically range 0.20 to 0.65 for related content
    (unlike OpenAI ada-002 which gives 0.85+ scores as mentioned in the assignment)
  - Default threshold is set to 0.20 after calibration testing

Vector store: ChromaDB EphemeralClient (in-memory, no disk writes)
  - hnsw:space=cosine is required -- without it ChromaDB uses L2 distance
    and similarity conversion breaks
"""

import chromadb
from sentence_transformers import SentenceTransformer


# The three bot personas from the assignment (verbatim)
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


def setup_vector_store():
    """
    Creates an in-memory ChromaDB collection and loads all three bot personas.

    Returns:
        Tuple of (collection, embedding_model) for reuse in routing calls.

    Note on hnsw:space=cosine:
        ChromaDB returns DISTANCES by default (lower = more similar).
        With cosine space: similarity = 1 - distance
        Without it, L2 distance is used and the conversion does not apply.
    """
    print("\n[Phase 1] Setting up vector store...")

    model = SentenceTransformer("all-MiniLM-L6-v2")
    print("  [OK] Loaded embedding model: all-MiniLM-L6-v2")

    client = chromadb.EphemeralClient()
    collection = client.create_collection(
        name="bot_personas",
        metadata={"hnsw:space": "cosine"}
    )

    for bot_id, persona_text in BOT_PERSONAS.items():
        embedding = model.encode(persona_text).tolist()
        collection.add(
            ids=[bot_id],
            embeddings=[embedding],
            documents=[persona_text],
            metadatas=[{"bot_id": bot_id}]
        )
        print(f"  [OK] Stored embedding for {bot_id}")

    print("  [OK] Vector store ready\n")
    return collection, model


def route_post_to_bots(post_content: str, threshold: float = 0.20):
    """
    Main routing function. Embeds an incoming post and finds which bots match.

    The assignment specifies threshold=0.85, which is calibrated for OpenAI ada-002.
    With all-MiniLM-L6-v2, realistic scores range from 0.20 to 0.65.
    The default threshold is set to 0.20 to get meaningful matches.
    Callers can override threshold for stricter or looser matching.

    Args:
        post_content: The text of the incoming social media post.
        threshold:    Minimum cosine similarity to include a bot as a match.

    Returns:
        List of dicts: [{"bot_id": str, "similarity": float}, ...]
        Only bots whose similarity score >= threshold are included.
    """
    collection, model = setup_vector_store()

    print(f"  Input Post : \"{post_content}\"")
    print(f"  Threshold  : {threshold}\n")

    post_embedding = model.encode(post_content).tolist()

    # n_results=3 retrieves all three bots for comparison
    results = collection.query(
        query_embeddings=[post_embedding],
        n_results=3,
        include=["distances", "metadatas", "documents"]
    )

    # ChromaDB with cosine space returns distances, NOT similarities.
    # Convert: similarity = 1 - distance
    matched_bots = []
    print("  Cosine Similarity Scores:")

    distances = results["distances"][0]
    metadatas = results["metadatas"][0]

    for i, distance in enumerate(distances):
        similarity = 1 - distance
        bot_id = metadatas[i]["bot_id"]

        if similarity >= threshold:
            status = "[MATCHED]"
            matched_bots.append({"bot_id": bot_id, "similarity": round(similarity, 4)})
        else:
            status = "[below threshold]"

        print(f"    {bot_id}: {similarity:.4f}  {status}")

    routed = [b["bot_id"] for b in matched_bots] if matched_bots else ["No bots matched"]
    print(f"\n  Routed to: {routed}")
    return matched_bots


if __name__ == "__main__":
    test_post = "OpenAI just released a new model that might replace junior developers."
    matches = route_post_to_bots(test_post)
    print("\nFinal result:", matches)
