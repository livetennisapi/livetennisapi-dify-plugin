from __future__ import annotations

from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from livetennisapi import LiveTennisAPI

from livetennisapi_client import emit, missing_id, ok, required_id, run_tool


class GetMatchAnalysisTool(Tool):
    """ULTRA. A key below that tier reaches the guard's tier wall, not an error.

    ``Analysis.profile`` and ``Analysis.thesis`` are plain dicts on the SDK
    model, not nested objects -- attribute access on them silently yields
    nothing.
    """

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        match_id = required_id(tool_parameters.get("match_id"))
        if match_id is None:
            yield from emit(self, missing_id("match_id"))
            return

        def body(client: LiveTennisAPI) -> dict[str, Any]:
            analysis = client.get_match_analysis(match_id)
            profile = getattr(analysis, "profile", None) if analysis else None
            thesis = getattr(analysis, "thesis", None) if analysis else None
            if not isinstance(profile, dict) and not isinstance(thesis, dict):
                return ok("No model analysis exists for this match yet.")

            lines: list[str] = []
            data: dict[str, Any] = {}

            if isinstance(profile, dict):
                lines.append("Profile:")
                win_probability = profile.get("win_probability_p1")
                if win_probability is not None:
                    lines.append(f"  Win probability (player 1): {win_probability * 100:.1f}%")
                closeness = profile.get("expected_closeness")
                if closeness is not None:
                    lines.append(f"  Expected closeness: {closeness}")
                if profile.get("volatility_rating"):
                    lines.append(f"  Volatility: {profile['volatility_rating']}")
                key_factors = list(profile.get("key_factors") or [])
                if key_factors:
                    lines.append(f"  Key factors: {'; '.join(key_factors)}")
                data["profile"] = {
                    "win_probability_p1": win_probability,
                    "expected_closeness": closeness,
                    "volatility_rating": profile.get("volatility_rating"),
                    "key_factors": key_factors,
                }

            if isinstance(thesis, dict):
                lines.extend(("", "Thesis:"))
                if thesis.get("pick_side"):
                    lines.append(f"  Pick: player {thesis['pick_side']}")
                confidence = thesis.get("confidence")
                if confidence is not None:
                    lines.append(f"  Confidence: {confidence * 100:.0f}%")
                if thesis.get("state"):
                    lines.append(f"  State: {thesis['state']}")
                if thesis.get("reasoning"):
                    lines.append(f"  Reasoning: {thesis['reasoning']}")
                data["thesis"] = {
                    "pick_side": thesis.get("pick_side"),
                    "confidence": confidence,
                    "state": thesis.get("state"),
                    "reasoning": thesis.get("reasoning"),
                }

            return ok("\n".join(lines), **data)

        yield from emit(self, run_tool(self.runtime.credentials, body))
