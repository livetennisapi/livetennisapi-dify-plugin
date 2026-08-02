# livetennisapi-dify-plugin

The Live Tennis API plugin for [Dify](https://dify.ai), plus everything needed
to submit it to `langgenius/dify-plugins`.

The user-facing documentation is `plugin/README.md` — that is the file shipped
inside the package and shown on the Marketplace. This file is for whoever
builds and submits it.

## Layout

```
.
├── plugin/                      the plugin project -- this is what gets packaged
│   ├── manifest.yaml            author, name, version, runner, icon, privacy
│   ├── main.py                  entrypoint: Plugin(DifyPluginEnv(...)).run()
│   ├── README.md                shipped user docs
│   ├── PRIVACY.md               shipped privacy policy (mandatory)
│   ├── requirements.txt         dify_plugin + livetennisapi
│   ├── .difyignore              keeps caches/tests/VCS out of the package
│   ├── _assets/icon.png         brand mark; CI resolves manifest.icon here
│   ├── livetennisapi_client.py  shared client, formatters, tier-aware guard
│   ├── provider/
│   │   ├── livetennisapi.yaml   credential schema + the 6 tool manifests
│   │   └── livetennisapi.py     credential validation
│   └── tools/                   6 x (<tool>.yaml + <tool>.py)
├── test/
│   ├── stub_api.py              local stand-in for the API
│   └── test_tools.py            drives all 6 tools offline
├── dist/
│   ├── livetennisapi-0.0.1.difypkg
│   ├── livetennisapi-0.0.2.difypkg   as merged in langgenius/dify-plugins#2773
│   └── livetennisapi-0.0.3.difypkg
└── LICENSE                      MIT -- root only; the package ships no licence file
```

## Develop

Requires Python 3.12 — the runner version declared in `manifest.yaml`, and the
version the upstream CI uses.

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r plugin/requirements.txt
```

## Test

No credentials and no network. A local `http.server` stub stands in for the API,
so the suite never touches production.

```bash
python test/test_tools.py
```

It drives all six tools through: no key, the success path, a 403 tier wall,
401, 404, 429, and unusable parameters. Two invariants are the point:
**nothing raises** — every expected failure returns a plain-English result a
workflow can branch on — and **the API key travels in the `x-api-key` header**,
asserted on the wire so a client-library default can never silently move it
back to `Authorization: Bearer`.

## Build

Needs the `dify` CLI, which is the plugin daemon binary:

```bash
curl -sL -o dify \
  https://github.com/langgenius/dify-plugin-daemon/releases/download/0.6.5/dify-plugin-linux-amd64
chmod +x dify

./dify plugin package ./plugin -o dist/livetennisapi-<version>.difypkg
```

Then confirm the package holds runtime files only:

```bash
unzip -l dist/livetennisapi-<version>.difypkg
```

There is no `LICENSE` inside the package, deliberately: the upstream submission
requirements limit a `.difypkg` to files the plugin needs at runtime, and the
marketplace's own packages carry none. The MIT licence text lives at this
repo's root.

## Submit

The upstream repo takes **one file per PR — the `.difypkg`, and nothing else**.
The plugin source is not committed there. Verified against the repo: 1059 of its
1154 tracked files are `.difypkg`, and each of the last six merged PRs touched a
single package file.

1. Fork `langgenius/dify-plugins`.
2. Copy the package to `livetennisapi/livetennisapi/livetennisapi-<version>.difypkg`
   — a **top-level** `<author>/<plugin_name>/` directory, not under `plugins/`.
3. Open the PR filling the upstream PR template completely. Use the merged
   [#2773](https://github.com/langgenius/dify-plugins/pull/2773) as the
   precedent for structure and level of disclosure.

Two things the CI will fail you on if you improvise:

- **Tick exactly one risk box.** `pr-risk-label.yaml` matches
  `/^- \[[xX]\] Low risk\s*$/m` and counts all three patterns — ticking two
  labels the PR `risk: missing` just as surely as ticking none.

- **Bump the version** for any resubmission. `pre-check-plugin.yaml` fails if
  `<author>/<name>/<version>` already exists on the Marketplace:

  ```bash
  curl -o /dev/null -w '%{http_code}\n' \
    https://marketplace.dify.ai/api/v1/plugins/livetennisapi/livetennisapi/<version>
  ```

  `404` means the version is free to use.

**Merged is not published.** After a merge, the upstream `upload-merged-plugin`
workflow pushes the package to the Marketplace — and it can fail independently
of the PR. That is exactly what happened to 0.0.2: #2773 merged on 2026-07-28,
but the upload step died on a Marketplace-side `database error`, so the
Marketplace kept serving 0.0.1. After a merge, always confirm:

```bash
curl -s -o /dev/null -w '%{http_code}\n' \
  https://marketplace.dify.ai/api/v1/plugins/livetennisapi/livetennisapi/<version>
```

`200` means it is actually live. If it is not, check the workflow run for the
merge commit in `langgenius/dify-plugins` and ask the maintainers to re-run it —
or ship the next version, whose merge triggers a fresh upload.

## Licence

MIT.
