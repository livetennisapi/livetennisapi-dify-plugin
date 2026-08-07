from __future__ import annotations

from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from livetennisapi import LiveTennisAPI

from livetennisapi_client import (
    ARCHIVE_TOURS,
    archive_player_out,
    choice_param,
    emit,
    int_param,
    ok,
    run_tool,
)


class GetArchivePlayersTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        name = str(tool_parameters.get("name") or "").strip() or None
        tour = choice_param(tool_parameters.get("tour"), ARCHIVE_TOURS, None)
        limit = int_param(tool_parameters.get("limit"), 10)

        def body(client: LiveTennisAPI) -> dict[str, Any]:
            page = client.list_archive_players(name, tour=tour, limit=limit)
            scope = (f' matching "{name}"' if name else "") + (f" on the {tour.upper()} tour" if tour else "")
            if not page.data:
                return ok(
                    f"No archive players{scope}. The archive's people are the 1968-2022 era; "
                    "current players are served by search_players.",
                    players=[],
                )

            rows = [archive_player_out(bio) for bio in page.data]
            lines = [f"{len(rows)} archive player(s){scope}:"]
            for row in rows:
                line = f"  [{row['id']}] {row['name'] or '?'}"
                if row["country"]:
                    line += f" ({row['country']})"
                if row["tour"]:
                    line += f" - {row['tour'].upper()}"
                if row["career_high_rank"] is not None:
                    line += f" - career-high {row['career_high_rank']}"
                    if row["career_high_date"]:
                        line += f" ({row['career_high_date']})"
                lines.append(line)
            return ok("\n".join(lines), players=rows)

        yield from emit(self, run_tool(self.runtime.credentials, body))
