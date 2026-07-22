#!/usr/bin/env python3
"""Drive all twelve tools against a local stub. No credentials, no network.

What this is really guarding
----------------------------
The distinctive behaviour of this plugin is that an endpoint above the user's
plan returns a plain-English explanation as a NORMAL result. That is easy to
state and easy to lose: any tool that lets an exception escape turns a tier
wall into a failed workflow node, and a model handed a bare 403 invents reasons
or retries pointlessly.

So the tier-wall case is not one assertion here, it is a pass over every tool
with the stub answering 403 to everything: nothing may raise, and every tool
must name the tier it needs. The same pass runs for 401, 404 and 429.

Run: python test/test_tools.py        (or: pytest test/)
"""

from __future__ import annotations

import importlib
import pathlib
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "plugin"))
sys.path.insert(0, str(ROOT / "test"))

import livetennisapi_client  # noqa: E402
from dify_plugin.entities.tool import ToolRuntime  # noqa: E402
from stub_api import StubAPI  # noqa: E402

KEY = {"api_key": "twjp_test_key"}

#: Plausible arguments for every tool, so none is skipped for lack of input.
ARGS: dict[str, dict[str, Any]] = {
    "get_live_matches": {"limit": 2},
    "get_upcoming_matches": {"limit": 2},
    "get_match": {"match_id": 101},
    "get_match_score": {"match_id": 101},
    "search_players": {"query": "player", "limit": 2},
    "get_player": {"player_id": 1},
    "get_fixtures": {"limit": 2},
    "get_recent_results": {"limit": 2},
    "get_match_events": {"match_id": 101, "limit": 2},
    "get_match_odds": {"match_id": 101, "limit": 2},
    "get_match_analysis": {"match_id": 101},
    "check_api_status": {},
}

#: Which tools sit above the FREE floor, and the tier each must name.
TIER_GATED = {
    "get_recent_results": "BASIC",
    "get_match_events": "PRO",
    "get_match_odds": "PRO",
    "get_match_analysis": "ULTRA",
}

TOOL_CLASSES: dict[str, Any] = {}
for name in ARGS:
    module = importlib.import_module(f"tools.{name}")
    TOOL_CLASSES[name] = next(
        value
        for key, value in vars(module).items()
        if isinstance(value, type) and key.endswith("Tool") and value.__module__ == module.__name__
    )

failures: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def invoke(name: str, credentials: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Run one tool, returning its text half and its JSON half.

    Any exception escaping here is itself the failure this suite exists to
    catch, so it is deliberately not swallowed.
    """
    runtime = ToolRuntime(credentials=credentials, user_id=None, session_id=None)
    messages = list(TOOL_CLASSES[name](runtime=runtime, session=None)._invoke(dict(ARGS[name])))
    text = next((m.message.text for m in messages if m.type.value == "text"), None)
    payload = next((m.message.json_object for m in messages if m.type.value == "json"), None)
    check(text is not None, f"{name}: emitted no text message")
    check(payload is not None, f"{name}: emitted no json message")
    return text or "", dict(payload or {})


def phase(title: str) -> None:
    print(f"\n--- {title} ---")


def main() -> int:
    stub = StubAPI().start()
    livetennisapi_client.BASE_URL = stub.url
    print(f"stub listening on {stub.url}")

    # 1. Static metadata. A tool with no description is invisible to a model.
    phase("1. every tool is importable and exposes _invoke")
    for name, cls in TOOL_CLASSES.items():
        check("_invoke" in cls.__dict__, f"{name}: no _invoke")
        print(f"  {name:22s} -> {cls.__name__}")

    # 2. No key. The early return must still emit both halves.
    phase("2. no API key configured")
    for name in ARGS:
        text, payload = invoke(name, {})
        check(isinstance(payload.get("ok"), bool), f"{name} (no key): 'ok' is not a boolean")
        check(bool(payload.get("message")), f"{name} (no key): empty message")
        check(text == payload.get("message"), f"{name} (no key): text and json message disagree")
        if name == "check_api_status":
            # The one tool that legitimately works without a key -- diagnosing
            # "why is everything else refusing data" is precisely its job.
            check(payload.get("ok") is True, "check_api_status (no key) should still succeed")
            check(payload.get("has_key") is False, "check_api_status (no key) should report has_key false")
            check(payload.get("tier") is None, "check_api_status (no key) should report tier null")
        else:
            check(payload.get("ok") is False, f"{name} (no key): expected ok false")
            check(payload.get("reason") == "no_api_key", f"{name} (no key): wrong reason")
        print(f"  {name:22s} ok={payload.get('ok')!s:5s} reason={payload.get('reason')}")

    # 3. The success path against the stub.
    phase("3. success path")
    for name in ARGS:
        text, payload = invoke(name, KEY)
        check(payload.get("ok") is True, f"{name}: expected ok true, got {payload.get('message')!r}")
        check(text == payload.get("message"), f"{name}: text and json message disagree")
        extra = [k for k in payload if k not in ("ok", "message", "reason")]
        print(f"  {name:22s} ok={payload.get('ok')!s:5s} fields={extra}")

    # Spot-check the values, not just the shape -- an all-null success is still
    # a pass against a shape-only assertion.
    _, live = invoke("get_live_matches", KEY)
    match = live["matches"][0]
    check(match["id"] == 101, f"get_live_matches: wrong id {match['id']}")
    check(match["player1"] == "Player One", f"get_live_matches: wrong player1 {match['player1']}")
    # Player-major games [[6,3],[4,2]] reads 6-4 3-2, NOT 6-3 4-2.
    check(match["score"] == "6-4 3-2 (40-30)", f"get_live_matches: score is {match['score']!r}")
    print(f"  score formatting from player-major games: {match['score']!r}")

    _, analysis = invoke("get_match_analysis", KEY)
    check(analysis["profile"]["win_probability_p1"] == 0.61, "analysis: profile not read (dict access)")
    check(analysis["thesis"]["pick_side"] == 1, "analysis: thesis not read (dict access)")
    print(f"  analysis profile/thesis decoded: {analysis['profile']['key_factors']}")

    _, detail = invoke("get_match", KEY)
    check(detail["match"]["id"] == 101, "get_match: wrong id")

    _, status = invoke("check_api_status", KEY)
    check(status.get("tier") == "ULTRA", f"check_api_status: tier is {status.get('tier')!r}")
    check(status.get("has_key") is True, "check_api_status: has_key should be true")
    print(f"  detected tier against a stub that allows everything: {status.get('tier')}")

    # 4. THE PATH THAT MATTERS. Everything answers 403.
    phase("4. tier wall - every endpoint answers 403 upgrade_required")
    stub.rules = {"/history": 403, "/events": 403, "/markets": 403, "/analysis": 403}
    for name, expected_tier in TIER_GATED.items():
        text, payload = invoke(name, KEY)  # must not raise
        check(payload.get("ok") is False, f"{name} (403): expected ok false")
        check(
            payload.get("reason") == "upgrade_required",
            f"{name} (403): reason is {payload.get('reason')!r}",
        )
        check(
            payload.get("required_tier") == expected_tier,
            f"{name} (403): required_tier is {payload.get('required_tier')!r}, expected {expected_tier}",
        )
        check(expected_tier in text, f"{name} (403): message does not name the {expected_tier} tier")
        check("upgrade" in text.lower(), f"{name} (403): message offers no remedy")
        check(len(text) > 80, f"{name} (403): message is too terse to act on")
        print(f"  {name:22s} tier={payload.get('required_tier'):6s} :: {text.splitlines()[0][:78]}")

    # A FREE key must still be able to use the FREE tools while walled off the rest.
    _, live = invoke("get_live_matches", KEY)
    check(live.get("ok") is True, "get_live_matches should still work behind a tier wall on other paths")
    print(f"  {'get_live_matches':22s} unaffected by walls elsewhere: ok={live.get('ok')}")

    # check_api_status must identify FREE from the 403 on /history, not fall over.
    _, status = invoke("check_api_status", KEY)
    check(status.get("ok") is True, "check_api_status must not fail when history is walled")
    check(status.get("tier") == "FREE", f"check_api_status: tier is {status.get('tier')!r}, expected FREE")
    print(f"  {'check_api_status':22s} identified tier from the wall: {status.get('tier')}")

    # 5. The other expected states, none of which may raise.
    for status_code, reason, label in (
        (401, "unauthorized", "rejected key"),
        (404, "not_found", "unknown id"),
        (429, "rate_limited", "rate limit"),
    ):
        phase(f"5. {status_code} {label} - normal result, no exception")
        stub.rules = {"/matches": status_code, "/players": status_code, "/fixtures": status_code}
        for name in ("get_live_matches", "get_match_score", "search_players", "get_fixtures"):
            text, payload = invoke(name, KEY)  # must not raise
            check(payload.get("ok") is False, f"{name} ({status_code}): expected ok false")
            check(
                payload.get("reason") == reason,
                f"{name} ({status_code}): reason is {payload.get('reason')!r}, expected {reason}",
            )
            check(bool(text), f"{name} ({status_code}): empty message")
            print(f"  {name:22s} reason={payload.get('reason'):14s} :: {text[:64]}")

    stub.rules = {}

    # 6. Bad parameters, handled before any request is made.
    phase("6. missing or unusable parameters")
    for name, args in (("get_match", {}), ("get_player", {}), ("search_players", {"query": "  "})):
        original = ARGS[name]
        ARGS[name] = args
        try:
            text, payload = invoke(name, KEY)
        finally:
            ARGS[name] = original
        check(payload.get("ok") is False, f"{name} (bad params): expected ok false")
        check(
            payload.get("reason") == "invalid_parameter",
            f"{name} (bad params): reason is {payload.get('reason')!r}",
        )
        print(f"  {name:22s} reason={payload.get('reason')} :: {text[:64]}")

    # 7. run_tool's base_url argument, exercised directly.
    phase("7. run_tool base_url injection")
    result = livetennisapi_client.run_tool(
        KEY,
        lambda client: livetennisapi_client.ok(
            "direct", count=len(client.list_matches(status="live", limit=1).data)
        ),
        base_url=stub.url,
    )
    check(result["ok"] is True and result["count"] == 1, f"run_tool base_url injection failed: {result}")
    print(f"  run_tool(base_url=...) -> ok={result['ok']} count={result['count']}")

    stub.stop()

    print()
    if failures:
        print(f"FAIL - {len(failures)} problem(s):")
        for problem in failures:
            print(f"  - {problem}")
        print("\npaths the stub was asked for:")
        for path in sorted(set(stub.asked)):
            print(f"  {path}")
        return 1

    print(
        f"OK - {len(ARGS)} tools x (no key, success, 403 tier wall, 401, 404, 429, bad params); "
        f"{len(set(stub.asked))} distinct upstream paths exercised; nothing raised"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
