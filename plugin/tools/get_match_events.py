from __future__ import annotations

from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from livetennisapi import LiveTennisAPI

from livetennisapi_client import dash, emit, int_param, missing_id, ok, required_id, run_tool


class GetMatchEventsTool(Tool):
    """PRO. A key below that tier reaches the guard's tier wall, not an error."""

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        match_id = required_id(tool_parameters.get("match_id"))
        if match_id is None:
            yield from emit(self, missing_id("match_id"))
            return

        limit = int_param(tool_parameters.get("limit"), 30)

        def body(client: LiveTennisAPI) -> dict[str, Any]:
            page = client.list_match_events(match_id, limit=limit)
            if not page.data:
                return ok("No events recorded for this match.", events=[])

            events = [
                {
                    "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                    "type": event.type,
                    "player": event.player,
                }
                for event in page.data
            ]
            lines = [
                f"{dash(event['timestamp'])} - {dash(event['type'])}"
                + (f" (player {event['player']})" if event["player"] else "")
                for event in events
            ]
            return ok("\n".join(lines), events=events)

        yield from emit(self, run_tool(self.runtime.credentials, body))
