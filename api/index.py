"""
index.py -- FastAPI Serverless Entry Point

Exposes API endpoints to interface with the Persona Router, LangGraph Content Engine, and Combat Reply Engine.
Supports CORS and uses SSE to stream graph execution nodes in real-time.
"""

import json
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.router import route_post_to_bots, get_all_scores
from api.content_engine import build_content_graph
from api.rag_engine import generate_defense_reply, detect_injection

app = FastAPI(
    title="Cognitive Routing & RAG AI API",
    description="Backend API for Persona Router, Content Graph (LangGraph), and Combat RAG engine",
    version="1.0.0"
)

# Enable CORS for local cross-origin React development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Models ────────────────────────────────────────────────────────────────

class RouteRequest(BaseModel):
    post_content: str
    threshold: float = 0.20
    personas: Optional[Dict[str, str]] = None

class ContentGraphRequest(BaseModel):
    bot_id: str
    persona: str
    groq_api_key: Optional[str] = None

class CommentItem(BaseModel):
    author: str
    text: str

class CombatRequest(BaseModel):
    bot_id: str
    bot_persona: str
    parent_post: str
    comment_history: List[CommentItem]
    human_reply: str
    groq_api_key: Optional[str] = None

# ── API Routes ────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health_check():
    """Simple API health check endpoint."""
    return {"status": "healthy", "service": "Cognitive Routing & RAG Engine"}

@app.post("/api/route")
def route_post(data: RouteRequest):
    """
    Routes an incoming post to the matching bot personas based on semantic similarity.
    Calculated via Hugging Face embeddings + plain-python Cosine Similarity.
    """
    try:
        matched = route_post_to_bots(
            post_content=data.post_content,
            threshold=data.threshold,
            personas=data.personas,
        )
        # Calculate full scores for all personas (even those below threshold)
        all_scores = get_all_scores(data.post_content, personas=data.personas)
            
        return {
            "post": data.post_content,
            "scores": all_scores,
            "routed": [[b["bot_id"], b["similarity"]] for b in matched]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/content_graph")
async def run_content_graph_api(data: ContentGraphRequest):
    """
    Executes the 3-node LangGraph pipeline for the given persona.
    Streams execution progress node-by-node using Server-Sent Events (SSE).
    """
    async def event_generator():
        try:
            app_runnable = build_content_graph()
            initial_state = {
                "bot_id": data.bot_id,
                "persona": data.persona,
                "query": "",
                "search_results": "",
                "post_json": None,
                "groq_api_key": data.groq_api_key
            }
            
            # Stream sync execution events
            # We wrap the generator to run cleanly
            for event in app_runnable.stream(initial_state):
                for node_name, node_output in event.items():
                    payload = {
                        "node": node_name,
                        "query": node_output.get("query", ""),
                        "search_results": node_output.get("search_results", ""),
                        "post_json": node_output.get("post_json")
                    }
                    yield f"data: {json.dumps(payload)}\n\n"
                    
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/api/combat_reply")
def run_combat_reply_api(data: CombatRequest):
    """
    Generates a context-aware combat reply using the RAG conversation thread.
    Applies security pre-filtering and system prompt constraints for injection defense.
    """
    try:
        # Pre-check: scan human reply for injection keywords before sending to LLM
        heuristic_detected = detect_injection(data.human_reply)
        
        history = [{"author": c.author, "text": c.text} for c in data.comment_history]
        
        reply = generate_defense_reply(
            bot_persona=data.bot_persona,
            bot_id=data.bot_id,
            parent_post=data.parent_post,
            comment_history=history,
            human_reply=data.human_reply,
            groq_api_key=data.groq_api_key
        )
        
        return {
            "reply": reply,
            "heuristic_detected": heuristic_detected,
            "human_message": data.human_reply
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
