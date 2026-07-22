# Plugin Submission

## Plugin information

- **Author**: livetennisapi
- **Plugin name**: livetennisapi
- **Version**: 0.0.1
- **Source repository**: https://github.com/livetennisapi/livetennisapi-dify-plugin
- **Contact**: support@livetennisapi.com

## Submission type

- [x] New plugin
- [ ] Version update

## What changed

New plugin. Twelve read-only tools over the Live Tennis API, giving an agent or
workflow live tennis scores, schedules, results, players and rankings across
ATP, WTA, Challenger and ITF.

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

Every tool is a `GET`. The plugin has no write path of any kind.

Two things worth a reviewer's attention:

1. **Tier walls are normal results, not errors.** The API is tiered, so a user
   on a lower plan will hit endpoints their key does not unlock. Rather than
   surfacing a bare `403`, the plugin returns `ok: false` with a plain-English
   message naming the plan required and where to upgrade. Same for a rejected
   key, an unknown id and a rate limit. No tool raises, so a tier wall never
   fails a workflow node — the branch stays in the author's control via the
   `ok` and `reason` fields.
2. **Each tool emits both halves**: a text message for a model to read, and a
   JSON message with the identical facts for a workflow to consume without
   re-parsing English. Both are declared in each tool's `output_schema`.

## Risk level

- [x] Low risk
- [ ] Medium risk
- [ ] High risk

<!-- Select one based on the risk classification in docs/plugin-submission-requirements.md. -->

## Required checks

- [x] I have read and followed the [Marketplace submission requirements](https://github.com/langgenius/dify-plugins/blob/main/docs/plugin-submission-requirements.md).
- [x] I have read and comply with the Plugin Developer Agreement.
- [x] I tested this plugin on Dify Community Edition and Dify Cloud, or documented any limitation below.
- [x] The package contains only files needed at runtime.
- [x] The package does not contain secrets, local credentials, `.env` files, `.git` directories, virtual environments, caches, logs, or IDE files.
- [x] The package does not contain executables or bundled binaries, or I explained why they are required below.
- [x] The plugin README includes setup steps, usage instructions, required APIs or credentials, connection requirements, and the source repository link.
- [x] The plugin includes `PRIVACY.md` or a hosted privacy policy, and `manifest.yaml` references it.
- [x] All user-facing text is primarily in English, with any localized README files following the [i18n guidance](https://docs.dify.ai/en/develop-plugin/features-and-specs/plugin-types/multilingual-readme).

## Security and privacy notes

**Network destinations.** One, fixed and documented:
`https://api.livetennisapi.com/api/public/v1`. It is a module constant in
`livetennisapi_client.py`, deliberately **not** exposed as a credential or a
tool parameter, so the destination cannot be redirected by a user, a workflow or
a model. There is no arbitrary URL fetching, proxying, crawling or webhook
forwarding.

**Sensitive capabilities: none.** No command or code execution, no shell, no
SQL, no database access, no SSH/SFTP, no filesystem operations, no browser
automation, no bundled binaries. Every tool issues a `GET` and formats the
response.

**Credentials.** A single `api_key` (`secret-input`), sent as an
`Authorization: Bearer` header to the one host above. It is never logged, never
included in an error message, and never returned in tool output. The plugin
writes no files and keeps no cache or state between invocations.

**Input constraints.** `limit` parameters are coerced and clamped to 1–200; id
parameters are coerced to integers and rejected with a normal result if
unusable. Requests carry a 30-second timeout. Invalid input is answered, not
propagated.

**Please note explicitly, so you can re-classify if you disagree:** one tool,
`get_match_odds`, reports **match-winner market prices** — implied probability,
bid, ask and mid for a tennis match. I have classified the submission as Low
risk because this is read-only *reporting of publicly published prices*, and
because the requirements' High-risk bucket concerns health, financial,
biometric and similar **sensitive personal data**, which market prices are not.
The plugin cannot place, modify, settle or transact anything, and moves no money
or assets; there is no write path to any venue. I would rather flag this
plainly than have it discovered in review — if your reading differs, I am happy
for the label to be raised.

**Data returned** is public professional-sport information: player names,
nationalities, rankings, handedness, dates of birth, match results and scores.
No Dify user identity, conversation content, prompt or workflow variable is sent
anywhere. See `PRIVACY.md`.

**Dependencies: two lines.**

```
dify_plugin>=0.9.0
livetennisapi>=1.0.2
```

`livetennisapi` is the vendor's own published Python SDK for the API being
wrapped (PyPI, pure Python, MIT). It adds **exactly one distribution and zero
new transitive dependencies** — its only requirement, `httpx`, is already a
`dify_plugin` dependency. Verified by diffing a clean install:

```
dify_plugin alone: 37 distributions
with livetennisapi: 38 distributions
added by livetennisapi:
  livetennisapi
```

No direct-URL installs, no git-based installs, no pinned-to-nothing ranges.

## Local validation

Built with the official CLI (`dify-plugin-linux-amd64` v0.6.5):

```
$ dify plugin package ./plugin -o dist/livetennisapi-0.0.1.difypkg
2026/07/22 10:43:44 INFO plugin packaged successfully output_path=dist/livetennisapi-0.0.1.difypkg
```

**Package contents — 34 files, runtime only.** No `.git`, `__pycache__`, `.pyc`,
`.env`, virtual environment, cache, log, IDE, OS-generated or test file, and no
executable or binary:

```
$ unzip -l dist/livetennisapi-0.0.1.difypkg
      185  .difyignore
     3262  PRIVACY.md
     4626  README.md
    21951  _assets/icon.png
    14483  livetennisapi_client.py
      380  main.py
      709  manifest.yaml
     1988  provider/livetennisapi.py
     1114  provider/livetennisapi.yaml
       40  requirements.txt
             tools/{check_api_status,get_fixtures,get_live_matches,get_match,
                    get_match_analysis,get_match_events,get_match_odds,
                    get_match_score,get_player,get_recent_results,
                    get_upcoming_matches,search_players}.{py,yaml}
---------
   105784   34 files
```

**Your CI's own validators**, run locally against the unpacked package
(`langgenius/dify-marketplace-toolkit`, plugin daemon v0.6.5, Python 3.12.13):

```
$ python3 validator/test-plugin-install.py -d ./unpacked_plugin
Testing plugin in directory: ./unpacked_plugin
* Serving Flask app 'dify_plugin.core.server.serverless.request_reader'
!!! Detected 'Serving Flask app' in output, sending request to port 8080
!!! Request to port 8080 successful
!!! Plugin test result: success

$ python3 uploader/upload-package.py -d ./unpacked_plugin -t placeholder \
    --plugin-daemon-path ./dify-plugin-linux-amd64 -u https://marketplace.dify.ai -f --test
v0.6.5
2026/07/22 10:44:45 INFO plugin packaged successfully output_path=temp.difypkg
!!! Skip uploading package in testing
```

**Dependency install in a clean virtualenv** — resolves cleanly on Python 3.12:

```
$ pip install -r requirements.txt
dify_plugin == 0.10.0
livetennisapi == 1.0.2
httpx == 0.28.1
```

**Functional test suite — 12 tools, offline, no credentials and no network.** A
local `http.server` stub stands in for the API, so every path is exercised
without touching production or needing a key:

```
$ python test/test_tools.py
stub listening on http://127.0.0.1:34033

--- 1. every tool is importable and exposes _invoke ---     [12/12]
--- 2. no API key configured ---                            [12/12 return a normal result]
--- 3. success path ---                                     [12/12 ok=true]
  score formatting from player-major games: '6-4 3-2 (40-30)'
  analysis profile/thesis decoded: ['serve', 'hard-court record']
  detected tier against a stub that allows everything: ULTRA

--- 4. tier wall - every endpoint answers 403 upgrade_required ---
  get_recent_results     tier=BASIC  :: This data requires the BASIC plan, and the configured API key...
  get_match_events       tier=PRO    :: This data requires the PRO plan, and the configured API key...
  get_match_odds         tier=PRO    :: This data requires the PRO plan, and the configured API key...
  get_match_analysis     tier=ULTRA  :: This data requires the ULTRA plan, and the configured API key...
  get_live_matches       unaffected by walls elsewhere: ok=True
  check_api_status       identified tier from the wall: FREE

--- 5. 401 rejected key / 404 unknown id / 429 rate limit ---
  all four probed tools return a normal result with the right reason; none raises

--- 6. missing or unusable parameters ---                   [rejected before any request]
--- 7. run_tool base_url injection ---                      ok=True count=1

OK - 12 tools x (no key, success, 403 tier wall, 401, 404, 429, bad params);
16 distinct upstream paths exercised; nothing raised
```

Version availability checked against the Marketplace, as your `Check If Version
Exists` step does:

```
$ curl -o /dev/null -w '%{http_code}' \
    https://marketplace.dify.ai/api/v1/plugins/livetennisapi/livetennisapi/0.0.1
404
```

## Reviewer notes

- **Scope of my testing, stated precisely.** I ran the official plugin-install
  validator (the plugin boots under the serverless runner and answers a
  request), the packaging check, a clean-room dependency install, and the
  12-tool functional suite above against a local stub. I did **not** run it
  against a live Dify Cloud tenant, and my Community Edition check was the
  daemon-level install validator rather than a full CE UI walkthrough. Flagging
  that rather than implying broader coverage than I have.
- **No i18n.** All user-facing text is English. I would rather ship one accurate
  language than machine-translated tool descriptions a model has to act on.
- **Version `0.0.1`**, first release, confirmed absent from the Marketplace.
- The icon is the project's own brand mark, not the template placeholder.
