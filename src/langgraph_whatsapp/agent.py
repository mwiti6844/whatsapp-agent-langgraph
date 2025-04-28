"""LangGraph WhatsApp bridge – Assistant client wrapper.

This module exposes the ``Agent`` class, a thin convenience wrapper around
``langgraph_sdk`` that:

1. Creates (or re‑uses) a unique **thread** per phone number.
2. Accepts plain‑text plus optional images and converts them to the
   LangGraph **MessageContent** schema.
3. Invokes the hosted assistant **streaming** and returns the assistant’s
   final reply – transparently supporting both the legacy ``messages``
   payload and the newer ``response`` / ``content`` keys.

It raises a clear ``ValueError`` when the payload structure is
unrecognised so the caller can surface meaningful errors.
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from langgraph_sdk import get_client

from langgraph_whatsapp import config

LOGGER = logging.getLogger(__name__)


class Agent:  # noqa: D101 – simple facade
    """Minimal async wrapper around :pymod:`langgraph_sdk`."""

    def __init__(self) -> None:
        # Lazily parse the CONFIG env‑var (may be JSON string or a dict)
        if isinstance(config.CONFIG, str):
            try:
                self._graph_config: Dict[str, Any] = json.loads(config.CONFIG)
            except json.JSONDecodeError as exc:  # pragma: no cover
                LOGGER.error("CONFIG env‑var is not valid JSON: %s", exc)
                raise
        else:
            self._graph_config = config.CONFIG or {}

        self._client = get_client(url=config.LANGGRAPH_URL)
        LOGGER.debug("LangGraph client initialised for %s", config.LANGGRAPH_URL)

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    async def invoke(
        self,
        *,
        id: str,
        user_message: str,
        images: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Send the *user_message* (and images) to the assistant & return reply.

        Parameters
        ----------
        id
            Unique identifier (phone number). Used to derive a deterministic
            thread_id so each user gets a single conversation thread.
        user_message
            Plain‑text message from the user.
        images
            Zero or more image payloads, each a dict of shape
            ``{"image_url": {"url": "data:…"}}``.

        Returns
        -------
        str
            Assistant’s reply text.
        """
        thread_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, id))
        LOGGER.info("Invoking assistant – thread_id=%s", thread_id)

        # ------------------------------------------------------------------
        # Build MessageContent list (supports text + images interleaved)
        # ------------------------------------------------------------------
        content: List[Dict[str, Any]] = []
        if user_message:
            content.append({"type": "text", "text": user_message})

        for img in images or []:
            if isinstance(img, dict) and "image_url" in img:
                content.append({"type": "image_url", "image_url": img["image_url"]})

        payload = {
            "thread_id": thread_id,
            "assistant_id": config.ASSISTANT_ID,
            "input": {
                "messages": [
                    {"role": "user", "content": content}
                ]
            },
            "config": self._graph_config,
            "metadata": {"event": "api_call"},
            "multitask_strategy": "interrupt",
            "if_not_exists": "create",
            "stream_mode": "values",
        }

        # ------------------------------------------------------------------
        # Stream the run – only the *last* chunk has the full assistant reply
        # ------------------------------------------------------------------
        final_chunk: Any = None
        try:
            async for chunk in self._client.runs.stream(**payload):
                final_chunk = chunk
        except Exception:  # pragma: no cover
            LOGGER.exception("LangGraph run failed for thread %s", thread_id)
            raise

        # ------------------------------------------------------------------
        # Extract assistant reply – handle legacy & current SDK schemas
        # ------------------------------------------------------------------
        data = getattr(final_chunk, "data", {}) or {}

        if "messages" in data:  # ≤ v0.1.x
            return data["messages"][-1]["content"]
        if "response" in data:  # new default
            return data["response"]
        if "content" in data:   # output_mode="last_message"
            return data["content"]

        # Unknown schema – surface for debugging
        raise ValueError(f"Unexpected assistant payload: {data}")
