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


def page(row: dict[str, Any]) -> dict[str, Any]:
    return {"data": [row], "meta": {"limit": 1, "offset": 0, "count": 1}}


class StubAPI:
    """A running stub. ``rules`` forces a status for any path containing a key.

    Example -- make everything above the FREE tier answer as a tier wall::

        stub.rules = {"/history": 403, "/events": 403}
    """

    def __init__(self) -> None:
        self.rules: dict[str, int] = {}
        self.asked: list[str] = []
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        assert self._server is not None, "stub is not started"
        return f"http://127.0.0.1:{self._server.server_address[1]}"

    def _forced_status(self, path: str) -> int | None:
        for marker, status in self.rules.items():
            if marker in path:
                return status
        return None

    def _body_for(self, path: str) -> dict[str, Any]:
        if "/health" in path:
            return {"status": "ok", "version": "v1"}
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
                path = self.path.split("?")[0]

                forced = stub._forced_status(path)
                if forced is not None:
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
