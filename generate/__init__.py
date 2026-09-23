"""Daily job: select HN posts, fetch their source, ask GPT-6 Luna for card CONTENT only,
then assemble the JSON here. The model never sees or emits ids, urls or counts —
those are facts we already have from HN.

    python3 -m generate          write data/<today UTC>.json
    python3 -m generate --check  offline self-check, no network, no API key
    python3 -m generate --dry 3  fetch 3 posts, print the model input, call nothing
    python3 -m generate --sample 1  one real call, print the card, write nothing

The system prompt lives in prompt.md, next to this file, so it can be edited without
touching code.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PROMPT = Path(__file__).resolve().parent / "prompt.md"
