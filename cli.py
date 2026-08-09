#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import sys

from ctg.agent import scrub_dead_links, stream_conspiracy_text
from ctg.config import load_settings


async def _run(topic: str, *, scrub: bool) -> int:
    settings = load_settings()
    print(
        f"[provider={settings.provider} model={settings.model}]\n",
        file=sys.stderr,
    )

    buffer: list[str] = []
    async for token in stream_conspiracy_text(topic, settings=settings):
        print(token, end="", flush=True)
        buffer.append(token)
    print()

    if scrub:
        full = "".join(buffer)
        corrected, removed = scrub_dead_links(full)
        if removed:
            print("\n---\nRemoved unverifiable markdown links:")
            for item in removed:
                print(f"- {item}")
            print("\nCorrected output:\n")
            print(corrected.strip())
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a speculative, evidence-linked conspiracy narrative."
    )
    parser.add_argument("topic", nargs="+", help="Topic to riff on")
    parser.add_argument(
        "--scrub-links",
        action="store_true",
        help="After streaming, re-check markdown links and reprint if any fail",
    )
    args = parser.parse_args()
    topic = " ".join(args.topic).strip()

    try:
        raise SystemExit(asyncio.run(_run(topic, scrub=args.scrub_links)))
    except KeyboardInterrupt as exc:
        print("\nInterrupted.", file=sys.stderr)
        raise SystemExit(130) from exc
    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
