from __future__ import annotations

from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from livetennisapi import LiveTennisAPI

from livetennisapi_client import (
    dash,
    emit,
    int_param,
    missing_id,
    ok,
    price_out,
    required_id,
    run_tool,
)


class GetMatchOddsTool(Tool):
    """PRO. Read-only reporting of match-winner market prices.

    This reports prices; it cannot place, modify or settle anything. There is
    no write path to any venue anywhere in this plugin.
    """

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        match_id = required_id(tool_parameters.get("match_id"))
        if match_id is None:
            yield from emit(self, missing_id("match_id"))
            return

        limit = int_param(tool_parameters.get("limit"), 10)

        def body(client: LiveTennisAPI) -> dict[str, Any]:
            market = client.get_market_prices(match_id, limit=limit)
            if market is None:
                return ok("No market data for that match.")

            prices = [price_out(price) for price in market.prices or []]
            lines = [f"Market: {market.question or '-'}"]
            if market.status:
                lines.append(f"Status: {market.status}")
            if market.volume is not None:
                lines.append(f"24h volume: {market.volume}")
            if market.liquidity is not None:
                lines.append(f"Liquidity: {market.liquidity}")
            lines.extend(("", "Recent prices (newest first):"))
            for price in prices:
                lines.append(
                    f"  side {dash(price['side'])}: mid {dash(price['mid'])} - "
                    f"bid {dash(price['bid'])} - ask {dash(price['ask'])}"
                    + (f" @ {price['timestamp']}" if price["timestamp"] else "")
                )

            return ok(
                "\n".join(lines),
                market={
                    "question": market.question,
                    "status": market.status,
                    "volume": market.volume,
                    "liquidity": market.liquidity,
                    "prices": prices,
                },
            )

        yield from emit(self, run_tool(self.runtime.credentials, body))
