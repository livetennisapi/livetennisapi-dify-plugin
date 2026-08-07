# Changelog

All notable changes to the Live Tennis API Dify plugin. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.0.6] — 2026-08-07

### Added
- Six new tools over the API's documented surface, following the existing
  conventions (prose + JSON, tier gates named in descriptions, no tool raises):
  - `get_h2h` — head-to-head across the 1968–2022 archive plus current
    matches (BASIC).
  - `get_archive_matches`, `get_archive_players`, `get_archive_career` —
    the 1968–2022 results archive (BASIC).
  - `get_rankings` — the published ranking table for one system (atp, wta,
    itf_jt, itf_mt, itf_wt), optionally as of a past date (PRO).
  - `get_match_statistics` — in-play statistics, derived and measured
    families (ULTRA).
- `juniors` value for `get_matches`' `tour` parameter — the API's tours are
  ATP, WTA, Challenger, ITF and juniors.
- Daily-cap 429s now surface `scope="day"`, `limit_per_day` and the absolute
  `resets_at` instant; the 24-hour abuse throttle is its own
  `reason: "abuse_throttled"` with `retry_at_epoch`; ambiguous player-name
  fragments return `reason: "ambiguous_name"` with the candidate list.
- CI (`.github/workflows/ci.yml`): ruff lint, the offline stub-server test
  suite, a product-copy truth pin (`scripts/truthcheck.sh`), and a check that
  the `.difypkg` packages cleanly.

### Changed
- Reconciled the 0.0.4/0.0.5 Marketplace releases — upstream maintainer
  packaging fixes, folded back into source (see below).
- Dependency floor raised to `livetennisapi>=1.3.0`; the `tour`-keyword
  request shim in `list_matches` is gone (the SDK has it natively).
- Marketplace listing copy: current quota grid (FREE 100/day, BASIC 1,000/day,
  PRO 10,000/day, ULTRA 500,000/day), five-tour phrasing, tier-gate table for
  all twelve tools, contact hello@livetennisapi.com.

## [0.0.5] — 2026-08-03

Published directly to `langgenius/dify-plugins` by the Dify maintainers
(packaging fix, no change from this repo at the time — reconciled here in
0.0.6). Removes the `entertainment` manifest tag, leaving `news`.

## [0.0.4] — 2026-08-03

Published directly to `langgenius/dify-plugins` by the Dify maintainers.
Version bump only; content identical to 0.0.3.

## [0.0.3] — 2026-08-02

### Fixed
- The API documentation link points at https://docs.livetennisapi.com (the
  address printed by earlier versions redirected to the homepage).
- The repository carries the MIT licence text as a `LICENSE` file.

## [0.0.2] — 2026-07-26

Narrowed the plugin to the API's documented public endpoints. **Breaking for
workflows built on 0.0.1.**

### Changed
- `get_live_matches`, `get_upcoming_matches`, `get_recent_results` replaced by
  `get_matches` with a `status` parameter; new `tour` parameter.

### Removed
- `get_match_events`, `get_match_odds`, `get_match_analysis`,
  `check_api_status`. Market and analysis data is embedded in `get_match`.

### Fixed
- The API key travels in the `x-api-key` header, as documented, instead of
  `Authorization: Bearer`.
- `get_match`'s output schema described the market price list incorrectly.

## [0.0.1] — 2026-07-22

Initial release.
