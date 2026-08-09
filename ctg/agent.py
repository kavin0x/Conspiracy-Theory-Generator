from __future__ import annotations

import os
import re
from collections.abc import AsyncIterator
from typing import Any

from agents import (
    Agent,
    ItemHelpers,
    ModelSettings,
    OpenAIChatCompletionsModel,
    Runner,
    Tool,
    WebSearchTool,
    set_tracing_disabled,
)
from openai import AsyncOpenAI
from openai.types.responses import ResponseTextDeltaEvent

from .config import Settings, load_settings
from .tools import search_verified_links, verify_url, verify_url_tool, web_search

INSTRUCTIONS = """\
You are "The Conspiracy Theorist" — an entertainment writer who invents fresh, \
original conspiracy *narratives* that feel plausible because they weave in real, \
publicly available sources.

Tone: sly, engaging, cinematic. Not shrill. Not bigoted. Not a call to harass anyone.

Hard rules:
1. This is fiction-for-fun framed as speculation. Do not claim certainty. Prefer hedges \
   like "suggests", "raises questions", "according to".
2. Every factual claim that could be checked MUST be backed by at least one full \
   https:// URL you have verified with tools.
3. Workflow for each claim cluster:
   - Call `search_verified_links` with a tight query (prefer declassified docs, court \
     filings, reputable news, academic papers).
   - If you need context snippets, call `web_search`.
   - Call `verify_url_tool` on any URL you did not get from `search_verified_links`.
   - Never invent URLs. Never include an unverified URL. If you cannot verify evidence, \
     drop that claim.
4. Prefer primary sources: FOIA releases, court dockets, congressional records, \
   peer-reviewed papers, major news archives.
5. Avoid recycled famous conspiracies as the main thesis. Twist familiar topics into \
   something new, or invent a novel angle grounded in obscure-but-real documents.
6. Do not invent crimes by named private individuals. Public institutions, corporations, \
   and historical events are fair game for speculative framing.
7. Output format:
   - Short paragraphs of narrative.
   - After each paragraph, a line starting with `Evidence:` followed by one or more \
     verified URLs separated by spaces.
   - End with a one-line disclaimer: `Note: Speculative entertainment — verify sources yourself.`
"""


def _build_model(settings: Settings):
    if settings.provider == "openrouter":
        set_tracing_disabled(True)
        client = AsyncOpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
            default_headers={
                "HTTP-Referer": settings.app_url,
                "X-Title": settings.app_name,
            },
        )
        return OpenAIChatCompletionsModel(
            model=settings.model,
            openai_client=client,
        )

    # Native OpenAI path — Responses API via default provider.
    os.environ.setdefault("OPENAI_API_KEY", settings.api_key)
    return settings.model


def build_agent(settings: Settings | None = None) -> Agent[Any]:
    settings = settings or load_settings()
    tools: list[Tool] = [web_search, search_verified_links, verify_url_tool]

    # OpenAI-hosted WebSearchTool only works on the OpenAI Responses path.
    if settings.provider == "openai":
        tools = [WebSearchTool(), *tools]

    return Agent(
        name="Conspiracy Theorist",
        instructions=INSTRUCTIONS,
        model=_build_model(settings),
        tools=tools,
        model_settings=ModelSettings(tool_choice="auto", temperature=0.85),
    )


def _delta_from_raw_event(data: Any) -> str | None:
    if isinstance(data, ResponseTextDeltaEvent):
        return data.delta or None

    # Chat Completions streaming chunks (OpenRouter / compatible APIs)
    choices = getattr(data, "choices", None)
    if not choices:
        return None
    choice0 = choices[0]
    delta = getattr(choice0, "delta", None)
    if delta is None and isinstance(choice0, dict):
        delta = choice0.get("delta")
    if delta is None:
        return None
    content = getattr(delta, "content", None)
    if content is None and isinstance(delta, dict):
        content = delta.get("content")
    return content if isinstance(content, str) and content else None


async def stream_conspiracy_text(
    topic: str,
    *,
    settings: Settings | None = None,
    agent: Agent[Any] | None = None,
) -> AsyncIterator[str]:
    """Yield text tokens as the agent generates them (no duplicate finals)."""
    agent = agent or build_agent(settings)
    result_stream = Runner.run_streamed(agent, input=topic.strip())
    saw_delta = False

    async for event in result_stream.stream_events():
        if event.type == "raw_response_event":
            token = _delta_from_raw_event(event.data)
            if token:
                saw_delta = True
                yield token
            continue

        if (
            not saw_delta
            and event.type == "run_item_stream_event"
            and event.item.type == "message_output_item"
        ):
            chunk = ItemHelpers.text_message_output(event.item)
            if chunk:
                yield chunk


def generate_conspiracy(topic: str, *, settings: Settings | None = None) -> str:
    agent = build_agent(settings)
    result = Runner.run_sync(agent, topic.strip())
    return result.final_output or ""


def scrub_dead_links(text: str) -> tuple[str, list[str]]:
    """Remove markdown links whose URLs fail verification."""
    pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
    removed: list[str] = []

    def _replace(match: re.Match[str]) -> str:
        url = match.group(2)
        if verify_url(url):
            return match.group(0)
        removed.append(match.group(0))
        return "[INVALID LINK REMOVED]"

    return pattern.sub(_replace, text), removed
