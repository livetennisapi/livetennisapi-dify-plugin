# Build plan — Live Tennis API Dify plugin

## Build target & source of truth

Build a Dify **tool plugin** wrapping the Live Tennis API, packaged as a `.difypkg` and ready
to submit to `langgenius/dify-plugins`. Greenfield; a fresh local git repo at
`/home/ben/Documents/ben-is-a-dev/livetennisapi-oss/dify-plugin/`.

Sources of truth, in priority order:

1. **Tool surface** — `../livetennisapi-mcp/src/server.ts` (12 `server.registerTool(...)` calls).
   Descriptions and parameter schemas are reused verbatim where the two platforms allow.
   That file is read-only for this task.
2. **Submission rules** — the target repo itself, cloned and read today (not the brief):
   - `docs/plugin-submission-requirements.md`
   - `docs/plugin-review-guidelines.md`
   - `.github/pull_request_template.md`
   - `.github/workflows/pre-check-plugin.yaml`, `.github/workflows/pr-risk-label.yaml`
3. **Plugin conventions** — a real merged package, unpacked:
   `scrapeunblocker/scrapeunblocker/scrapeunblocker-0.0.2.difypkg`.
4. **REST surface** — `../openapi/openapi.yaml` and the published `livetennisapi` PyPI SDK 1.0.2.

## Summary

Ready to build as specified. Nothing in the brief was contradicted by the repo, but four
things were **verified or corrected** against it:

- `[FACT]` The submission PR adds **exactly one file**: the `.difypkg`. Verified two ways —
  1059 of 1154 tracked files are `.difypkg`, and the last six merged PRs
  (#2740–#2745) each touched a single `.difypkg` and nothing else. The plugin *source*
  is not committed to `dify-plugins`. So the brief's "top-level `<author>/<plugin_name>/`"
  is right, but that directory holds only the package.
- `[FACT]` `pre-check-plugin.yaml` hard-fails if more than one `.difypkg` changes in a PR,
  requires the icon at `_assets/<manifest.icon>` inside the package, and rejects an author
  string containing `dify` or `langgenius`. `livetennisapi` passes all three.
- `[FACT]` The risk regex is `/^- \[[xX]\] Low risk\s*$/m` and it counts **all three**
  patterns — ticking two labels the PR `risk: missing` just as surely as ticking none.
- `[JUDGMENT]` **No user-configurable base URL.** The reference plugin exposes `base_url`
  as a credential; we deliberately do not. "Low risk" is defined as calling *fixed*,
  documented third-party HTTPS APIs, and a user-settable base URL makes the destination
  non-fixed — handing a reviewer a reason to re-label under the doc's own
  "when more than one level seems possible, choose the higher" rule. The base URL is a
  module constant. The stub test injects its URL through a test-only constructor argument,
  never through a credential.

Top risks, honestly stated:

1. **`get_match_odds` reads as "financial" to a skimming reviewer.** It reports market
   prices. Dify's High-risk bucket names "financial ... sensitive personal data" — personal
   data, which market prices are not — and its banned-content rule targets money *movement*.
   Mitigation: tick Low, and disclose the tool explicitly in the PR's "Security and privacy
   notes" so the reviewer re-labels rather than rejects. This is a call the reviewer may
   overturn; it is not a call we can make silently.
2. **Marketplace-side review is not CI.** Passing `pre-check-plugin.yaml` locally proves
   packaging, not acceptance.

Blocking open questions: none. The two `[ASSUMPTION]`s below are non-blocking.

## Build units (ordered)

### [BUILD-001] Repo skeleton and plugin metadata
- **Delivers** `plugin/manifest.yaml`, `plugin/main.py`, `plugin/requirements.txt`,
  `plugin/.difyignore`, `plugin/_assets/icon.png`, repo `.gitignore`.
- **Depends-on** nothing.
- **Files** as above.
- **Acceptance** `dify plugin package ./plugin` is not yet expected to pass (no tools), but
  `manifest.yaml` parses under `yq` and carries every field `pre-check-plugin.yaml` reads:
  `author`, `name`, `version`, `type`, `icon`, `privacy`, `meta.runner`.
- **Output strategy** one-shot — short declarative files.
- **Becomes commit** `BUILD-001 plugin skeleton and manifest`.

### [BUILD-002] Shared client and the tier-aware guard
- **Delivers** `plugin/livetennisapi_client.py` — credential → SDK client, score formatter,
  match/player/fixture/price serialisers, and `respond()`: the single place where an API
  exception becomes a **normal** result.
- **Depends-on** BUILD-001.
- **Files** `plugin/livetennisapi_client.py`.
- **Acceptance** `respond()` returns `ok=False` plus a plain-English message naming the
  required tier for `UpgradeRequired`, and never re-raises for `UpgradeRequired`,
  `Unauthorized`, `NotFound` or `RateLimited`. Asserted directly in BUILD-008.
- **Output strategy** staged — this is the load-bearing file; structure first
  (constants → formatters → serialisers → guard), then fill and re-read each section.
- **Becomes commit** `BUILD-002 shared client with tier-aware guard`.

### [BUILD-003] Tool provider and credentials
- **Delivers** `plugin/provider/livetennisapi.yaml` (one `api_key` secret-input credential),
  `plugin/provider/livetennisapi.py` (`_validate_credentials`).
- **Depends-on** BUILD-002.
- **Acceptance** provider yaml lists all 12 tool yamls; credential validation raises
  `ToolProviderCredentialValidationError` on a rejected key and returns cleanly on a good one.
- **Output strategy** one-shot.
- **Becomes commit** `BUILD-003 tool provider and api_key credential`.

### [BUILD-004] FREE/BASIC tools (8)
- **Delivers** `get_live_matches`, `get_upcoming_matches`, `get_match`, `get_match_score`,
  `search_players`, `get_player`, `get_fixtures`, `get_recent_results` — `.yaml` + `.py` each.
- **Depends-on** BUILD-003.
- **Acceptance** each yields a text message and a json message; `ok` is a boolean on every
  path; descriptions match `server.ts`.
- **Output strategy** staged — one tool at a time, re-read after each.
- **Becomes commit** `BUILD-004 free and basic tier tools`.

### [BUILD-005] PRO tools (2)
- **Delivers** `get_match_events`, `get_match_odds`.
- **Acceptance** as BUILD-004, plus: on a 403 the result is a normal message naming PRO.
- **Becomes commit** `BUILD-005 pro tier tools`.

### [BUILD-006] ULTRA tool (1)
- **Delivers** `get_match_analysis`.
- **Acceptance** as BUILD-005, naming ULTRA.
- **Becomes commit** `BUILD-006 ultra tier tool`.

### [BUILD-007] Meta tool
- **Delivers** `check_api_status` — reachability plus tier probe, mirroring `server.ts`
  including the FREE-detection catch that a naive port gets wrong.
- **Acceptance** reports `ok=true` even with no usable data; reports the detected tier.
- **Becomes commit** `BUILD-007 check_api_status meta tool`.

### [BUILD-008] Stub-server test harness
- **Delivers** `test/stub_api.py`, `test/test_tools.py` — a local `http.server` stub modelled
  on `../livetennisapi-mcp/test/tools-output.mjs`, driving all 12 tools with no credentials
  and no network.
- **Acceptance** every tool invoked; every tool asserted to yield a boolean `ok`; the
  **tier-wall path asserted to return an explanation, not raise**; a stub 401, 404 and 429
  likewise. Runs green.
- **Output strategy** staged.
- **Becomes commit** `BUILD-008 stub-server test suite`.

### [BUILD-009] README and PRIVACY
- **Delivers** `plugin/README.md`, `plugin/PRIVACY.md`.
- **Acceptance** README covers setup, usage, required credential, connection requirements and
  the source repo link (the four things `plugin-review-guidelines.md` checks); PRIVACY names
  what is sent where and is referenced by `manifest.yaml: privacy`.
- **Becomes commit** `BUILD-009 readme and privacy policy`.

### [BUILD-010] Package and PR body
- **Delivers** `dist/livetennisapi-0.0.1.difypkg`, `PR_BODY.md`, repo `README.md`.
- **Acceptance** `dify plugin package` succeeds; the unpacked package contains no `.git`,
  no `__pycache__`, no venv, no tests, no secrets; `PR_BODY.md` matches the upstream template
  and exactly one risk box is ticked, verified by running the CI regex against it.
- **Becomes commit** `BUILD-010 build package and PR body`.

## Conventions to follow

| Concern | Pattern | Cited from |
|---|---|---|
| Package layout | `manifest.yaml`, `main.py`, `provider/`, `tools/`, `_assets/`, `requirements.txt`, `.difyignore` | unpacked `scrapeunblocker-0.0.2.difypkg` |
| Entrypoint | `Plugin(DifyPluginEnv(MAX_REQUEST_TIMEOUT=...))`, `plugin.run()` | `su/main.py:1-12` |
| Tool class | `class X(Tool)`, `_invoke(self, tool_parameters) -> Generator[ToolInvokeMessage, None, None]` | `su/tools/search_google.py:11-13` |
| Failure shape | `yield self.create_json_message({...})` and return — **never raise** | `su/tools/search_google.py:16-18` |
| Credentials | `self.runtime.credentials`, `secret-input`, validated in the provider | `su/provider/scrapeunblocker.py:11-17` |
| Tool yaml | `identity` / `description.human` + `.llm` / `output_schema` / `parameters` / `extra.python.source` | `su/tools/search_google.yaml` |
| Score formatting | `games` is **player-major**; zip the two lists with `zip_longest` | `livetennisapi/cli.py:70-92`; the same bug is called out in `../SUBMISSIONS.md` |
| Tier semantics | `UpgradeRequired.required_tier`, tier wall is a normal result | `server.ts:210-220`; `livetennisapi/_base.py:25-30` |

Deliberate deviation from the reference package, stated rather than silent: **no `base_url`
credential** (see Summary).

## Open questions & assumptions

- `[ASSUMPTION]` (non-blocking) Depending on the published `livetennisapi` PyPI SDK is
  preferable to re-implementing HTTP. Grounds: it is the vendor SDK for the API being
  wrapped, it is pure Python, and its only requirement — `httpx` — is *already* a
  `dify_plugin` dependency, so the plugin's dependency footprint grows by one package with
  zero new transitive deps. Verified locally. The alternative (inline `requests`) would
  duplicate the tier-mapping logic that is the point of this integration.
- `[ASSUMPTION]` (non-blocking) Version `0.0.1`. Verified absent from the marketplace today
  (`/api/v1/plugins/livetennisapi/livetennisapi/0.0.1` → 404), which is what
  `pre-check-plugin.yaml` checks.

## Handoff

Build, then `/full-review`. Most relevant personas for this work: `/security-audit`
(credential handling, no key leakage into messages), `/code-logic-review` (the guard's
branch coverage and the player-major score formatter), and `/dependency-audit` (the
two-line `requirements.txt` a Dify reviewer will read).

## Status

All ten units complete, each committed green. See `PR_BODY.md` and the repo `README.md`.

### BLOCKER before filing — not fixable from here

`[FACT]` **`https://github.com/livetennisapi/livetennisapi-dify-plugin` returns 404.**
Checked 2026-07-22 alongside every other URL the plugin ships (all seven others return 200:
`/subscribe/free`, `/#pricing`, `/docs`, `/privacy`, `/terms`, the site root, and the API
health endpoint).

Why it matters: `plugin-submission-requirements.md` requires the README to carry "a link to
the source repository", and `plugin-review-guidelines.md` has the reviewer check exactly
that. The URL appears in `plugin/README.md` (source, issues, support), `plugin/PRIVACY.md`
(contact) and the PR body's **Source repository** field. A reviewer who clicks it gets a 404.

Not fixed here because publishing it means creating and pushing a remote, which this task
forbids. **Publish that repository before opening the PR** — the name is already the one the
sibling projects reference, so no file needs editing once it exists.
