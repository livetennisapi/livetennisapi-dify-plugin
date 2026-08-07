from __future__ import annotations

from collections.abc import Generator, Mapping
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from livetennisapi import LiveTennisAPI

from livetennisapi_client import emit, fail, ok, run_tool


def _record_line(label: str, split: Any) -> str | None:
    """``label: 10-2`` from a ``{"wins": .., "losses": ..}`` mapping, or None."""
    if not isinstance(split, Mapping):
        return None
    return f"  {label}: {split.get('wins', 0)}-{split.get('losses', 0)}"


class GetArchiveCareerTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        name = str(tool_parameters.get("name") or "").strip()
        if len(name) < 3:
            yield from emit(
                self,
                fail(
                    "The 'name' parameter is required - a full or partial player name of at "
                    "least 3 characters that resolves to exactly one archive player. An "
                    "ambiguous fragment is answered with the candidate names to choose from.",
                    "invalid_parameter",
                ),
            )
            return

        def body(client: LiveTennisAPI) -> dict[str, Any]:
            career = client.get_archive_career(name)
            if career is None:
                return ok(f'No archive career found for "{name}".')

            player = dict(career.player or {})
            span = dict(career.span or {})
            record = dict(career.record or {})
            serve = dict(career.serve or {})

            lines = [
                f"{player.get('name') or name} - archive career "
                f"({span.get('first', '?')} to {span.get('last', '?')}):",
                f"  Record: {record.get('wins', 0)}-{record.get('losses', 0)}, "
                f"{record.get('titles', 0)} title(s)",
            ]
            for surface, split in (record.get("by_surface") or {}).items():
                line = _record_line(surface, split)
                if line:
                    lines.append(line)
            matches_with_stats = serve.get("matches_with_stats") or 0
            if matches_with_stats:
                lines.append(
                    f"  Serve (over {matches_with_stats} matches with stats, recorded from 1991): "
                    f"{serve.get('aces', 0)} aces, {serve.get('double_faults', 0)} double faults"
                    + (
                        f", {serve['first_in_pct']:.0%} first serves in"
                        if isinstance(serve.get("first_in_pct"), float)
                        else ""
                    )
                )
            else:
                lines.append(
                    "  No per-match serve statistics - the corpus records them from 1991 only."
                )

            return ok(
                "\n".join(lines),
                player=player,
                span=span,
                record=record,
                by_year=list(career.by_year or []),
                serve=serve,
            )

        yield from emit(self, run_tool(self.runtime.credentials, body))
