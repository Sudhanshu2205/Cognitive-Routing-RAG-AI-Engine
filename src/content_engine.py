"""
content_engine.py -- Phase 2: Autonomous Content Engine using LangGraph

Implements a 3-node LangGraph state machine that simulates a bot autonomously
creating a social media post by "researching" a topic first.

Graph structure:
    decide_search --> web_search --> draft_post --> END

Node responsibilities:
    Node 1 (decide_search): LLM reads persona and decides what to post about.
                            Outputs a search query string.
    Node 2 (web_search):    Runs mock_searxng_search tool with the query.
                            Returns hardcoded news headlines matched to keywords.
    Node 3 (draft_post):    LLM uses persona + search results to write a
                            280-character opinionated post.

Output format (guaranteed via Pydantic structured output):
    {"bot_id": "...", "topic": "...", "post_content": "..."}

LLM: Groq llama-3.3-70b-versatile via langchain_groq
"""

import os
import json
from typing import TypedDict, Optional

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

load_dotenv()


# ── Mock Search Tool ──────────────────────────────────────────────────────────

@tool
def mock_searxng_search(query: str) -> str:
    """
    Simulates a SearXNG web search with hardcoded recent headlines.

    In a production system this would call an actual search API (Tavily, SearXNG).
    Keywords are matched to realistic-sounding headlines that cover the main
    topics each bot persona cares about.

    Args:
        query: Search query string from Node 1 (decide_search).

    Returns:
        A string of simulated news headlines relevant to the query.
    """
    query_lower = query.lower()

    if "crypto" in query_lower or "bitcoin" in query_lower or "btc" in query_lower:
        return (
            "Bitcoin hits new all-time high amid regulatory ETF approvals. "
            "Crypto market cap crosses $3T as institutional money floods in."
        )
    elif "ai" in query_lower or "model" in query_lower or "llm" in query_lower or "openai" in query_lower:
        return (
            "OpenAI launches new model automating coding tasks, threatening junior dev jobs. "
            "Tech layoffs surge as companies replace entry-level roles with AI agents."
        )
    elif "market" in query_lower or "stock" in query_lower or "fed" in query_lower or "interest" in query_lower:
        return (
            "Fed holds rates steady at 5.25%; S&P 500 rallies 2.3% on CPI data. "
            "Hedge funds rotate into tech as yield curve flattens."
        )
    elif "climate" in query_lower or "environment" in query_lower or "nature" in query_lower:
        return (
            "Record-breaking heatwave scorches Europe as emissions targets are missed again. "
            "UN report: Tech industry carbon footprint up 40% due to AI data centers."
        )
    elif "elon" in query_lower or "spacex" in query_lower or "tesla" in query_lower:
        return (
            "SpaceX Starship completes full orbital test successfully. "
            "Elon Musk announces plans for Mars colony by 2030."
        )
    else:
        return (
            "Breaking: Major geopolitical shifts reshape global tech supply chains. "
            "Experts say this decade will define the next 100 years of civilization."
        )


# ── LangGraph State ───────────────────────────────────────────────────────────

class BotState(TypedDict):
    """Typed state dict passed between all nodes in the LangGraph pipeline."""
    bot_id: str
    persona: str
    query: str           # populated in Node 1
    search_results: str  # populated in Node 2
    post_json: Optional[dict]  # populated in Node 3


# ── Pydantic Schema for Structured Output ─────────────────────────────────────

class PostOutput(BaseModel):
    """
    Pydantic model passed to llm.with_structured_output().

    Forces the LLM to return exactly this JSON structure every time.
    LangChain uses function-calling under the hood to guarantee the format.
    """
    bot_id: str = Field(description="The ID of the bot writing the post")
    topic: str = Field(description="The main topic of the post in a few words")
    post_content: str = Field(description="The actual post content, max 280 characters")


# ── LLM Factory ───────────────────────────────────────────────────────────────

def get_llm():
    """
    Returns a ChatGroq instance. Raises a clear EnvironmentError if no key.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY not found. Copy .env.example to .env and add your key."
        )
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.7,
        api_key=api_key
    )


# ── Node 1: Decide Search ──────────────────────────────────────────────────────

def decide_search(state: BotState) -> BotState:
    """
    Node 1 -- Decide what topic to post about and generate a search query.

    The LLM receives the bot's full persona and decides what topic fits
    its personality today. It outputs only the search query string.
    """
    print("\n  [Node 1: Decide Search]")

    llm = get_llm()
    prompt = f"""You are this bot: {state['persona']}

Based on your personality and interests, decide what topic you want to post about today.
Then write a short search query (5-10 words max) to find recent news about that topic.

Only return the search query. Nothing else."""

    response = llm.invoke([HumanMessage(content=prompt)])
    query = response.content.strip().strip('"')

    print(f"    Generated Query: \"{query}\"")
    return {**state, "query": query}


# ── Node 2: Web Search ────────────────────────────────────────────────────────

def web_search(state: BotState) -> BotState:
    """
    Node 2 -- Execute the mock search tool with the query from Node 1.

    Calls mock_searxng_search with keyword matching. In a real system
    this would invoke Tavily, SearXNG, or a similar search API.
    """
    print("\n  [Node 2: Web Search]")

    results = mock_searxng_search.invoke({"query": state["query"]})
    print(f"    Search Results: {results}")

    return {**state, "search_results": results}


# ── Node 3: Draft Post ────────────────────────────────────────────────────────

def draft_post(state: BotState) -> BotState:
    """
    Node 3 -- Write the final post using persona + search results.

    Uses llm.with_structured_output(PostOutput) to guarantee JSON output.
    LangChain translates this to a function-calling request so the LLM
    must return valid JSON matching the PostOutput schema.

    Output is capped at 280 characters to simulate Twitter/X.
    """
    print("\n  [Node 3: Draft Post]")

    llm = get_llm()
    structured_llm = llm.with_structured_output(PostOutput)

    system_prompt = f"""You are {state['bot_id']} -- a social media bot with this personality:
{state['persona']}

You MUST stay in character at all times. Be opinionated, direct, and authentic to your persona.
Write a post that is under 280 characters. Use the search results as context but write in your own voice."""

    human_prompt = f"""Today's search results about "{state['query']}":
{state['search_results']}

Now write your post. Remember: you are {state['bot_id']} with this exact personality.
Your post MUST be under 280 characters and strongly reflect your worldview."""

    output: PostOutput = structured_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ])

    post_dict = {
        "bot_id": state["bot_id"],
        "topic": output.topic,
        "post_content": output.post_content
    }

    print(f"    Generated JSON Output:")
    print(f"    {json.dumps(post_dict, indent=4)}")

    return {**state, "post_json": post_dict}


# ── Build the LangGraph Pipeline ──────────────────────────────────────────────

def build_content_graph():
    """
    Assembles the 3-node LangGraph pipeline and returns a compiled runnable.

    Graph edges:
        decide_search --> web_search --> draft_post --> END
    """
    graph = StateGraph(BotState)

    graph.add_node("decide_search", decide_search)
    graph.add_node("web_search", web_search)
    graph.add_node("draft_post", draft_post)

    graph.set_entry_point("decide_search")
    graph.add_edge("decide_search", "web_search")
    graph.add_edge("web_search", "draft_post")
    graph.add_edge("draft_post", END)

    return graph.compile()


def run_content_engine(bot_id: str, persona: str) -> dict:
    """
    Main entry point for Phase 2.

    Args:
        bot_id:  Bot identifier string, e.g. "Bot_A".
        persona: Full persona description string.

    Returns:
        Final post as a dict: {"bot_id": ..., "topic": ..., "post_content": ...}
    """
    app = build_content_graph()

    initial_state: BotState = {
        "bot_id": bot_id,
        "persona": persona,
        "query": "",
        "search_results": "",
        "post_json": None,
    }

    result = app.invoke(initial_state)
    return result["post_json"]


if __name__ == "__main__":
    persona = (
        "I believe AI and crypto will solve all human problems. I am highly optimistic "
        "about technology, Elon Musk, and space exploration. I dismiss regulatory concerns."
    )
    post = run_content_engine("Bot_A", persona)
    print("\nFinal post:", json.dumps(post, indent=2))
