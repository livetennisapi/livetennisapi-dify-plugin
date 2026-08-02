from __future__ import annotations

from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from livetennisapi import LiveTennisAPI

from livetennisapi_client import (
    MATCH_STATUSES,
    TOURS,
    choice_param,
    emit,
    int_param,
    list_matches,
    match_out,
    ok,
    run_tool,
    summarise,
)

#: What an empty page means, per status. A bare "no matches" reads as a fault.
EMPTY = {
    "live": "No matches are live right now",
    "upcoming": "No upcoming matches are scheduled",
    "completed": "No completed matches available",
}


class GetMatchesTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        # An unrecognised status falls back to "live" rather than being forwarded:
        # the API would reject it, and "what tennis is on" is the common intent.
        status = choice_param(tool_parameters.get("status"), MATCH_STATUSES, "live") or "live"
        tour = choice_param(tool_parameters.get("tour"), TOURS, None)
        limit = int_param(tool_parameters.get("limit"), 20)

        def body(client: LiveTennisAPI) -> dict[str, Any]:
            page = list_matches(client, status=status, tour=tour, limit=limit)
            scope = f" on the {tour.upper()} tour" if tour else ""
            if not page.data:
                return ok(f"{EMPTY[status]}{scope}.", matches=[], status=status, tour=tour)
            return ok(
                f"{len(page.data)} {status} match(es){scope}:\n\n"
                + "\n\n".join(summarise(match) for match in page.data),
                matches=[match_out(match) for match in page.data],
                status=status,
                tour=tour,
            )

        yield from emit(self, run_tool(self.runtime.credentials, body))
