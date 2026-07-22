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
│   │   ├── livetennisapi.yaml   credential schema + the 12 tool manifests
│   │   └── livetennisapi.py     credential validation
│   └── tools/                   12 x (<tool>.yaml + <tool>.py)
├── test/
│   ├── stub_api.py              local stand-in for the API
│   └── test_tools.py            drives all 12 tools offline
├── dist/
│   └── livetennisapi-0.0.1.difypkg
├── PR_BODY.md                   the submission PR body, template-filled
└── BUILD_PLAN.md                how this was built, and why
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

It drives all twelve tools through: no key, the success path, a 403 tier wall,
401, 404, 429, and unusable parameters. The tier-wall pass is the point — it
asserts that every gated tool returns an explanation naming the required plan
and that **nothing raises**.

## Build

Needs the `dify` CLI, which is the plugin daemon binary:

```bash
curl -sL -o dify \
  https://github.com/langgenius/dify-plugin-daemon/releases/download/0.6.5/dify-plugin-linux-amd64
chmod +x dify

./dify plugin package ./plugin -o dist/livetennisapi-0.0.1.difypkg
```

Then confirm the package holds runtime files only:

```bash
unzip -l dist/livetennisapi-0.0.1.difypkg
```

## Submit

The upstream repo takes **one file per PR — the `.difypkg`, and nothing else**.
The plugin source is not committed there. Verified against the repo: 1059 of its
1154 tracked files are `.difypkg`, and each of the last six merged PRs touched a
single package file.

1. Fork `langgenius/dify-plugins`.
2. Copy the package to `livetennisapi/livetennisapi/livetennisapi-0.0.1.difypkg`
   — a **top-level** `<author>/<plugin_name>/` directory, not under `plugins/`.
3. Open the PR using `PR_BODY.md` verbatim as the body.

Two things the CI will fail you on if you improvise:

- **Tick exactly one risk box.** `pr-risk-label.yaml` matches
  `/^- \[[xX]\] Low risk\s*$/m` and counts all three patterns — ticking two
  labels the PR `risk: missing` just as surely as ticking none. `PR_BODY.md` is
  already correct; check it with:

  ```bash
  node -e 'const b=require("fs").readFileSync("PR_BODY.md","utf8");
    console.log(/^- \[[xX]\] Low risk\s*$/m.test(b))'
  ```

- **Bump the version** for any resubmission. `pre-check-plugin.yaml` fails if
  `<author>/<name>/<version>` already exists on the Marketplace:

  ```bash
  curl -o /dev/null -w '%{http_code}\n' \
    https://marketplace.dify.ai/api/v1/plugins/livetennisapi/livetennisapi/0.0.1
  ```

  `404` means the version is free to use.

## Licence

MIT.
