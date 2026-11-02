"""Minimal OpenRouter client shared by the LLM passes (review, canonicalize, summarize)."""

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

URL = "https://openrouter.ai/api/v1/chat/completions"
ROOT = Path(__file__).resolve().parent.parent
HAIKU = "anthropic/claude-haiku-5.5"
SONNET = "anthropic/claude-sonnet-5.5"


def api_key():
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        k, _, v = line.partition("=")
        if k.strip() == "OPEN_ROUTER_API_KEY":
            return v.strip().strip("\"'")
    sys.exit("OPEN_ROUTER_API_KEY not found in .env")


def structured(key, model, system, user, schema, max_tokens=1024, effort="low"):
    """One chat call constrained to `schema`. Returns (parsed_json, cost_usd)."""
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "reasoning": {"effort": effort},
        "messages": [
            # Stable system prompt first so the provider can cache it across calls.
            {"role": "system", "content": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_schema", "json_schema": {"name": "result", "strict": True, "schema": schema}},
        "usage": {"include": True},
    }
    req = urllib.request.Request(
        URL,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "X-Title": "hacker-courses"},
    )
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                resp = json.load(r)
            break
        except urllib.error.HTTPError as e:
            # 429 and 5xx are transient; anything else is a bug in the request.
            if e.code != 429 and e.code < 500:
                raise RuntimeError(f"HTTP {e.code}: {e.read()[:300]!r}") from None
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(2 ** attempt)
    else:
        raise RuntimeError("gave up after retries")
    choice = resp["choices"][0]
    if choice.get("finish_reason") not in ("stop", "end_turn"):
        raise RuntimeError(f"finish_reason={choice.get('finish_reason')}")
    return json.loads(choice["message"]["content"]), resp.get("usage", {}).get("cost", 0.0) or 0.0
