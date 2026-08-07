"""A local stand-in for the Live Tennis API.

Modelled on the MCP server's stub (../../livetennisapi-mcp/test/tools-output.mjs)
so both integrations are proved against the same shapes. No credentials, no
network: the tests bind this to 127.0.0.1 and point the plugin at it.

Routing is by path shape rather than an exact table, which keeps the stub
honest -- it answers whatever the SDK actually asks for, and `asked` records
every path so an unexpected 404 is visible instead of mysterious.
"""

from __future__ import annotations

import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

MATCH: dict[str, Any] = {
    "id": 101,
    "tournament": "Test Open",
    "round": "QF",
    "status": "live",
    "surface": "hard",
    "indoor": False,
    "winner": None,
    "players": {"p1": {"id": 1, "name": "Player One"}, "p2": {"id": 2, "name": "Player Two"}},
    "score": {
        "sets": [1, 0],
        "server": 1,
        "is_tiebreak": False,
        "win_probability_p1": 0.61,
        # Player-major: [[p1 per set], [p2 per set]] -> 6-4, 3-2.
        "games": [[6, 3], [4, 2]],
        "points": ["40", "30"],
    },
    # Embedded, tier-gated blocks. Since 0.0.2 the API embeds these in a match
    # detail rather than serving them from their own endpoints.
    "market": None,  # filled in below -- MARKET is defined later in the file
    "analysis": None,
}

PLAYER: dict[str, Any] = {
    "id": 1,
    "name": "Player One",
    "country": "ESP",
    "ranking": 3,
    "ranking_points": 7000,
    "ranking_movement": "up",
    "hand": "R",
    "birthday": "2003-05-05",
    "tour": "ATP",
}

FIXTURE: dict[str, Any] = {
    "event_date": "2026-07-23T12:00:00Z",
    "tournament": "Test Open",
    "round": "SF",
    "player1_name": "Player One",
    "player2_name": "Player Two",
}

MARKET: dict[str, Any] = {
    "question": "Who wins?",
    "status": "open",
    "volume": 1000,
    "liquidity": 500,
    "prices": [{"side": 1, "mid": 0.6, "bid": 0.59, "ask": 0.61, "timestamp": "2026-07-22T00:00:00Z"}],
}

ANALYSIS: dict[str, Any] = {
    "profile": {
        "win_probability_p1": 0.61,
        "expected_closeness": 0.4,
        "volatility_rating": "medium",
        "key_factors": ["serve", "hard-court record"],
    },
    "thesis": {
        "pick_side": 1,
        "confidence": 0.7,
        "state": "active",
        "reasoning": "Better on hard courts.",
    },
}

EVENT: dict[str, Any] = {"timestamp": "2026-07-22T00:00:00Z", "type": "break", "player": 1}

H2H: dict[str, Any] = {
    "players": {"p1": {"name": "Player One"}, "p2": {"name": "Player Two"}},
    "totals": {"p1_wins": 3, "p2_wins": 1, "meetings": 5, "undecided": 1},
    "by_surface": {"hard": {"p1": 2, "p2": 1}, "clay": {"p1": 1, "p2": 0}},
    "meetings": [
        {
            "era": "current",
            "date": "2026-07-01",
            "tournament": "Test Open",
            "round": "F",
            "surface": "hard",
            "score": "6-4 6-4",
            "outcome": "completed",
            "winner": 1,
        },
        {
            "era": "archive",
            "date": "2021-06-01",
            "tournament": "Old Open",
            "round": "SF",
            "surface": "clay",
            "score": "W/O",
            "outcome": "walkover",
            "winner": None,
        },
    ],
}

ARCHIVE_MATCH: dict[str, Any] = {
    "id": 555,
    "source_id": "atp-1980-001",
    "tour": "atp",
    "level": "G",
    "tournament": "Old Open",
    "surface": "grass",
    "event_date": "1980-06-23",
    "round": "F",
    "best_of": 5,
    "winner": {"name": "Old Winner", "country": "SWE", "rank": 1, "seed": 1, "player_id": 9001},
    "loser": {"name": "Old Loser", "country": "USA", "rank": 2, "seed": 2, "player_id": 9002},
    "score": "6-4 7-6(5) 6-3",
    "outcome": "completed",
}

ARCHIVE_PLAYER: dict[str, Any] = {
    "id": 9001,
    "tour": "atp",
    "name": "Old Winner",
    "hand": "R",
    "dob": "1956-06-06",
    "country": "SWE",
    "height_cm": 180,
    "career_high_rank": 1,
    "career_high_date": "1980-08-01",
}

ARCHIVE_CAREER: dict[str, Any] = {
    "player": {"name": "Old Winner"},
    "span": {"first": "1973-01-01", "last": "1983-07-01"},
    "record": {
        "wins": 600,
        "losses": 120,
        "titles": 60,
        "by_surface": {"clay": {"wins": 300, "losses": 40}},
        "by_level": {"G": {"wins": 100, "losses": 15}},
    },
    "by_year": [{"year": 1980, "wins": 70, "losses": 6}],
    "serve": {"matches_with_stats": 0},
}

RANKING: dict[str, Any] = {
    "player_id": 1,
    "player_name": "Player One",
    "system": "atp",
    "tour": "atp",
    "rank": 1,
    "points": 9000,
    "previous_rank": 2,
    "rank_movement": None,
    "rating": None,
    "effective_date": "2026-07-20",
    "observed_at": "2026-07-20T00:00:00Z",
}

STATISTICS: dict[str, Any] = {
    "match_id": 101,
    "coverage": "live",
    "as_of": "2026-07-22T00:10:00Z",
    "age_seconds": 3,
    "games_counted": 15,
    "tiebreak_games_excluded": 0,
    "inconsistent_games_excluded": 0,
    "sets_covered": [1, 2],
    "freshness": {
        "derived": {"coverage": "live", "age_seconds": 3},
        "measured": {"coverage": "live", "age_seconds": 20},
        "measured_divergence": None,
    },
    "players": {
        "p1": {
            "service_games_played": 8,
            "service_games_won": 7,
            "hold_pct": 88,
            "return_games_played": 7,
            "return_games_won": 2,
            "break_pct": 29,
            "break_points_faced": 3,
            "break_points_saved": 2,
            "measured": {"aces": 9, "double_faults": 1},
        },
        "p2": {
            "service_games_played": 7,
            "service_games_won": 5,
            "hold_pct": 71,
            "return_games_played": 8,
            "return_games_won": 1,
            "break_pct": 13,
            "break_points_faced": 5,
            "break_points_saved": 3,
            "measured": {"aces": 4, "double_faults": 3},
        },
    },
}

MATCH["market"] = MARKET
MATCH["analysis"] = ANALYSIS


def page(row: dict[str, Any]) -> dict[str, Any]:
    return {"data": [row], "meta": {"limit": 1, "offset": 0, "count": 1}}


class StubAPI:
    """A running stub. ``rules`` forces a response for any path containing a key.

    A rule value is either a bare status (the body becomes the canonical error
    for that status) or a ``(status, body)`` pair for the responses whose BODY
    is the thing under test -- the daily-cap 429, the abuse throttle, the
    ambiguous-name 400::

        stub.rules = {"/history": 403, "/h2h": (400, {"error": "ambiguous_name", ...})}
    """

    def __init__(self) -> None:
        self.rules: dict[str, int | tuple[int, dict[str, Any]]] = {}
        self.asked: list[str] = []
        #: One entry per request: the path plus the two auth-relevant headers,
        #: so a test can assert what actually went over the wire.
        self.seen_headers: list[dict[str, str | None]] = []
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        assert self._server is not None, "stub is not started"
        return f"http://127.0.0.1:{self._server.server_address[1]}"

    def _forced_status(self, path: str) -> int | tuple[int, dict[str, Any]] | None:
        for marker, status in self.rules.items():
            if marker in path:
                return status
        return None

    def _body_for(self, path: str) -> dict[str, Any]:
        if "/health" in path:
            return {"status": "ok", "version": "v1"}
        if "/statistics" in path:
            return STATISTICS
        if "/h2h" in path:
            return H2H
        if "/history/archive/career" in path:
            return ARCHIVE_CAREER
        if "/history/archive/players" in path:
            return page(ARCHIVE_PLAYER)
        if "/history/archive/matches" in path:
            single = bool(re.search(r"/\d+$", path))
            return ARCHIVE_MATCH if single else page(ARCHIVE_MATCH)
        if "/rankings" in path:
            return page(RANKING)
        if "/events" in path:
            return page(EVENT)
        if "/analysis" in path:
            return ANALYSIS
        if "/markets" in path or "/prices" in path:
            return MARKET
        if "/score" in path:
            return dict(MATCH["score"])
        if "/fixtures" in path:
            return page(FIXTURE)
        # A trailing numeric segment means one item; otherwise a collection.
        single = bool(re.search(r"/\d+$", path))
        if "/players" in path:
            return PLAYER if single else page(PLAYER)
        if "/matches" in path:
            return MATCH if single else page(MATCH)
        return page(MATCH)

    def start(self) -> StubAPI:
        stub = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def do_GET(self) -> None:  # noqa: N802 - stdlib naming
                stub.asked.append(self.path)
                stub.seen_headers.append(
                    {
                        "path": self.path,
                        "x-api-key": self.headers.get("x-api-key"),
                        "authorization": self.headers.get("authorization"),
                    }
                )
                path = self.path.split("?")[0]

                forced = stub._forced_status(path)
                if forced is not None:
                    if isinstance(forced, tuple):
                        status, body = forced
                        self._send(status, body)
                        return
                    codes = {
                        401: "unauthorized",
                        403: "upgrade_required",
                        404: "not_found",
                        429: "rate_limited",
                        500: "server_error",
                    }
                    self._send(forced, {"error": codes.get(forced, "error")})
                    return

                self._send(200, stub._body_for(path))

            def _send(self, status: int, body: dict[str, Any]) -> None:
                payload = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args: Any) -> None:
                """Silence the default stderr access log."""

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def __enter__(self) -> StubAPI:
        return self.start()

    def __exit__(self, *exc: Any) -> None:
        self.stop()
