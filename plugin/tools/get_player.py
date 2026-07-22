from __future__ import annotations

from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from livetennisapi import LiveTennisAPI

from livetennisapi_client import emit, missing_id, ok, player_out, required_id, run_tool


class GetPlayerTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        player_id = required_id(tool_parameters.get("player_id"))
        if player_id is None:
            yield from emit(self, missing_id("player_id"))
            return

        def body(client: LiveTennisAPI) -> dict[str, Any]:
            player = client.get_player(player_id)
            if player is None:
                return ok("No data returned for that player id.")

            out = player_out(player)
            lines = [f"{out['name'] or 'Unknown'} [{out['id']}]"]
            if out["country"]:
                lines.append(f"Country: {out['country']}")
            if out["ranking"] is not None:
                points = f" ({out['ranking_points']} pts)" if out["ranking_points"] else ""
                lines.append(f"Ranking: {out['ranking']}{points}")
            if out["ranking_movement"]:
                lines.append(f"Movement: {out['ranking_movement']}")
            if out["hand"]:
                lines.append(f"Plays: {'right-handed' if out['hand'] == 'R' else 'left-handed'}")
            if out["birthday"]:
                lines.append(f"Born: {out['birthday']}")
            if out["tour"]:
                lines.append(f"Tour: {out['tour']}")

            return ok("\n".join(lines), player=out)

        yield from emit(self, run_tool(self.runtime.credentials, body))
