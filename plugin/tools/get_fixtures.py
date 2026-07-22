from __future__ import annotations

from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from livetennisapi import LiveTennisAPI

from livetennisapi_client import dash, emit, fixture_out, int_param, ok, run_tool


class GetFixturesTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        limit = int_param(tool_parameters.get("limit"), 20)

        def body(client: LiveTennisAPI) -> dict[str, Any]:
            page = client.list_fixtures(limit=limit)
            if not page.data:
                return ok("No upcoming fixtures.", fixtures=[])

            fixtures = [fixture_out(fixture) for fixture in page.data]
            lines = [
                f"{dash(fixture['event_date'])} - {dash(fixture['tournament'])}"
                + (f" ({fixture['round']})" if fixture["round"] else "")
                + f": {dash(fixture['player1'])} vs {dash(fixture['player2'])}"
                for fixture in fixtures
            ]
            return ok("\n".join(lines), fixtures=fixtures)

        yield from emit(self, run_tool(self.runtime.credentials, body))
