from __future__ import annotations

from dify_plugin import DifyPluginEnv, Plugin

# 60s is generous for this API — every call is a single read and the SDK's own
# per-request timeout is 30s. The margin covers the SDK's two retries on 429/5xx.
plugin = Plugin(DifyPluginEnv(MAX_REQUEST_TIMEOUT=60))


def main() -> None:
    plugin.run()


if __name__ == "__main__":
    main()
