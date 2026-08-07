from __future__ import annotations

from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from livetennisapi import LiveTennisAPI

from livetennisapi_client import (
    RANKING_SYSTEMS,
    choice_param,
    emit,
    int_param,
    ok,
    ranking_out,
    run_tool,
)

#: Human names for the systems, for prose only.
SYSTEM_LABELS = {
    "atp": "ATP singles",
    "wta": "WTA singles",
    "itf_jt": "ITF juniors",
    "itf_mt": "ITF men's World Tennis Tour",
    "itf_wt": "ITF women's World Tennis Tour",
}


class GetRankingsTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        # An unrecognised system falls back to the ATP table rather than being
        # forwarded -- the API would 400 on it, and "who is number 1" almost
        # always means the ATP or WTA table, which the model names correctly.
        system = choice_param(tool_parameters.get("system"), RANKING_SYSTEMS, "atp") or "atp"
        as_of = str(tool_parameters.get("as_of") or "").strip() or None
        limit = int_param(tool_parameters.get("limit"), 20)

        def body(client: LiveTennisAPI) -> dict[str, Any]:
            page = client.list_rankings(system=system, as_of=as_of, limit=limit)
            label = SYSTEM_LABELS.get(system, system)
            when = f" as of {as_of}" if as_of else ""
            if not page.data:
                return ok(
                    f"No {label} ranking table available{when}. ITF history begins 2026-07-29 "
                    "and cannot be reconstructed earlier.",
                    rankings=[],
                    system=system,
                )

            rows = [ranking_out(record) for record in page.data]
            effective = rows[0]["effective_date"]
            lines = [
                f"{label} rankings{when}"
                + (f" (week of {effective})" if effective else "")
                + ":"
            ]
            for row in rows:
                line = f"  {row['rank']}. {row['player_name'] or '?'}"
                if row["points"] is not None:
                    line += f" - {row['points']} pts"
                if row["previous_rank"] is not None and row["previous_rank"] != row["rank"]:
                    line += f" (prev {row['previous_rank']})"
                lines.append(line)
            return ok("\n".join(lines), rankings=rows, system=system)

        yield from emit(self, run_tool(self.runtime.credentials, body))
