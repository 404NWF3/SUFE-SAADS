from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

import httpx


DEFAULT_CONFIG = Path.home() / ".openclaw" / "openclaw.json"
DEFAULT_AGENT_ID = "llm-security-intel"
DEFAULT_GATEWAY_URL = "http://127.0.0.1:18789"


def load_openclaw_config(config_path: Path) -> dict[str, Any]:
    return json.loads(config_path.read_text(encoding="utf-8-sig"))


def derive_gateway_url(config: dict[str, Any]) -> str:
    gateway = config.get("gateway") or {}
    bind = gateway.get("bind") or "loopback"
    port = gateway.get("port") or 18789
    host = "127.0.0.1" if bind in {"loopback", "localhost", "0.0.0.0", "::"} else str(bind)
    return f"http://{host}:{port}"


def resolve_token(config: dict[str, Any]) -> str:
    env_token = os.getenv("OPENCLAW_GATEWAY_TOKEN")
    if env_token:
        return env_token
    gateway = config.get("gateway") or {}
    auth = gateway.get("auth") or {}
    token = auth.get("token")
    if token:
        return str(token)
    raise RuntimeError("No Gateway token found. Set OPENCLAW_GATEWAY_TOKEN or gateway.auth.token.")


def probe_models(client: httpx.Client, gateway_url: str, token: str) -> list[str]:
    response = client.get(
        f"{gateway_url.rstrip('/')}/v1/models",
        headers={"Authorization": f"Bearer {token}"},
        timeout=httpx.Timeout(10.0, read=10.0),
    )
    response.raise_for_status()
    payload = response.json()
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, list):
        raise RuntimeError(f"/v1/models returned unexpected payload: {payload!r}")
    return [str(item["id"]) for item in data if isinstance(item, dict) and item.get("id")]


def flush_event(data_lines: list[str]) -> dict[str, Any] | str | None:
    if not data_lines:
        return None
    raw = "\n".join(data_lines)
    data_lines.clear()
    if raw == "[DONE]":
        return raw
    return json.loads(raw)


def stream_response(
    client: httpx.Client,
    *,
    gateway_url: str,
    token: str,
    agent_id: str,
    session_key: str,
    prompt: str,
) -> str:
    final_text = ""
    with client.stream(
        "POST",
        f"{gateway_url.rstrip('/')}/v1/responses",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "text/event-stream",
            "Content-Type": "application/json",
            "x-openclaw-agent-id": agent_id,
            "x-openclaw-session-key": session_key,
        },
        json={
            "model": "openclaw",
            "stream": True,
            "input": prompt,
        },
        timeout=httpx.Timeout(30.0, read=120.0),
    ) as response:
        response.raise_for_status()
        data_lines: list[str] = []
        for raw_line in response.iter_lines():
            line = raw_line.rstrip("\r")
            if not line:
                event = flush_event(data_lines)
                if event is None:
                    continue
                if event == "[DONE]":
                    print("[DONE]")
                    break
                event_type = str(event.get("type") or "")
                print(f"event={event_type}")
                if event_type == "response.output_text.delta":
                    delta = str(event.get("delta") or "")
                    if delta:
                        sys.stdout.write(delta)
                        sys.stdout.flush()
                elif event_type == "response.output_text.done":
                    final_text = str(event.get("text") or final_text)
                    print()
                elif event_type == "response.completed":
                    response_payload = event.get("response") or {}
                    output = response_payload.get("output") or []
                    for item in output:
                        if not isinstance(item, dict):
                            continue
                        content = item.get("content") or []
                        for part in content:
                            if isinstance(part, dict) and part.get("type") == "output_text":
                                final_text = str(part.get("text") or final_text)
                continue
            if line.startswith(":"):
                continue
            if line.startswith("data:"):
                data_lines.append(line[5:].lstrip())
    return final_text


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test OpenClaw HTTP Responses.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to openclaw.json")
    parser.add_argument("--gateway-url", default=None, help="Override Gateway base URL")
    parser.add_argument("--agent-id", default=DEFAULT_AGENT_ID, help="OpenClaw agent id")
    parser.add_argument(
        "--prompt",
        default="请只回复一行：OPENCLAW_FLOW_OK",
        help="Prompt sent to OpenClaw",
    )
    parser.add_argument("--session-key", default=None, help="Optional explicit session key")
    args = parser.parse_args()

    config_path = Path(args.config).expanduser()
    config = load_openclaw_config(config_path)
    gateway_url = args.gateway_url or derive_gateway_url(config) or DEFAULT_GATEWAY_URL
    token = resolve_token(config)
    session_key = args.session_key or f"smoke:{args.agent_id}:{uuid.uuid4().hex[:8]}"

    print(f"config={config_path}")
    print(f"gateway_url={gateway_url}")
    print(f"agent_id={args.agent_id}")
    print(f"session_key={session_key}")

    with httpx.Client() as client:
        model_ids = probe_models(client, gateway_url, token)
        print("models=", ", ".join(model_ids))
        print("stream_start")
        final_text = stream_response(
            client,
            gateway_url=gateway_url,
            token=token,
            agent_id=args.agent_id,
            session_key=session_key,
            prompt=args.prompt,
        )
        print("\nstream_end")
        print(f"final_text={final_text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
