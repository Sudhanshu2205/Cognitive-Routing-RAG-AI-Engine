"""
router.py -- Phase 1: Vector-Based Persona Matching (Vercel Serverless Ready)

This module implements the persona matching logic using a self-contained
TF-IDF vectorizer and cosine similarity calculation. No external API calls
are needed — everything runs in-process, ensuring instant results and
zero network dependencies on Vercel's serverless environment.
"""

import math
import re
from collections import Counter

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

# Common English stop words to filter out for better similarity matching
STOP_WORDS = frozenset([
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your",
    "yours", "yourself", "yourselves", "he", "him", "his", "himself", "she", "her",
    "hers", "herself", "it", "its", "itself", "they", "them", "their", "theirs",
    "themselves", "what", "which", "who", "whom", "this", "that", "these", "those",
    "am", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "having", "do", "does", "did", "doing", "a", "an", "the", "and", "but", "if",
    "or", "because", "as", "until", "while", "of", "at", "by", "for", "with",
    "about", "against", "between", "through", "during", "before", "after", "above",
    "below", "to", "from", "up", "down", "in", "out", "on", "off", "over", "under",
    "again", "further", "then", "once", "here", "there", "when", "where", "why",
    "how", "all", "both", "each", "few", "more", "most", "other", "some", "such",
    "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "s",
    "t", "can", "will", "just", "don", "should", "now", "d", "ll", "m", "o", "re",
    "ve", "y", "ain", "aren", "couldn", "didn", "doesn", "hadn", "hasn", "haven",
    "isn", "ma", "mightn", "mustn", "needn", "shan", "shouldn", "wasn", "weren",
    "won", "wouldn",
])


def tokenize(text: str) -> list[str]:
    """Tokenizes text into lowercase words, removing stop words and short tokens."""
    words = re.findall(r'[a-zA-Z]+', text.lower())
    return [w for w in words if w not in STOP_WORDS and len(w) > 1]


def compute_tfidf_vectors(documents: list[str]) -> tuple[list[dict], dict]:
    """
    Computes TF-IDF vectors for a list of documents.
    
    Returns:
        Tuple of (list of TF-IDF vector dicts, IDF dict)
    """
    # Tokenize all documents
    tokenized_docs = [tokenize(doc) for doc in documents]
    
    # Compute document frequency (DF) for each term
    num_docs = len(tokenized_docs)
    df = Counter()
    for tokens in tokenized_docs:
        unique_tokens = set(tokens)
        for token in unique_tokens:
            df[token] += 1
    
    # Compute IDF: log(N / df) with smoothing
    idf = {}
    for term, freq in df.items():
        idf[term] = math.log((num_docs + 1) / (freq + 1)) + 1  # smooth IDF
    
    # Compute TF-IDF for each document
    tfidf_vectors = []
    for tokens in tokenized_docs:
        tf = Counter(tokens)
        total_terms = len(tokens) if tokens else 1
        
        vector = {}
        for term, count in tf.items():
            tf_val = count / total_terms
            vector[term] = tf_val * idf.get(term, 1.0)
        
        tfidf_vectors.append(vector)
    
    return tfidf_vectors, idf


def cosine_similarity_sparse(v1: dict, v2: dict) -> float:
    """Computes cosine similarity between two sparse vectors (dicts)."""
    # Find common terms
    common_terms = set(v1.keys()) & set(v2.keys())
    
    dot_product = sum(v1[t] * v2[t] for t in common_terms)
    
    mag1 = math.sqrt(sum(val ** 2 for val in v1.values())) if v1 else 0
    mag2 = math.sqrt(sum(val ** 2 for val in v2.values())) if v2 else 0
    
    if mag1 == 0 or mag2 == 0:
        return 0.0
    
    return dot_product / (mag1 * mag2)


def route_post_to_bots(
    post_content: str,
    threshold: float = 0.20,
    personas: dict = None,
    hf_token: str = None  # kept for API compatibility, not used
) -> list:
    """
    Stateless routing function. Computes TF-IDF similarity between
    the post and each bot persona.
    
    Args:
        post_content: Content of the post.
        threshold: Cosine similarity cutoff.
        personas: Persona dictionary mapping bot ID to persona description.
        hf_token: Unused, kept for API compatibility.
        
    Returns:
        List of dicts: [{"bot_id": str, "similarity": float}]
    """
    if not personas:
        personas = BOT_PERSONAS

    bot_ids = list(personas.keys())
    persona_texts = list(personas.values())
    
    # Build TF-IDF vectors for all documents together (post + all personas)
    all_documents = [post_content] + persona_texts
    tfidf_vectors, _ = compute_tfidf_vectors(all_documents)
    
    post_vector = tfidf_vectors[0]
    persona_vectors = tfidf_vectors[1:]
    
    # Calculate similarities and filter by threshold
    matched_bots = []
    for i, bot_id in enumerate(bot_ids):
        similarity = cosine_similarity_sparse(post_vector, persona_vectors[i])
        if similarity >= threshold:
            matched_bots.append({
                "bot_id": bot_id,
                "similarity": round(similarity, 4)
            })
    
    # Sort matches by similarity score descending
    matched_bots.sort(key=lambda x: x["similarity"], reverse=True)
    return matched_bots


def get_all_scores(post_content: str, personas: dict = None) -> dict:
    """
    Returns similarity scores for ALL personas (not just those above threshold).
    Used by the API to populate the frontend visualizer.
    """
    if not personas:
        personas = BOT_PERSONAS

    bot_ids = list(personas.keys())
    persona_texts = list(personas.values())
    
    all_documents = [post_content] + persona_texts
    tfidf_vectors, _ = compute_tfidf_vectors(all_documents)
    
    post_vector = tfidf_vectors[0]
    persona_vectors = tfidf_vectors[1:]
    
    scores = {}
    for i, bot_id in enumerate(bot_ids):
        similarity = cosine_similarity_sparse(post_vector, persona_vectors[i])
        scores[bot_id] = round(similarity, 4)
    
    return scores
