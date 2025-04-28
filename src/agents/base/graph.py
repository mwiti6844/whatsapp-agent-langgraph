from contextlib import asynccontextmanager
from datetime import datetime
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor
from langchain_mcp_adapters.client import MultiServerMCPClient

from agents.base.prompt import CALENDAR_AGENT_PROMPT, SUPERVISOR_PROMPT

load_dotenv()

from langchain_openai import ChatOpenAI
import os

def _groq_chat() -> ChatOpenAI:
    """Return a streaming GroqCloud chat model (OpenAI-compatible)."""
    return ChatOpenAI(
        # use env var if set, else fall back to a *valid* Groq model ID
        model_name=os.getenv("GROQ_MODEL", "llama3-70b-8192"),
        api_key=os.environ["GROQ_API_KEY"],
        base_url=os.getenv("OPENAI_API_BASE", "https://api.groq.com/openai/v1"),
        temperature=0.2,
        streaming=True,
    )


@asynccontextmanager
async def build_agent():
    """Builds and yields the LangGraph agent graph using GroqCloud models."""

    today = datetime.now().strftime("%Y-%m-%d")

    # ────────────────────────────────────────────────────────────────────────────
    # Optional MCP servers (Zapier, Supermemory, etc.)
    # Add your SSE endpoints as env‑vars; empty URLs are ignored gracefully.
    # ────────────────────────────────────────────────────────────────────────────
    zapier_server = {
        "zapier": {
            "url": os.getenv("ZAPIER_URL_MCP"),
            "transport": "sse",
        }
    }

    supermemory_server = {
        "supermemory": {
            "url": os.getenv("SUPERMEMORY_URL_MCP"),
            "transport": "sse",
        }
    }

    zapier_server = {k: v for k, v in zapier_server.items() if v["url"]}
    supermemory_server = {k: v for k, v in supermemory_server.items() if v["url"]}

    # ────────────────────────────────────────────────────────────────────────────
    # Build agents
    # ────────────────────────────────────────────────────────────────────────────
    async with MultiServerMCPClient(zapier_server) as calendar_client, \
              MultiServerMCPClient(supermemory_server) as supervisor_client:

        # Sub‑agent dedicated to calendar/tool actions
        calendar_agent = create_react_agent(
            model=_groq_chat(),
            tools=calendar_client.get_tools(),
            name="calendar_agent",
            prompt=CALENDAR_AGENT_PROMPT.render(today=today),
        )

        # Supervisor orchestrates reasoning & delegation
        graph = create_supervisor(
            [calendar_agent],
            model=_groq_chat(),
            output_mode="last_message",
            prompt=SUPERVISOR_PROMPT.render(),
            tools=supervisor_client.get_tools(),
        )

        yield graph
