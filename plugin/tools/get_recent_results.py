from __future__ import annotations

from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from livetennisapi import LiveTennisAPI

from livetennisapi_client import emit, int_param, match_out, ok, run_tool, summarise


class GetRecentResultsTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        limit = int_param(tool_parameters.get("limit"), 20)

        def body(client: LiveTennisAPI) -> dict[str, Any]:
            # /history/matches -- the first endpoint above the FREE floor, so a
            # FREE key reaches the guard's tier wall here rather than erroring.
            page = client.list_completed_matches(limit=limit)
            if not page.data:
                return ok("No completed matches available.", matches=[])
            return ok(
                "\n\n".join(summarise(match) for match in page.data),
                matches=[match_out(match) for match in page.data],
            )

        yield from emit(self, run_tool(self.runtime.credentials, body))
