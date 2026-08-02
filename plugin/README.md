# Live Tennis API

Live tennis scores, schedules, players and fixtures for Dify — covering ATP,
WTA, Challenger and ITF.

**Every tool is a read.** This plugin cannot create, modify or delete anything,
in the Live Tennis API or anywhere else.

- **Source repository:** https://github.com/livetennisapi/livetennisapi-dify-plugin
- **API documentation:** https://livetennisapi.com/docs
- **Get a free API key (no card):** https://livetennisapi.com/subscribe/free
- **Contact:** support@livetennisapi.com

## Setup

1. Get an API key at https://livetennisapi.com/subscribe/free. The free tier
   needs no payment card and allows 1,000 requests per day. Keys look like
   `twjp_...`.
2. In Dify, go to **Tools → Live Tennis API → Authorize**.
3. Paste the key into **Live Tennis API Key** and save.

Dify verifies the key immediately by making one live-matches request. If the key
is rejected you will see it at this point rather than later, inside a workflow.

### Connection requirements

The plugin makes outbound HTTPS requests to a single fixed host:

```
https://api.livetennisapi.com/api/public/v1
```

That address is a constant in the plugin; it is not configurable, and there is
no other network destination. A self-hosted Dify instance behind an egress
firewall needs `api.livetennisapi.com:443` allowed.

The API key is sent in the **`x-api-key`** request header. A request without it
is answered `401 {"error": "unauthorized"}`.

## Tools

Six tools, one per documented public endpoint. All six work on the free plan.

| Tool | Endpoint | Description |
| --- | --- | --- |
| `get_matches` | `GET /matches` | Matches that are live now, upcoming, or completed — optionally one tour |
| `get_match` | `GET /matches/{id}` | Full detail for one match by id |
| `get_match_score` | `GET /matches/{id}/score` | Current score only — the lowest-latency read |
| `search_players` | `GET /players` | Search players by name |
| `get_player` | `GET /players/{id}` | One player's profile and ranking |
| `get_fixtures` | `GET /fixtures` | The forward schedule |

`get_matches` takes `status` (`live`, the default, `upcoming` or `completed`),
an optional `tour` (`atp`, `wta`, `challenger`, `itf`) and a `limit` (1–200,
default 20). It echoes back the `status` and `tour` it actually used, because an
unrecognised value falls back rather than being forwarded to the API.

Match ids come from `get_matches`; player ids come from `search_players`.

Every tool returns two things: prose for a model to read, and the same facts as
JSON (`ok`, `message`, `reason`, plus the data) for a workflow to consume without
re-parsing English. `ok` is always a boolean; `reason` explains a false one.

## Errors are results, not exceptions

**No tool raises.** A rejected key, an unknown id, a rate limit or an unusable
parameter all come back as a normal result:

```
ok = true                              -> use matches / player / score / ...
ok = false, reason = no_api_key        -> the plugin has no key configured
ok = false, reason = unauthorized      -> the key was rejected
ok = false, reason = not_found         -> no data for that id
ok = false, reason = rate_limited      -> back off; retry_after when the API sent one
ok = false, reason = invalid_parameter -> the message says what was wrong
ok = false, reason = upgrade_required  -> the message names the plan required
ok = false, reason = connection_error  -> the API could not be reached
ok = false, reason = request_failed    -> anything else the API returned
```

This is deliberate. Handed a bare HTTP status, an agent tends to invent a reason
or retry pointlessly; handed a sentence, it relays the situation to the user and
moves on. And because nothing raises, none of these states fails a workflow node
— the branch stays in your control via `ok` and `reason`.

## Plans

Every endpoint these six tools call is included in the free plan. Higher plans
raise the daily request allowance and additionally embed a match-winner `market`
block and a model `analysis` block inside `get_match`'s response. On a lower plan
those blocks are simply absent, which is not an error.

## Rate limits

Limits are per plan and enforced by the API — 1,000 requests per day on the free
tier. On a limit the tools return `ok: false` with `reason: "rate_limited"` and,
when the API supplies it, a `retry_after` value in seconds.

## Usage

**In an Agent.** Add the tools you want and ask naturally — "what tennis is on
right now", "who plays tomorrow on the WTA tour", "how did Alcaraz do".

**In a Workflow.** Read the JSON output and branch on `ok`, then on `reason`.

## Changes in 0.0.2

This release narrows the plugin to the Live Tennis API's six documented public
endpoints. **It is a breaking change for existing workflows.**

- `get_live_matches`, `get_upcoming_matches` and `get_recent_results` are
  replaced by the single **`get_matches`**, which takes `status`. Update any
  node that used them to `get_matches` with the matching `status`.
- `get_match_events`, `get_match_odds`, `get_match_analysis` and
  `check_api_status` are **removed**. Market and analysis data is still
  available, embedded in `get_match`.
- **New `tour` parameter** on `get_matches`, for narrowing to ATP, WTA,
  Challenger or ITF.
- **Fixed:** the API key is now sent in the `x-api-key` header, which is what the
  API documents, instead of `Authorization: Bearer`.
- **Fixed:** `get_match`'s declared output schema described the market price list
  incorrectly, so a workflow reading that schema saw the wrong shape.

## Support

Issues and questions: https://github.com/livetennisapi/livetennisapi-dify-plugin/issues

## Licence

MIT.
