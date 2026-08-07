"""Shared plumbing for every Live Tennis API tool.

Three things live here so that twelve tool files cannot drift apart:

1. **The client factory.** The API base URL is a module constant, not a
   credential. A user-settable base URL would make the plugin's network
   destination user-controlled, which is precisely the line Dify's submission
   requirements draw between "Low risk" (fixed, documented third-party HTTPS
   APIs) and higher. Tests inject a stub URL through ``base_url`` directly;
   nothing in the plugin UI can reach it.

2. **The formatters.** Prose for a model to read, plus the same facts as flat
   JSON for a workflow to read without re-parsing English. ``format_score`` in
   particular guards the one shape everyone gets wrong -- see below.

3. **``run_tool``, the guard.** The single place an API failure becomes a
   *normal* result. A tier wall is not an error: the key is valid, the plan
   simply does not include the endpoint, and there is a clear remedy. Handed a
   bare 403 a model invents reasons or retries pointlessly, so every expected
   failure returns prose naming the required tier instead. No tool raises.
"""

from __future__ import annotations

from collections.abc import Callable, Generator, Mapping
from itertools import zip_longest
from typing import Any

from livetennisapi import (
    AbuseThrottled,
    APIConnectionError,
    BadRequest,
    LiveTennisAPI,
    LiveTennisAPIError,
    NotFound,
    RateLimited,
    Unauthorized,
    UpgradeRequired,
)

#: Fixed and documented. Deliberately not user-configurable -- see module docstring.
BASE_URL = "https://api.livetennisapi.com/api/public/v1"

SIGNUP_URL = "https://livetennisapi.com/subscribe/free"
PRICING_URL = "https://livetennisapi.com/#pricing"

#: What each plan unlocks, phrased for a model to relay when a tier wall answers.
TIER_TABLE = (
    "Tiers: FREE = live and upcoming matches, scores, players, fixtures; "
    "BASIC adds completed results, head-to-head and the 1968-2022 results archive; "
    "PRO adds ranking tables and embeds market prices in a match detail; "
    "ULTRA adds match statistics and embeds model analysis in a match detail."
)

REQUEST_TIMEOUT = 30.0

#: The lifecycle values ``GET /matches`` accepts for ``status``.
MATCH_STATUSES = ("live", "upcoming", "completed")

#: The values ``GET /matches`` accepts for ``tour``. Sent lower-case.
TOURS = ("atp", "wta", "challenger", "itf", "juniors")

#: The tours of the 1968-2022 results archive -- a licensed historical corpus
#: with its own id space, which holds the ATP and WTA lineages (main draws,
#: qualifying and the ITF/futures tiers underneath each).
ARCHIVE_TOURS = ("atp", "wta")

#: The ranking systems ``GET /rankings`` publishes as full tables. ``utr`` is
#: deliberately absent: a rating is not a ranking and has no listing.
RANKING_SYSTEMS = ("atp", "wta", "itf_jt", "itf_mt", "itf_wt")


# -- client -------------------------------------------------------------------


def api_key_of(credentials: Mapping[str, Any] | None) -> str:
    """The configured key, or an empty string. Never raises on a missing dict."""
    if not credentials:
        return ""
    return str(credentials.get("api_key") or "").strip()


def make_client(credentials: Mapping[str, Any] | None, *, base_url: str | None = None) -> LiveTennisAPI:
    """Build a client bound to one key.

    ``auth_header`` is passed explicitly. The Live Tennis API authenticates on
    the ``x-api-key`` request header; the SDK's constructor default is
    ``"bearer"``, so leaving it unset sends ``Authorization: Bearer ...``
    instead. Naming it here means a change to the SDK's default cannot silently
    change what this plugin sends.

    ``base_url`` exists for the offline test stub only. It has no credential
    behind it, so a plugin user cannot redirect traffic anywhere.
    """
    return LiveTennisAPI(
        api_key=api_key_of(credentials),
        base_url=base_url or BASE_URL,
        timeout=REQUEST_TIMEOUT,
        auth_header="x-api-key",
    )


def list_matches(client: LiveTennisAPI, *, status: str, tour: str | None, limit: int) -> Any:
    """``GET /matches`` with the documented ``status``, ``tour`` and ``limit``.

    Until livetennisapi 1.3.0 the SDK's ``list_matches`` had no ``tour``
    keyword and this function carried a request-layer shim for it. The
    dependency floor is now 1.3.0, so the shim is gone -- this stays as the
    one seam the tools call through, and ``tour`` is only sent when set.
    """
    if not tour:
        return client.list_matches(status=status, limit=limit)
    return client.list_matches(status=status, tour=tour, limit=limit)


# -- formatters ---------------------------------------------------------------


def _n(value: Any) -> Any:
    """Normalise absent values to ``None`` so the JSON shape stays stable."""
    return None if value is None else value


def dash(value: Any) -> Any:
    """``-`` for an absent value, so prose never prints a bare ``None``."""
    return "-" if value is None else value


def _iso(value: Any) -> str | None:
    """Datetimes as ISO strings; anything else as-is. JSON has no datetime."""
    if value is None:
        return None
    isoformat = getattr(value, "isoformat", None)
    return isoformat() if callable(isoformat) else str(value)


def format_score(score: Any) -> str:
    """Render a score as ``6-4 3-6 2-1 (40-30)``.

    ``games`` is **player-major** -- ``[[6, 3, 2], [4, 6, 1]]`` reads 6-4, 3-6,
    2-1 -- so the sets come from zipping the two lists, never from iterating
    one of them. Indexing it the other way is the single most common mistake
    against this API, and it already shipped as a real bug in a sibling
    integration. ``zip_longest`` rather than ``zip``: a set in progress leaves
    one side shorter and ``zip`` would silently drop the set being played.

    Mirrors ``_format_score`` in the livetennisapi SDK's CLI, which is private
    and so cannot be imported.
    """
    if score is None:
        return "-"
    parts: list[str] = []
    games = getattr(score, "games", None) or []
    if len(games) >= 2 and isinstance(games[0], list) and isinstance(games[1], list):
        for a, b in zip_longest(games[0], games[1], fillvalue="-"):
            parts.append(f"{a}-{b}")
    elif getattr(score, "sets", None):
        sets = score.sets or []
        if len(sets) >= 2:
            parts.append(f"{sets[0]}-{sets[1]}")

    points = getattr(score, "points", None) or []
    if len(points) >= 2:
        parts.append(f"({points[0]}-{points[1]})")
    return " ".join(parts) or "-"


def _player_names(match: Any) -> tuple[str, str]:
    """The two players' names, or ``?`` each.

    ``Match.players`` is a **dict** keyed ``p1``/``p2`` holding ``Player``
    objects -- a dict of objects, not an object of objects. Reaching for
    ``players.p1`` yields nothing and quietly renders every match as "? vs ?".
    """
    players = getattr(match, "players", None)
    if not isinstance(players, Mapping):
        return ("?", "?")
    return (
        getattr(players.get("p1"), "name", None) or "?",
        getattr(players.get("p2"), "name", None) or "?",
    )


def summarise(match: Any) -> str:
    """Compact one-line-per-fact match summary -- token-efficient to read."""
    p1, p2 = _player_names(match)
    score = getattr(match, "score", None)
    server = getattr(score, "server", None)
    round_ = getattr(match, "round", None)
    lines = [
        f"[{getattr(match, 'id', None)}] {getattr(match, 'tournament', None) or 'Unknown event'}"
        + (f" - {round_}" if round_ else ""),
        f"  {p1}{' (serving)' if server == 1 else ''} vs {p2}{' (serving)' if server == 2 else ''}",
        f"  Score: {format_score(score)}",
    ]
    surface = getattr(match, "surface", None)
    if surface:
        lines.append(f"  Surface: {surface}{' (indoor)' if getattr(match, 'indoor', None) else ''}")
    status = getattr(match, "status", None)
    if status and status != "live":
        lines.append(f"  Status: {status}")
    winner = getattr(match, "winner", None)
    if winner:
        lines.append(f"  Winner: {p1 if winner == 1 else p2}")
    win_probability = getattr(score, "win_probability_p1", None)
    if win_probability is not None:
        lines.append(f"  Model win probability ({p1}): {win_probability * 100:.1f}%")
    return "\n".join(lines)


def match_out(match: Any) -> dict[str, Any]:
    """One match as flat JSON. Every field nullable -- the API allows gaps."""
    p1, p2 = _player_names(match)
    score = getattr(match, "score", None)
    return {
        "id": _n(getattr(match, "id", None)),
        "tournament": _n(getattr(match, "tournament", None)),
        "round": _n(getattr(match, "round", None)),
        "player1": None if p1 == "?" else p1,
        "player2": None if p2 == "?" else p2,
        "score": format_score(score),
        "status": _n(getattr(match, "status", None)),
        "surface": _n(getattr(match, "surface", None)),
        "indoor": _n(getattr(match, "indoor", None)),
        "serving": _n(getattr(score, "server", None)),
        "winner": _n(getattr(match, "winner", None)),
        "win_probability_p1": _n(getattr(score, "win_probability_p1", None)),
    }


def player_out(player: Any) -> dict[str, Any]:
    return {
        "id": _n(getattr(player, "id", None)),
        "name": _n(getattr(player, "name", None)),
        "country": _n(getattr(player, "country", None)),
        "ranking": _n(getattr(player, "ranking", None)),
        "ranking_points": _n(getattr(player, "ranking_points", None)),
        "ranking_movement": _n(getattr(player, "ranking_movement", None)),
        "hand": _n(getattr(player, "hand", None)),
        "birthday": _iso(getattr(player, "birthday", None)),
        "tour": _n(getattr(player, "tour", None)),
    }


def fixture_out(fixture: Any) -> dict[str, Any]:
    return {
        "event_date": _iso(getattr(fixture, "event_date", None)),
        "tournament": _n(getattr(fixture, "tournament", None)),
        "round": _n(getattr(fixture, "round", None)),
        "player1": _n(getattr(fixture, "player1_name", None)),
        "player2": _n(getattr(fixture, "player2_name", None)),
    }


def price_out(price: Any) -> dict[str, Any]:
    return {
        "side": _n(getattr(price, "side", None)),
        "mid": _n(getattr(price, "mid", None)),
        "bid": _n(getattr(price, "bid", None)),
        "ask": _n(getattr(price, "ask", None)),
        "timestamp": _iso(getattr(price, "timestamp", None)),
    }


def _participant_out(participant: Any) -> dict[str, Any]:
    """One side of an archive result. ``player_id`` is the corpus person id
    (joins ``get_archive_players`` rows within the same tour), never a roster id."""
    return {
        "name": _n(getattr(participant, "name", None)),
        "country": _n(getattr(participant, "country", None)),
        "rank": _n(getattr(participant, "rank", None)),
        "seed": _n(getattr(participant, "seed", None)),
        "player_id": _n(getattr(participant, "player_id", None)),
    }


def archive_match_out(row: Any) -> dict[str, Any]:
    """One 1968-2022 archive result. Winner/loser-shaped, as recorded at source.

    ``event_date`` is the TOURNAMENT START date -- per-match dates do not exist
    in this era's records, and none are invented.
    """
    return {
        "id": _n(getattr(row, "id", None)),
        "tour": _n(getattr(row, "tour", None)),
        "tournament": _n(getattr(row, "tournament", None)),
        "level": _n(getattr(row, "level", None)),
        "surface": _n(getattr(row, "surface", None)),
        "event_date": _iso(getattr(row, "event_date", None)),
        "round": _n(getattr(row, "round", None)),
        "best_of": _n(getattr(row, "best_of", None)),
        "winner": _participant_out(getattr(row, "winner", None)),
        "loser": _participant_out(getattr(row, "loser", None)),
        "score": _n(getattr(row, "score", None)),
        "outcome": _n(getattr(row, "outcome", None)),
    }


def archive_player_out(bio: Any) -> dict[str, Any]:
    """One archive player bio. ``None`` fields are the era's silence, not gaps."""
    return {
        "id": _n(getattr(bio, "id", None)),
        "tour": _n(getattr(bio, "tour", None)),
        "name": _n(getattr(bio, "name", None)),
        "hand": _n(getattr(bio, "hand", None)),
        "dob": _iso(getattr(bio, "dob", None)),
        "country": _n(getattr(bio, "country", None)),
        "height_cm": _n(getattr(bio, "height_cm", None)),
        "career_high_rank": _n(getattr(bio, "career_high_rank", None)),
        "career_high_date": _iso(getattr(bio, "career_high_date", None)),
    }


def ranking_out(record: Any) -> dict[str, Any]:
    """One ranking-table row. ``player_id`` may be null for players outside the
    roster -- the published table has no silent holes, so the name always rides."""
    return {
        "rank": _n(getattr(record, "rank", None)),
        "player_id": _n(getattr(record, "player_id", None)),
        "player_name": _n(getattr(record, "player_name", None)),
        "system": _n(getattr(record, "system", None)),
        "points": _n(getattr(record, "points", None)),
        "previous_rank": _n(getattr(record, "previous_rank", None)),
        "rank_movement": _n(getattr(record, "rank_movement", None)),
        "effective_date": _iso(getattr(record, "effective_date", None)),
    }


# -- parameters ---------------------------------------------------------------
#
# Dify hands tool parameters through untyped: a "number" arrives as int, float
# or str depending on whether a user typed it, a workflow computed it, or a
# model filled it in. Coercing in one place stops twelve tools each inventing
# their own half-correct version.


def choice_param(value: Any, allowed: tuple[str, ...], default: str | None) -> str | None:
    """One of ``allowed``, case-folded, or ``default`` for anything else.

    A model that fills in "ATP", "Live" or a stray "any" must not turn into a
    query string the API rejects, so an unrecognised value falls back rather
    than being forwarded.
    """
    if value is None:
        return default
    candidate = str(value).strip().lower()
    if candidate in allowed:
        return candidate
    return default


def int_param(value: Any, default: int, *, minimum: int = 1, maximum: int = 200) -> int:
    """A bounded int, falling back to ``default`` on anything unusable.

    Clamped rather than rejected: a model asking for 500 matches means "as many
    as you can", and the API's own ceiling is 200.
    """
    if value is None or value == "":
        return default
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


def required_id(value: Any) -> int | None:
    """An id parameter, or ``None`` when it is missing or not a number."""
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


# -- results ------------------------------------------------------------------


def ok(message: str, **data: Any) -> dict[str, Any]:
    """A result that carried data."""
    return {"ok": True, "message": message, **data}


def fail(message: str, reason: str, **extra: Any) -> dict[str, Any]:
    """A result that carried no data.

    Not an exception, and not flagged as an error. Every case that reaches here
    -- a tier wall, a rejected key, an unknown id, a rate limit -- is a normal
    state with a remedy the message spells out.
    """
    return {"ok": False, "message": message, "reason": reason, **extra}


def missing_id(name: str) -> dict[str, Any]:
    """The result for an absent or unparseable id parameter."""
    return fail(
        f"The '{name}' parameter is required and must be a number. Match ids come from "
        "get_matches; player ids come from search_players.",
        "invalid_parameter",
    )


NO_KEY_MESSAGE = (
    "No API key is configured for this plugin. Add your Live Tennis API key in the "
    "plugin's settings. A free key, no card required, is available at " + SIGNUP_URL
)


def run_tool(
    credentials: Mapping[str, Any] | None,
    body: Callable[[LiveTennisAPI], dict[str, Any]],
    *,
    base_url: str | None = None,
) -> dict[str, Any]:
    """Run one tool body, turning every expected failure into a normal result.

    ``body`` receives a client and returns the finished result dict, built with
    ``ok()`` or ``fail()``.

    The ``UpgradeRequired`` branch is the point of this function. The API
    answers a tier wall with a bare ``403 {"error": "upgrade_required"}``; the
    SDK infers which tier the endpoint needs, and this turns that into a
    sentence a model can relay to the user rather than a status code it will
    guess about.

    Nothing here re-raises. A Dify workflow node that raises stops the flow,
    and none of these states is worth stopping a flow over.
    """
    if not api_key_of(credentials):
        return fail(NO_KEY_MESSAGE, "no_api_key")

    client = make_client(credentials, base_url=base_url)
    try:
        return body(client)
    except UpgradeRequired as exc:
        # The API answers a tier wall with a bare 403 and the SDK infers the
        # tier where it can. When it cannot, the sentence must still read as
        # English -- "requires the a higher plan" is what a naive f-string
        # interpolation of the fallback produces.
        needed = f"the {exc.required_tier} plan" if exc.required_tier else "a higher plan"
        return fail(
            f"This data requires {needed}, and the configured API key is on a lower "
            f"tier. Nothing is wrong with the key - the endpoint is simply not included in "
            f"the current plan. Upgrade at {PRICING_URL}\n\n{TIER_TABLE}",
            "upgrade_required",
            required_tier=exc.required_tier,
        )
    except Unauthorized:
        return fail(
            "The API key was rejected - it is missing, unknown, or disabled. Check the key "
            "configured for this plugin. Keys are at https://livetennisapi.com",
            "unauthorized",
        )
    except NotFound:
        return fail(
            "No data found for that request. The id may be wrong, or there may be no data yet.",
            "not_found",
        )
    except BadRequest as exc:
        # One 400 deserves better than the backstop: a name fragment matching
        # more than one player. The API sends the candidates, and relaying
        # them lets a model simply re-ask with the full name.
        if exc.error_code == "ambiguous_name":
            candidates = []
            if isinstance(exc.body, Mapping):
                candidates = [str(c) for c in exc.body.get("candidates") or []]
            listed = f" Candidates: {'; '.join(candidates)}." if candidates else ""
            return fail(
                f"That player name matches more than one person - give a fuller name.{listed}",
                "ambiguous_name",
                candidates=candidates,
            )
        return fail(f"The Live Tennis API rejected the request: {exc}", "request_failed")
    except AbuseThrottled as exc:
        # Must precede RateLimited (its parent class). "Wait a minute" is
        # exactly the wrong advice here: the key is blocked for 24 hours for
        # repeatedly hammering through its quota, and the remedy is to fix
        # the loop that did it, not to retry.
        until = f" The block lifts at {exc.retry_at.isoformat()}." if exc.retry_at is not None else ""
        return fail(
            "This API key is temporarily blocked (about 24 hours) for repeatedly exceeding "
            f"its quota.{until} Do not retry until then - fix the polling or retry loop "
            "that exhausted the quota, or upgrade the plan at " + PRICING_URL,
            "abuse_throttled",
            retry_at_epoch=exc.retry_at_epoch,
        )
    except RateLimited as exc:
        if exc.scope == "day":
            # The daily cap, not the minute window. `resets_at` is an absolute
            # instant derived from a local midnight -- not a UTC one -- so the
            # ISO timestamp is relayed as-is rather than paraphrased.
            resets = _iso(exc.resets_at)
            when = f" It resets at {resets}." if resets else ""
            quota = f" ({exc.limit_per_day}/day)" if exc.limit_per_day is not None else ""
            return fail(
                f"The daily request quota for this plan{quota} is used up.{when} "
                f"A higher plan raises the daily allowance: {PRICING_URL}",
                "rate_limited",
                scope="day",
                limit_per_day=exc.limit_per_day,
                resets_at=resets,
                retry_after=exc.retry_after,
            )
        wait = f" Retry in about {exc.retry_after:g}s." if exc.retry_after is not None else ""
        return fail(f"Rate limit reached for this plan.{wait}", "rate_limited", retry_after=exc.retry_after)
    except APIConnectionError as exc:
        # A genuine transport fault, unlike everything above. Returned rather
        # than raised so a workflow can branch on `ok` instead of dying, but
        # `reason` keeps it distinguishable from the expected states.
        return fail(f"Could not reach the Live Tennis API: {exc}", "connection_error")
    except LiveTennisAPIError as exc:
        # Backstop for the statuses with no bespoke branch above -- 400 and
        # 5xx. Without it those would escape and fail the workflow node, which
        # is exactly the behaviour this function exists to prevent.
        return fail(f"The Live Tennis API request failed: {exc}", "request_failed")
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            close()


def emit(tool: Any, payload: Mapping[str, Any]) -> Generator[Any, None, None]:
    """Yield a result as both prose and JSON.

    Two messages, always in this order and always both: the text is what a
    model reads, the JSON is what a workflow reads without re-parsing English.
    Keeping it in one helper is what stops a tool from emitting only one half.
    """
    yield tool.create_text_message(str(payload.get("message", "")))
    yield tool.create_json_message(dict(payload))
