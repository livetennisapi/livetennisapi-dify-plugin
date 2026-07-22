from __future__ import annotations

from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from livetennisapi import LiveTennisAPI

from livetennisapi_client import emit, format_score, missing_id, ok, required_id, run_tool


class GetMatchScoreTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        match_id = required_id(tool_parameters.get("match_id"))
        if match_id is None:
            yield from emit(self, missing_id("match_id"))
            return

        def body(client: LiveTennisAPI) -> dict[str, Any]:
            score = client.get_match_score(match_id)
            if score is None:
                return ok("No score available for that match yet.")

            formatted = format_score(score)
            lines = [f"Score: {formatted}"]
            if score.sets:
                lines.append(f"Sets: {'-'.join(str(value) for value in score.sets)}")
            if score.server:
                lines.append(f"Serving: player {score.server}")
            if score.is_tiebreak:
                lines.append("In a tiebreak")
            if score.win_probability_p1 is not None:
                lines.append(
                    f"Model win probability (player 1): {score.win_probability_p1 * 100:.1f}%"
                )

            return ok(
                "\n".join(lines),
                score={
                    "formatted": formatted,
                    "sets": list(score.sets) if score.sets else None,
                    "serving": score.server,
                    "is_tiebreak": score.is_tiebreak,
                    "win_probability_p1": score.win_probability_p1,
                },
            )

        yield from emit(self, run_tool(self.runtime.credentials, body))
