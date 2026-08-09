# Conspiracy Theory Generator

Entertainment tool that invents **fresh speculative narratives** and tries to back checkable claims with **live, verified URLs**.

> Use for humor / creative writing only. **Do not spread misinformation.** Verify every source yourself.

## Features

- Web UI with live token streaming (SSE)
- CLI streaming mode
- **OpenRouter** and **OpenAI** providers
- Local web search + URL verification (`ddgs` + `requests`)
- OpenAI-hosted `WebSearchTool` when using the OpenAI provider

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set either:

| Provider | Required env | Notes |
|---|---|---|
| **OpenRouter** | `OPENROUTER_API_KEY` | Set `LLM_PROVIDER=openrouter` (or leave unset if only this key exists). Pick any OpenRouter model via `MODEL`. |
| **OpenAI** | `OPENAI_API_KEY` | Set `LLM_PROVIDER=openai`. Uses the Responses API; can use OpenAI hosted web search. |

## Run (web)

```bash
python app.py
```

Open [http://127.0.0.1:5000/](http://127.0.0.1:5000/).

## Run (CLI)

```bash
python cli.py "undersea internet cables"
python cli.py "museum basements" --scrub-links
```

## Configuration

| Variable | Description |
|---|---|
| `LLM_PROVIDER` | `openai` or `openrouter` |
| `OPENROUTER_API_KEY` | OpenRouter API key |
| `OPENAI_API_KEY` | OpenAI API key |
| `MODEL` | Model id (provider-specific) |
| `APP_URL` / `APP_NAME` | Sent as OpenRouter `HTTP-Referer` / `X-Title` |

## Project layout

```
app.py          Flask web app + SSE endpoint
cli.py          Streaming CLI
ctg/            Agent, tools, provider config
templates/      UI
static/         CSS + JS
```

## License

Unlicense (public domain). See `LICENSE`.
