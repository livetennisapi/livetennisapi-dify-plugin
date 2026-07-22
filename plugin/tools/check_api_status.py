from __future__ import annotations

from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from livetennisapi import (
    LiveTennisAPI,
    LiveTennisAPIError,
    NotFound,
    Unauthorized,
    UpgradeRequired,
)

from livetennisapi_client import SIGNUP_URL, api_key_of, emit, fail, make_client, ok

TIER_SUMMARY = (
    "FREE  = live & upcoming matches, scores, players, fixtures\n"
    "BASIC = + historical results\n"
    "PRO   = + match events and market prices\n"
    "ULTRA = + model analysis, win probability and the live feed"
)


def _detect_tier(client: LiveTennisAPI) -> str | None:
    """Probe upward to discover the plan without asking the user.

    Returns ``None`` when the key is rejected outright.

    Two traps, both of which a naive port falls into:

    * ``FREE`` stops short of history, so ``UpgradeRequired`` on
      ``/history/matches`` *identifies* FREE and must be caught. Uncaught it
      escapes and reports a perfectly valid free key as unreachable.
    * ``NotFound`` on a higher endpoint is evidence *of* entitlement, not
      against it -- the call was allowed, that match simply has no data. Only
      ``UpgradeRequired`` proves a tier is not held.
    """
    try:
        client.list_matches(status="completed", limit=1)
    except Unauthorized:
        return None

    tier = "BASIC"
    history = None
    try:
        history = client.list_completed_matches(limit=1)
    except UpgradeRequired:
        return "FREE"

    match_id = history.data[0].id if history and history.data else None
    if match_id is None:
        return tier

    try:
        client.list_match_events(match_id, limit=1)
        tier = "PRO"
    except NotFound:
        tier = "PRO"
    except UpgradeRequired:
        return tier

    try:
        client.get_match_analysis(match_id)
        tier = "ULTRA"
    except NotFound:
        tier = "ULTRA"
    except UpgradeRequired:
        pass
    return tier


class CheckApiStatusTool(Tool):
    """The one tool that works without a key.

    Diagnosing "why is everything else refusing data" is precisely its job, so
    a missing key is reported as a fact about the configuration rather than
    treated as a failure.
    """

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        credentials = self.runtime.credentials
        has_key = bool(api_key_of(credentials))

        try:
            with make_client(credentials) as client:
                health = client.health()
                status = health.get("status")
                version = health.get("version")

                if not has_key:
                    yield from emit(
                        self,
                        ok(
                            f"API is reachable (status: {status}, version: {version}).\n"
                            "No API key is configured, so only this check will work. Add your key "
                            f"in the plugin settings - a free key, no card, is at {SIGNUP_URL}",
                            reachable=True,
                            api_version=version,
                            tier=None,
                            has_key=False,
                        ),
                    )
                    return

                tier = _detect_tier(client)

            if tier is None:
                yield from emit(
                    self,
                    ok(
                        "API is reachable, but the configured key was rejected (unauthorized).",
                        reachable=True,
                        api_version=version,
                        tier=None,
                        has_key=True,
                    ),
                )
                return

            yield from emit(
                self,
                ok(
                    f"API is reachable (status: {status}, version: {version}).\n"
                    f"The configured key appears to be on the {tier} plan.\n\n{TIER_SUMMARY}",
                    reachable=True,
                    api_version=version,
                    tier=tier,
                    has_key=True,
                ),
            )
        except LiveTennisAPIError as exc:
            yield from emit(
                self,
                fail(f"Could not reach the Live Tennis API: {exc}", "connection_error", reachable=False),
            )
