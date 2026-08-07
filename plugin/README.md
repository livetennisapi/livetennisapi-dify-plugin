# Live Tennis API

Live tennis scores, schedules, players, fixtures, rankings, head-to-head and a
1968–2022 results archive for Dify — covering ATP, WTA, Challenger, ITF and
juniors.

**Every tool is a read.** This plugin cannot create, modify or delete anything,
in the Live Tennis API or anywhere else.

- **Source repository:** https://github.com/livetennisapi/livetennisapi-dify-plugin
- **API documentation:** https://docs.livetennisapi.com
- **Get a free API key (no card):** https://livetennisapi.com/subscribe/free
- **Community:** https://discord.gg/f8WUZHgDm6
- **Contact:** hello@livetennisapi.com

## Setup

1. Get an API key at https://livetennisapi.com/subscribe/free. The free tier
   needs no payment card and allows 100 requests per day. Keys look like
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

Twelve tools over the Live Tennis API's documented public endpoints. The
**Plan** column is the lowest plan that includes the call — on a lower plan the
tool returns `ok: false` with `reason: "upgrade_required"` and a message naming
the plan, never an exception.

| Tool | Endpoint | Plan | Description |
| --- | --- | --- | --- |
| `get_matches` | `GET /matches` | FREE¹ | Matches live now, upcoming, or completed — optionally one tour |
| `get_match` | `GET /matches/{id}` | FREE² | Full detail for one match by id |
| `get_match_score` | `GET /matches/{id}/score` | FREE | Current score only — the lowest-latency read |
| `search_players` | `GET /players` | FREE | Search players by name |
| `get_player` | `GET /players/{id}` | FREE | One player's profile and ranking |
| `get_fixtures` | `GET /fixtures` | FREE | The forward schedule |
| `get_h2h` | `GET /h2h` | BASIC | Head-to-head between two players — archive plus current matches in one answer |
| `get_archive_matches` | `GET /history/archive/matches` | BASIC | Search the 1968–2022 results archive |
| `get_archive_players` | `GET /history/archive/players` | BASIC | Archive player bios and career-high ranks |
| `get_archive_career` | `GET /history/archive/career` | BASIC | One player's career aggregates over the archive |
| `get_rankings` | `GET /rankings` | PRO | The published ranking table for one system, optionally as of a past date |
| `get_match_statistics` | `GET /matches/{id}/statistics` | ULTRA | In-play statistics — aces, serve split, hold/break percentages |

¹ `status=completed` needs BASIC or higher; live and upcoming are FREE.
² The embedded `market` block appears at PRO, the `analysis` block at ULTRA; on
lower plans those blocks are simply absent, which is not an error.

`get_matches` takes `status` (`live`, the default, `upcoming` or `completed`),
an optional `tour` (`atp`, `wta`, `challenger`, `itf`, `juniors`) and a `limit`
(1–200, default 20). It echoes back the `status` and `tour` it actually used,
because an unrecognised value falls back rather than being forwarded to the API.

Match ids come from `get_matches`; player ids come from `search_players`. The
archive is its own id space — archive person ids come from
`get_archive_players` and join `get_archive_matches` rows, never `get_player`.

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
ok = false, reason = rate_limited      -> back off; retry_after when the API sent one,
                                          plus scope="day", limit_per_day and resets_at
                                          when the daily quota is what tripped
ok = false, reason = abuse_throttled   -> the key is blocked ~24h for repeatedly
                                          exceeding its quota; fix the retry loop,
                                          retry_at_epoch says when the block lifts
ok = false, reason = ambiguous_name    -> the name matched several players; candidates
                                          lists them
ok = false, reason = invalid_parameter -> the message says what was wrong
ok = false, reason = upgrade_required  -> the message names the plan required
ok = false, reason = connection_error  -> the API could not be reached
ok = false, reason = request_failed    -> anything else the API returned
```

This is deliberate. Handed a bare HTTP status, an agent tends to invent a reason
or retry pointlessly; handed a sentence, it relays the situation to the user and
moves on. And because nothing raises, none of these states fails a workflow node
— the branch stays in your control via `ok` and `reason`.

## Plans and rate limits

Limits are per plan and enforced by the API:

| Plan | Per minute | Per day | Price |
| --- | --- | --- | --- |
| FREE | 30 | 100 | $0 |
| BASIC | 60 | 1,000 | $9.99/mo |
| PRO | 300 | 10,000 | $29.99/mo |
| ULTRA | 600 | 500,000 | $99.99/mo |

On the free tier's 100 requests per day, poll no faster than every 15 minutes;
an always-on dashboard should run on BASIC or higher. When the daily quota is
exhausted the tools return the absolute instant it resets (`resets_at`) — the
reset is derived from a local midnight, so trust the timestamp rather than
assuming a time of day.

Higher plans also unlock more of the surface — the tier gates in the tools
table above. Upgrade at https://livetennisapi.com/subscribe/upgrade

## Usage

**In an Agent.** Add the tools you want and ask naturally — "what tennis is on
right now", "who plays tomorrow on the WTA tour", "what's the Sinner–Alcaraz
head-to-head", "who was world number 1 in July".

**In a Workflow.** Read the JSON output and branch on `ok`, then on `reason`.

## Changes in 0.0.6

- **Six new tools:** `get_h2h`, `get_archive_matches`, `get_archive_players`,
  `get_archive_career` (BASIC), `get_rankings` (PRO) and
  `get_match_statistics` (ULTRA). The six existing tools are unchanged —
  workflows built on 0.0.5 work unmodified.
- **New `juniors` value** for `get_matches`' `tour` parameter — the API covers
  ATP, WTA, Challenger, ITF and juniors.
- **Richer rate-limit results:** the daily cap now reports `scope`,
  `limit_per_day` and the absolute `resets_at` instant; the API's 24-hour abuse
  throttle is its own `reason: "abuse_throttled"` with `retry_at_epoch`.
- **`reason: "ambiguous_name"`** with the candidate list, when a player-name
  fragment matches more than one person.
- Reconciles the 0.0.4/0.0.5 Marketplace releases (packaging fixes made
  upstream by the Dify maintainers — no tool or behaviour changes).

## Changes in 0.0.3

- **Fixed:** the API documentation link now points to
  https://docs.livetennisapi.com. The address printed in earlier versions (a
  `/docs` path on the main domain) redirects to the homepage rather than the
  documentation.
- The source repository now carries the MIT licence text as a `LICENSE` file;
  previously the licence was stated but the file was missing.

## Changes in 0.0.2

This release narrows the plugin to the Live Tennis API's documented public
endpoints. **It is a breaking change for workflows built on 0.0.1.**

- `get_live_matches`, `get_upcoming_matches` and `get_recent_results` are
  replaced by the single **`get_matches`**, which takes `status`. Update any
  node that used them to `get_matches` with the matching `status`.
- `get_match_events`, `get_match_odds`, `get_match_analysis` and
  `check_api_status` are **removed**. Market and analysis data is still
  available, embedded in `get_match`.
- **New `tour` parameter** on `get_matches`.
- **Fixed:** the API key is now sent in the `x-api-key` header, which is what the
  API documents, instead of `Authorization: Bearer`.
- **Fixed:** `get_match`'s declared output schema described the market price list
  incorrectly, so a workflow reading that schema saw the wrong shape.

## Support

Issues and questions: https://github.com/livetennisapi/livetennisapi-dify-plugin/issues

## Licence

MIT.
