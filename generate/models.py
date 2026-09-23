"""The model calls: Gemini in production, GPT-6 Luna for `--sample --luna` evaluation."""

import json
import os
import urllib.error
import urllib.request

from . import PROMPT
from .cards import SCHEMA, model_input


GEMINI_FLASH = "gemini-3.8-flash"
GEMINI_API = "https://generativelanguage.googleapis.com/v1beta/interactions"
# Evaluation only, reached by `--sample N --luna`. Production stays on Gemini.
LUNA = "gpt-6-luna"
LUNA_API = "https://api.openai.com/v1/responses"
LUNA_EFFORT = "medium"  # the model's default; Flash thinks by default too, so like for like
# USD per 1M tokens, (input, output). Thinking bills as output on both.
# Flash's is the introductory price: it doubles to (1.50, 7.50) on 2027-01-01.
PRICES = {GEMINI_FLASH: (0.75, 3.75), LUNA: (0.10, 0.50)}
# Thinking is counted separately from total_output_tokens but billed as output,
# and it runs ~3x the visible answer — so it dominates both cost and wall time.
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


def gemini_text(body: dict) -> str:
    """Pull the answer out of an /interactions response.

    `steps` holds the run in order. Reasoning steps are `type: "thought"` and carry
    no `content` at all, so skipping them is not optional — the answer is in the
    content blocks of a later step. Last text block wins, matching the SDK's
    `output_text`, which is documented as the last text blocks in the response.
    """
    texts = [
        block["text"]
        for step in body.get("steps") or []
        if isinstance(step, dict)
        for block in step.get("content") or []
        if isinstance(block, dict) and isinstance(block.get("text"), str)
    ]
    if texts:
        return texts[-1]
    raise RuntimeError(
        f"no text block in Gemini response (status={body.get('status')!r}, "
        f"keys={sorted(body)}):\n{json.dumps(body)[:1500]}"
    )


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


def gemini_content(title: str, article: str, comments: list[str]) -> dict:
    payload = json.dumps(
        {
            "model": GEMINI_FLASH,
            "system_instruction": PROMPT.read_text(encoding="utf-8"),
            "input": model_input(title, article, comments),
            "response_format": {
                "type": "text",
                "mime_type": "application/json",
                "schema": SCHEMA,
            },
        }
    ).encode()
    req = urllib.request.Request(
        GEMINI_API,
        data=payload,
        headers={
            "x-goog-api-key": os.environ["GEMINI_API_KEY"],
            "content-type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as res:
            body = json.loads(res.read())
    except urllib.error.HTTPError as err:
        raise RuntimeError(f"gemini {err.code}: {err.read()[:300].decode('utf-8', 'replace')}")

    used = body.get("usage") or {}
    USAGE["calls"] += 1
    USAGE["input"] += used.get("total_input_tokens") or 0
    USAGE["output"] += used.get("total_output_tokens") or 0
    USAGE["thought"] += used.get("total_thought_tokens") or 0
    return json.loads(gemini_text(body))


def luna_content(title: str, article: str, comments: list[str]) -> dict:
    """gemini_content's twin for the OpenAI Responses API. Same prompt, same input."""
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
    # Unlike Gemini, output_tokens already includes reasoning. Split it out, or
    # usage_line would bill the thinking twice.
    USAGE["output"] += (used.get("output_tokens") or 0) - reasoning
    USAGE["thought"] += reasoning
    return json.loads(luna_text(body))


def usage_line(model: str = GEMINI_FLASH) -> str:
    price_in, price_out = PRICES[model]
    billed_out = USAGE["output"] + USAGE["thought"]
    cost = USAGE["input"] / 1e6 * price_in + billed_out / 1e6 * price_out
    share = USAGE["thought"] / billed_out * 100 if billed_out else 0
    return (
        f"{USAGE['calls']} call{'s' if USAGE['calls'] != 1 else ''} | in {USAGE['input']:,} | out {billed_out:,} "
        f"({USAGE['thought']:,} thinking, {share:.0f}%) | ${cost:.3f}"
    )
