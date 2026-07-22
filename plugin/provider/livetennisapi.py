from __future__ import annotations

from typing import Any

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError
from livetennisapi import LiveTennisAPIError, RateLimited, Unauthorized, UpgradeRequired

from livetennisapi_client import SIGNUP_URL, api_key_of, make_client


class LiveTennisAPIProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        """Prove the key works before the user saves it.

        ``/matches`` rather than ``/health``: health answers without a key at
        all, so it would happily accept a typo. A live-matches read is the
        cheapest call that actually exercises the key, and it is on the FREE
        tier -- validating against anything higher would reject valid keys.

        Only an outright rejection means the credential is bad. A tier wall or
        a rate limit both prove the opposite -- the API recognised the key and
        answered about the *plan*, not the key -- so both are accepted. Failing
        them would lock out a valid key for the wrong reason.
        """
        if not api_key_of(credentials):
            raise ToolProviderCredentialValidationError(
                f"An API key is required. Get a free key, no card, at {SIGNUP_URL}"
            )

        try:
            with make_client(credentials) as client:
                client.list_matches(status="live", limit=1)
        except Unauthorized as exc:
            raise ToolProviderCredentialValidationError(
                "The Live Tennis API rejected this key. Check it was copied in full "
                f"(keys start with 'twjp_'). Keys are at {SIGNUP_URL}"
            ) from exc
        except (UpgradeRequired, RateLimited):
            return
        except LiveTennisAPIError as exc:
            raise ToolProviderCredentialValidationError(
                f"Could not verify the key against the Live Tennis API: {exc}"
            ) from exc
