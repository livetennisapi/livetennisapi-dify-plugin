from __future__ import annotations

from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from livetennisapi import LiveTennisAPI

from livetennisapi_client import (
    dash,
    emit,
    match_out,
    missing_id,
    ok,
    price_out,
    required_id,
    run_tool,
    summarise,
)


class GetMatchTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        match_id = required_id(tool_parameters.get("match_id"))
        if match_id is None:
            yield from emit(self, missing_id("match_id"))
            return

        def body(client: LiveTennisAPI) -> dict[str, Any]:
            match = client.get_match(match_id)
            if match is None:
                return ok("No data returned for that match id.")

            text = summarise(match)
            data: dict[str, Any] = {"match": match_out(match)}

            # Both blocks are tier-gated at the API: the fields are simply
            # absent on a lower plan rather than the call failing, so their
            # absence is not worth a message.
            market = getattr(match, "market", None)
            if market is not None:
                prices = [price_out(price) for price in getattr(market, "prices", None) or []]
                text += f"\n\nMarket: {getattr(market, 'question', None) or '-'}"
                for price in prices:
                    text += (
                        f"\n  Side {dash(price['side'])}: mid {dash(price['mid'])} "
                        f"(bid {dash(price['bid'])} / ask {dash(price['ask'])})"
                    )
                data["market"] = {
                    "question": getattr(market, "question", None),
                    "prices": prices,
                }

            # Analysis.profile is a plain dict, not a model object -- attribute
            # access here silently yields None and drops the whole ULTRA block.
            profile = getattr(getattr(match, "analysis", None), "profile", None)
            if isinstance(profile, dict):
                text += "\n\nModel analysis:"
                win_probability = profile.get("win_probability_p1")
                if win_probability is not None:
                    text += f"\n  Win probability (player 1): {win_probability * 100:.1f}%"
                key_factors = list(profile.get("key_factors") or [])
                if key_factors:
                    text += f"\n  Key factors: {'; '.join(key_factors)}"
                data["analysis"] = {
                    "win_probability_p1": win_probability,
                    "key_factors": key_factors,
                }

            return ok(text, **data)

        yield from emit(self, run_tool(self.runtime.credentials, body))
