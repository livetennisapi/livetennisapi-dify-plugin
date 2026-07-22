# Live Tennis API

Live tennis scores, schedules, results, players and rankings for Dify — covering
ATP, WTA, Challenger and ITF.

**Every tool is a read.** This plugin cannot create, modify or delete anything,
in the Live Tennis API or anywhere else.

- **Source repository:** https://github.com/livetennisapi/livetennisapi-dify-plugin
- **API documentation:** https://livetennisapi.com/docs
- **Get a free API key (no card):** https://livetennisapi.com/subscribe/free

## Setup

1. Get an API key at https://livetennisapi.com/subscribe/free. The free tier
   needs no payment card. Keys look like `twjp_...`.
2. In Dify, go to **Tools → Live Tennis API → Authorize**.
3. Paste the key into **Live Tennis API Key** and save.

Dify verifies the key immediately by making one live-matches request. If the key
is rejected you will see the error at this point rather than later, inside a
workflow.

### Connection requirements

The plugin makes outbound HTTPS requests to a single fixed host:

```
https://api.livetennisapi.com/api/public/v1
```

That address is a constant in the plugin; it is not configurable, and there is
no other network destination. A self-hosted Dify instance behind an egress
firewall needs `api.livetennisapi.com:443` allowed.

## Plans and the tier wall

Endpoints are grouped by plan:

| Plan | Adds |
| --- | --- |
| FREE | Live and upcoming matches, scores, players, fixtures |
| BASIC | + historical results |
| PRO | + match events and market prices |
| ULTRA | + model analysis, win probability and the live feed |

If you call a tool your plan does not include, **it does not raise an error.**
It returns a normal result that explains the situation in plain English and
names the plan required:

> This data requires the PRO plan, and the configured API key is on a lower
> tier. Nothing is wrong with the key — the endpoint is simply not included in
> the current plan. Upgrade at https://livetennisapi.com/#pricing

This is deliberate. Handed a bare `403`, an agent tends to invent a reason or
retry pointlessly; handed a sentence, it relays the upgrade path to the user and
moves on. The same applies to a rejected key, an unknown id and a rate limit.

Use **API status and plan** (`check_api_status`) to find out which plan a key is
on — it works even with no key configured, which is what makes it useful for
diagnosing why the other tools are returning no data.

## Tools

Every tool returns two things: prose for a model to read, and the same facts as
JSON (`ok`, `message`, `reason`, plus the data) for a workflow to consume without
re-parsing English. `ok` is always a boolean; `reason` explains a false one.

| Tool | Plan | Description |
| --- | --- | --- |
| `get_live_matches` | FREE | Matches in progress, with live scores |
| `get_upcoming_matches` | FREE | Matches scheduled to start soon |
| `get_match` | FREE | Full detail for one match by id |
| `get_match_score` | FREE | Current score only — the lowest-latency read |
| `search_players` | FREE | Search players by name |
| `get_player` | FREE | One player's profile and ranking |
| `get_fixtures` | FREE | The forward schedule |
| `get_recent_results` | BASIC | Recently completed matches and winners |
| `get_match_events` | PRO | Match timeline — breaks, games, sets |
| `get_match_odds` | PRO | Match-winner market prices (read-only reporting) |
| `get_match_analysis` | ULTRA | Model win probability, thesis and key factors |
| `check_api_status` | any | API reachability and the detected plan |

## Usage

**In an Agent.** Add the tools you want and ask naturally — "what tennis is on
right now", "how is Alcaraz doing", "who plays tomorrow". Match ids come from
`get_live_matches`, `get_upcoming_matches` or `get_recent_results`; player ids
come from `search_players`.

**In a Workflow.** Read the JSON output. Branch on `ok`, and on `reason` when it
is false:

```
ok = true                      -> use matches / player / score / ...
ok = false, reason = upgrade_required -> message names the required tier
ok = false, reason = no_api_key       -> the plugin has no key configured
ok = false, reason = rate_limited     -> back off; retry_after when the API sent one
```

Because no tool raises, a tier wall or a rate limit will not fail the node — the
branch stays in your control.

## Rate limits

Limits are per plan and enforced by the API. On a limit the tools return
`ok: false` with `reason: "rate_limited"` and, when the API supplies it, a
`retry_after` value in seconds.

## Support

Issues and questions: https://github.com/livetennisapi/livetennisapi-dify-plugin/issues

## Licence

MIT.
