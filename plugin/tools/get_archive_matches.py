from __future__ import annotations

from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from livetennisapi import LiveTennisAPI

from livetennisapi_client import (
    ARCHIVE_TOURS,
    archive_match_out,
    choice_param,
    dash,
    emit,
    int_param,
    ok,
    run_tool,
)


def _clean(value: Any) -> str | None:
    """A stripped string parameter, or ``None`` when empty."""
    text = str(value or "").strip()
    return text or None


class GetArchiveMatchesTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        name = _clean(tool_parameters.get("name"))
        tour = choice_param(tool_parameters.get("tour"), ARCHIVE_TOURS, None)
        from_ = _clean(tool_parameters.get("from"))
        to = _clean(tool_parameters.get("to"))
        round_ = _clean(tool_parameters.get("round"))
        limit = int_param(tool_parameters.get("limit"), 20)

        def body(client: LiveTennisAPI) -> dict[str, Any]:
            page = client.list_archive_matches(
                tour=tour,
                name=name,
                from_=from_,
                to=to,
                round=round_.upper() if round_ else None,
                limit=limit,
            )
            scope = " ".join(
                part
                for part in (
                    f"for {name}" if name else None,
                    f"on the {tour.upper()} tour" if tour else None,
                    f"from {from_}" if from_ else None,
                    f"to {to}" if to else None,
                    f"round {round_.upper()}" if round_ else None,
                )
                if part
            )
            if not page.data:
                return ok(
                    f"No archive results {scope}".strip() + ". The archive covers 1968-2022; "
                    "matches from 2023 onward are served by get_matches with status=completed.",
                    matches=[],
                )

            rows = [archive_match_out(row) for row in page.data]
            lines = [f"{len(rows)} archive result(s) {scope}".strip() + " (newest tournament first):"]
            for row in rows:
                winner = row["winner"] or {}
                loser = row["loser"] or {}
                lines.append(
                    f"  [{row['id']}] {dash(row['event_date'])} {dash(row['tournament'])} "
                    f"({dash(row['round'])}, {dash(row['surface'])}): "
                    f"{dash(winner.get('name'))} d. {dash(loser.get('name'))} {dash(row['score'])}"
                    + (f" [{row['outcome']}]" if row["outcome"] not in (None, "completed") else "")
                )
            return ok("\n".join(lines), matches=rows)

        yield from emit(self, run_tool(self.runtime.credentials, body))
