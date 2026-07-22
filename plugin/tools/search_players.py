from __future__ import annotations

from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from livetennisapi import LiveTennisAPI

from livetennisapi_client import emit, fail, int_param, ok, player_out, run_tool


class SearchPlayersTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        query = str(tool_parameters.get("query") or "").strip()
        if not query:
            yield from emit(
                self,
                fail(
                    "The 'query' parameter is required - pass a full or partial player name, "
                    "for example 'alcaraz'.",
                    "invalid_parameter",
                ),
            )
            return

        limit = int_param(tool_parameters.get("limit"), 10)

        def body(client: LiveTennisAPI) -> dict[str, Any]:
            page = client.search_players(query, limit=limit)
            if not page.data:
                return ok(f'No players matched "{query}".', players=[])

            lines = []
            for player in page.data:
                line = f"[{player.id}] {player.name or '?'}"
                if player.country:
                    line += f" ({player.country})"
                if player.ranking is not None:
                    line += f" - rank {player.ranking}"
                if player.tour:
                    line += f" - {player.tour}"
                lines.append(line)

            return ok("\n".join(lines), players=[player_out(player) for player in page.data])

        yield from emit(self, run_tool(self.runtime.credentials, body))
