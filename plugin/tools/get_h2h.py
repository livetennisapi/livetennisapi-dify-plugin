from __future__ import annotations

from collections.abc import Generator, Mapping
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from livetennisapi import LiveTennisAPI

from livetennisapi_client import dash, emit, fail, ok, run_tool

#: How many meetings the prose lists. The JSON always carries all of them.
PROSE_MEETINGS = 10


def _resolved_name(players: Any, key: str, fallback: str) -> str:
    """The API's resolved name for one side, or the fragment the user gave."""
    if isinstance(players, Mapping):
        side = players.get(key)
        if isinstance(side, Mapping) and side.get("name"):
            return str(side["name"])
    return fallback


class GetH2HTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        p1 = str(tool_parameters.get("player1") or "").strip()
        p2 = str(tool_parameters.get("player2") or "").strip()
        # The API requires at least 3 characters per name; checking here saves
        # the request and gives a message that names the actual problem.
        if len(p1) < 3 or len(p2) < 3:
            yield from emit(
                self,
                fail(
                    "Both 'player1' and 'player2' are required - a full or partial player "
                    "name of at least 3 characters each, for example 'sinner' and 'alcaraz'.",
                    "invalid_parameter",
                ),
            )
            return

        def body(client: LiveTennisAPI) -> dict[str, Any]:
            h2h = client.get_h2h(p1, p2)
            players = getattr(h2h, "players", None) if h2h is not None else None
            if h2h is None or not players:
                return ok(
                    f'No head-to-head record found for "{p1}" vs "{p2}". Check the spelling, '
                    "or give fuller names.",
                    players=None,
                    totals=None,
                    meetings=[],
                )

            name1 = _resolved_name(players, "p1", p1)
            name2 = _resolved_name(players, "p2", p2)
            totals = dict(getattr(h2h, "totals", None) or {})
            meetings = [dict(m) for m in getattr(h2h, "meetings", None) or []]
            by_surface = dict(getattr(h2h, "by_surface", None) or {})

            lines = [
                f"{name1} vs {name2}: {totals.get('p1_wins', 0)}-{totals.get('p2_wins', 0)} "
                f"over {totals.get('meetings', len(meetings))} meeting(s)"
                + (f" ({totals['undecided']} with no derivable winner)" if totals.get("undecided") else "")
            ]
            for surface, split in by_surface.items():
                if isinstance(split, Mapping):
                    lines.append(f"  {surface}: {split.get('p1', 0)}-{split.get('p2', 0)}")
            if meetings:
                lines.append("")
                lines.append("Most recent meetings:")
                for meeting in meetings[:PROSE_MEETINGS]:
                    winner = meeting.get("winner")
                    won = name1 if winner == 1 else name2 if winner == 2 else "no decided winner"
                    lines.append(
                        f"  {dash(meeting.get('date'))} {dash(meeting.get('tournament'))} "
                        f"({dash(meeting.get('round'))}, {dash(meeting.get('surface'))}): "
                        f"{won}, {dash(meeting.get('score'))}"
                    )
                if len(meetings) > PROSE_MEETINGS:
                    lines.append(f"  ... and {len(meetings) - PROSE_MEETINGS} more in the JSON output.")

            return ok(
                "\n".join(lines),
                players={"p1": name1, "p2": name2},
                totals=totals,
                by_surface=by_surface,
                meetings=meetings,
            )

        yield from emit(self, run_tool(self.runtime.credentials, body))
