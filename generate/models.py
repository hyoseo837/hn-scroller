"""The model call: GPT-6 Luna over the OpenAI Responses API."""

import json
import os
import urllib.error
import urllib.request

from . import PROMPT
from .cards import SCHEMA, model_input


LUNA = "gpt-6-luna"
LUNA_API = "https://api.openai.com/v1/responses"
# Measured on 9 posts: high kept the prompt's format where medium drifted, for about
# $0.001 a card more. xhigh took 60-100+ s a post and once ran past the 120 s timeout.
LUNA_EFFORT = "high"
LUNA_PRICE_IN = 0.10   # USD per 1M input tokens
LUNA_PRICE_OUT = 0.50  # USD per 1M output tokens; reasoning bills as output
# Reasoning is ~90% of output at high effort, so it dominates both cost and wall time.
USAGE = {"calls": 0, "input": 0, "output": 0, "thought": 0}


def strict(schema):
    """A copy of `schema` for OpenAI strict mode: every object closed, every property
    required. Our optional `data` becomes required, so "none" is an empty list."""
    if isinstance(schema, list):
        return [strict(s) for s in schema]
    if not isinstance(schema, dict):
        return schema
    out = {k: strict(v) for k, v in schema.items()}
    if "properties" in out:
        out["required"] = list(out["properties"])
        out["additionalProperties"] = False
    return out


def luna_text(body: dict) -> str:
    """Pull the answer out of an OpenAI /v1/responses body.

    The top-level `output_text` is SDK-only and absent over raw HTTP. `output` holds
    `reasoning` items (no text) and a `message` whose content is `output_text` or
    `refusal`. A refusal or truncation must fail loudly, not parse as an empty card.
    """
    texts = []
    for item in body.get("output") or []:
        if item.get("type") != "message":
            continue
        for block in item.get("content") or []:
            if block.get("type") == "refusal":
                raise RuntimeError(f"luna refused: {block.get('refusal')!r}")
            if block.get("type") == "output_text":
                texts.append(block["text"])
    if texts and body.get("status") == "completed":
        return texts[-1]
    raise RuntimeError(
        f"no usable text in OpenAI response (status={body.get('status')!r}, "
        f"incomplete={body.get('incomplete_details')!r}):\n{json.dumps(body)[:1500]}"
    )


def luna_content(title: str, article: str, comments: list[str]) -> dict:
    """One post's card content. Strict JSON schema, so the shape is guaranteed."""
    payload = json.dumps(
        {
            "model": LUNA,
            "instructions": PROMPT.read_text(encoding="utf-8"),
            "input": model_input(title, article, comments),
            "reasoning": {"effort": LUNA_EFFORT},
            "text": {
                "format": {"type": "json_schema", "name": "card", "schema": strict(SCHEMA), "strict": True}
            },
        }
    ).encode()
    req = urllib.request.Request(
        LUNA_API,
        data=payload,
        headers={
            "authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
            "content-type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as res:
            body = json.loads(res.read())
    except urllib.error.HTTPError as err:
        raise RuntimeError(f"openai {err.code}: {err.read()[:300].decode('utf-8', 'replace')}")

    used = body.get("usage") or {}
    reasoning = (used.get("output_tokens_details") or {}).get("reasoning_tokens") or 0
    USAGE["calls"] += 1
    USAGE["input"] += used.get("input_tokens") or 0
    # output_tokens already includes reasoning. Split it out, or usage_line would
    # bill the thinking twice.
    USAGE["output"] += (used.get("output_tokens") or 0) - reasoning
    USAGE["thought"] += reasoning
    return json.loads(luna_text(body))


def usage_line() -> str:
    billed_out = USAGE["output"] + USAGE["thought"]
    cost = USAGE["input"] / 1e6 * LUNA_PRICE_IN + billed_out / 1e6 * LUNA_PRICE_OUT
    share = USAGE["thought"] / billed_out * 100 if billed_out else 0
    return (
        f"{USAGE['calls']} call{'s' if USAGE['calls'] != 1 else ''} | in {USAGE['input']:,} | out {billed_out:,} "
        f"({USAGE['thought']:,} thinking, {share:.0f}%) | ${cost:.3f}"
    )
