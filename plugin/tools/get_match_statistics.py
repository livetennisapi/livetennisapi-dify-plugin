from __future__ import annotations

from collections.abc import Generator, Mapping
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from livetennisapi import LiveTennisAPI

from livetennisapi_client import emit, missing_id, ok, required_id, run_tool

#: Measured fields worth a prose line, in display order. Absent means absent --
#: the API omits a measured field it does not hold, never zero-fills it.
MEASURED_LINES = (
    ("aces", "Aces"),
    ("double_faults", "Double faults"),
    ("winners", "Winners"),
    ("unforced_errors", "Unforced errors"),
)


def _side_lines(label: str, side: Mapping[str, Any]) -> list[str]:
    """Prose for one player's statistics block."""
    lines = [f"{label}:"]
    hold = side.get("hold_pct")
    if hold is not None:
        lines.append(
            f"  Holds: {side.get('service_games_won', 0)}/{side.get('service_games_played', 0)} ({hold}%)"
        )
    brk = side.get("break_pct")
    if brk is not None:
        lines.append(
            f"  Breaks: {side.get('return_games_won', 0)}/{side.get('return_games_played', 0)} ({brk}%)"
        )
    faced = side.get("break_points_faced")
    if faced:
        lines.append(f"  Break points saved: {side.get('break_points_saved', 0)}/{faced}")
    measured = side.get("measured")
    if isinstance(measured, Mapping):
        for key, label_text in MEASURED_LINES:
            if measured.get(key) is not None:
                lines.append(f"  {label_text}: {measured[key]}")
    return lines


class GetMatchStatisticsTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        match_id = required_id(tool_parameters.get("match_id"))
        if match_id is None:
            yield from emit(self, missing_id("match_id"))
            return

        def body(client: LiveTennisAPI) -> dict[str, Any]:
            stats = client.get_match_statistics(match_id)
            if stats is None:
                return ok("No statistics returned for that match id.")

            players = stats.players
            if not players:
                # The API's honest empty: the match exists, nothing is held for
                # it -- 200 with null players, not a 404.
                detail = f" {stats.detail}" if stats.detail else ""
                return ok(
                    f"The match exists but no statistics are held for it.{detail}",
                    match_id=stats.match_id,
                    coverage=stats.coverage,
                    players=None,
                )

            lines: list[str] = []
            if stats.coverage:
                lines.append(f"Statistics coverage: {stats.coverage}")
            for key, label in (("p1", "Player 1"), ("p2", "Player 2")):
                side = players.get(key)
                if isinstance(side, Mapping):
                    lines.extend(_side_lines(label, side))
            return ok(
                "\n".join(lines) or "Statistics returned, but empty.",
                match_id=stats.match_id,
                coverage=stats.coverage,
                games_counted=stats.games_counted,
                freshness=dict(stats.freshness or {}),
                players=dict(players),
            )

        yield from emit(self, run_tool(self.runtime.credentials, body))
