#!/usr/bin/env python3
"""Drive all six tools against a local stub. No credentials, no network.

What this is really guarding
----------------------------
The distinctive behaviour of this plugin is that every expected API failure --
a rejected key, an unknown id, a rate limit, a tier wall -- comes back as a
NORMAL result with a plain-English explanation. That is easy to state and easy
to lose: any tool that lets an exception escape turns an expected state into a
failed workflow node, and a model handed a bare status code invents reasons or
retries pointlessly.

So the failure cases are not one assertion here, they are a pass over every
tool with the stub answering 403, 401, 404 and 429 to everything: nothing may
raise, and every tool must explain itself.

Since 0.0.2 the suite also asserts the wire itself: the API key must travel in
the ``x-api-key`` request header -- not ``Authorization: Bearer`` -- on every
request, so a client-library default can never silently move it back.

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

API_KEY = "twjp_test_key"
KEY = {"api_key": API_KEY}

#: Plausible arguments for every tool, so none is skipped for lack of input.
ARGS: dict[str, dict[str, Any]] = {
    "get_matches": {"status": "live", "limit": 2},
    "get_match": {"match_id": 101},
    "get_match_score": {"match_id": 101},
    "search_players": {"query": "player", "limit": 2},
    "get_player": {"player_id": 1},
    "get_fixtures": {"limit": 2},
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


def invoke(
    name: str, credentials: dict[str, Any], args: dict[str, Any] | None = None
) -> tuple[str, dict[str, Any]]:
    """Run one tool, returning its text half and its JSON half.

    Any exception escaping here is itself the failure this suite exists to
    catch, so it is deliberately not swallowed.
    """
    runtime = ToolRuntime(credentials=credentials, user_id=None, session_id=None)
    tool_args = dict(ARGS[name]) if args is None else dict(args)
    messages = list(TOOL_CLASSES[name](runtime=runtime, session=None)._invoke(tool_args))
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

    # 1. Static metadata. A tool with no _invoke is invisible to Dify.
    phase("1. every tool is importable and exposes _invoke")
    for name, cls in TOOL_CLASSES.items():
        check("_invoke" in cls.__dict__, f"{name}: no _invoke")
        print(f"  {name:18s} -> {cls.__name__}")

    # 2. No key. The early return must still emit both halves.
    phase("2. no API key configured")
    for name in ARGS:
        text, payload = invoke(name, {})
        check(payload.get("ok") is False, f"{name} (no key): expected ok false")
        check(payload.get("reason") == "no_api_key", f"{name} (no key): wrong reason")
        check(bool(payload.get("message")), f"{name} (no key): empty message")
        check(text == payload.get("message"), f"{name} (no key): text and json message disagree")
        print(f"  {name:18s} ok={payload.get('ok')!s:5s} reason={payload.get('reason')}")
    check(not stub.asked, f"a keyless call reached the network: {stub.asked}")

    # 3. The success path against the stub.
    phase("3. success path")
    for name in ARGS:
        text, payload = invoke(name, KEY)
        check(payload.get("ok") is True, f"{name}: expected ok true, got {payload.get('message')!r}")
        check(text == payload.get("message"), f"{name}: text and json message disagree")
        extra = [k for k in payload if k not in ("ok", "message", "reason")]
        print(f"  {name:18s} ok={payload.get('ok')!s:5s} fields={extra}")

    # Spot-check the values, not just the shape -- an all-null success is still
    # a pass against a shape-only assertion.
    _, live = invoke("get_matches", KEY)
    match = live["matches"][0]
    check(match["id"] == 101, f"get_matches: wrong id {match['id']}")
    check(match["player1"] == "Player One", f"get_matches: wrong player1 {match['player1']}")
    # Player-major games [[6,3],[4,2]] reads 6-4 3-2, NOT 6-3 4-2.
    check(match["score"] == "6-4 3-2 (40-30)", f"get_matches: score is {match['score']!r}")
    check(live.get("status") == "live", f"get_matches: echoed status {live.get('status')!r}")
    print(f"  score formatting from player-major games: {match['score']!r}")

    # get_match must surface the embedded, tier-gated blocks when present.
    text, detail = invoke("get_match", KEY)
    check(detail["match"]["id"] == 101, "get_match: wrong id")
    market = detail.get("market") or {}
    check(
        (market.get("prices") or [{}])[0].get("mid") == 0.6,
        f"get_match: embedded market not surfaced ({market!r})",
    )
    analysis = detail.get("analysis") or {}
    check(
        analysis.get("win_probability_p1") == 0.61,
        f"get_match: embedded analysis not surfaced ({analysis!r})",
    )
    check("Market" in text, "get_match: prose omits the market block")
    check("Model analysis" in text, "get_match: prose omits the analysis block")
    print(f"  get_match embeds market + analysis: mid={market['prices'][0]['mid']}, wp={analysis['win_probability_p1']}")

    # 4. THE WIRE. Every request so far must have authenticated via x-api-key.
    phase("4. the API key travels in x-api-key, never Authorization: Bearer")
    check(bool(stub.seen_headers), "stub recorded no request headers")
    for seen in stub.seen_headers:
        check(
            seen["x-api-key"] == API_KEY,
            f"{seen['path']}: x-api-key header is {seen['x-api-key']!r}",
        )
        check(
            seen["authorization"] is None,
            f"{seen['path']}: unexpected Authorization header {seen['authorization']!r}",
        )
    print(f"  {len(stub.seen_headers)} request(s) checked: x-api-key present, Authorization absent")

    # 5. get_matches parameters: forwarded when valid, fallback when not.
    phase("5. get_matches status and tour handling")
    stub.asked.clear()
    _, completed = invoke("get_matches", KEY, {"status": "completed", "limit": 2})
    check(completed.get("ok") is True, "get_matches (completed): expected ok true")
    check(completed.get("status") == "completed", "get_matches: status not echoed")
    check(
        any("status=completed" in path for path in stub.asked),
        f"get_matches: status=completed never hit the wire ({stub.asked})",
    )
    print(f"  status=completed forwarded: {stub.asked[-1]}")

    stub.asked.clear()
    _, atp = invoke("get_matches", KEY, {"status": "live", "tour": "ATP", "limit": 2})
    check(atp.get("ok") is True, "get_matches (tour): expected ok true")
    check(atp.get("tour") == "atp", f"get_matches: tour echoed as {atp.get('tour')!r}, expected 'atp'")
    check(
        any("tour=atp" in path for path in stub.asked),
        f"get_matches: tour=atp never hit the wire ({stub.asked}) -- dropped silently?",
    )
    print(f"  tour='ATP' case-folded and forwarded: {stub.asked[-1]}")

    _, fallback = invoke("get_matches", KEY, {"status": "finished", "tour": "nfl", "limit": 2})
    check(fallback.get("ok") is True, "get_matches (bad values): expected ok true")
    check(fallback.get("status") == "live", "get_matches: bad status should fall back to live")
    check(fallback.get("tour") is None, "get_matches: bad tour should fall back to none")
    print(f"  unrecognised values fall back: status={fallback.get('status')!r} tour={fallback.get('tour')!r}")

    # 6. The tier wall. Everything answers 403 upgrade_required; nothing raises.
    phase("6. tier wall - every endpoint answers 403 upgrade_required")
    stub.rules = {"/matches": 403, "/players": 403, "/fixtures": 403}
    for name in ARGS:
        text, payload = invoke(name, KEY)  # must not raise
        check(payload.get("ok") is False, f"{name} (403): expected ok false")
        check(
            payload.get("reason") == "upgrade_required",
            f"{name} (403): reason is {payload.get('reason')!r}",
        )
        check("upgrade" in text.lower(), f"{name} (403): message offers no remedy")
        check("plan" in text.lower(), f"{name} (403): message does not talk about plans")
        check(len(text) > 80, f"{name} (403): message is too terse to act on")
        print(f"  {name:18s} reason={payload.get('reason')} :: {text.splitlines()[0][:72]}")

    # 7. The other expected states, none of which may raise.
    for status_code, reason, label in (
        (401, "unauthorized", "rejected key"),
        (404, "not_found", "unknown id"),
        (429, "rate_limited", "rate limit"),
    ):
        phase(f"7. {status_code} {label} - normal result, no exception")
        stub.rules = {"/matches": status_code, "/players": status_code, "/fixtures": status_code}
        for name in ARGS:
            text, payload = invoke(name, KEY)  # must not raise
            check(payload.get("ok") is False, f"{name} ({status_code}): expected ok false")
            check(
                payload.get("reason") == reason,
                f"{name} ({status_code}): reason is {payload.get('reason')!r}, expected {reason}",
            )
            check(bool(text), f"{name} ({status_code}): empty message")
            print(f"  {name:18s} reason={payload.get('reason'):14s} :: {text[:60]}")

    stub.rules = {}

    # 8. Bad parameters, handled before any request is made.
    phase("8. missing or unusable parameters")
    stub.asked.clear()
    for name, args in (
        ("get_match", {}),
        ("get_match", {"match_id": "not-a-number"}),
        ("get_player", {}),
        ("search_players", {"query": "  "}),
    ):
        text, payload = invoke(name, KEY, args)
        check(payload.get("ok") is False, f"{name} (bad params {args!r}): expected ok false")
        check(
            payload.get("reason") == "invalid_parameter",
            f"{name} (bad params {args!r}): reason is {payload.get('reason')!r}",
        )
        print(f"  {name:18s} {str(args):28s} reason={payload.get('reason')}")
    check(not stub.asked, f"a bad-parameter call reached the network: {stub.asked}")

    # 9. run_tool's base_url argument, exercised directly.
    phase("9. run_tool base_url injection")
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
        f"x-api-key asserted on the wire; nothing raised"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
