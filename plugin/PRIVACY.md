# Privacy Policy — Live Tennis API plugin

Last updated: 2026-08-07

## Summary

This plugin collects no personal data, stores nothing, and logs nothing. It
forwards your tool arguments to one fixed third-party API and returns the
answer. It is the thinnest possible layer between Dify and
`api.livetennisapi.com`.

## What the plugin sends, and where

The plugin makes outbound HTTPS requests to exactly one destination:

```
https://api.livetennisapi.com/api/public/v1
```

This host is a constant in the plugin's source. It is not user-configurable and
the plugin has no other network destination.

Each request carries:

| Sent | Why |
| --- | --- |
| Your Live Tennis API key, in the `x-api-key` request header | Authenticates the request and identifies your plan |
| The tool's arguments — a match id, a player id, player names, a match status, a tour, a ranking system, a date or date range, a round code, a result limit | These are the query itself |
| A `User-Agent` identifying the client library and version | Standard HTTP practice |

Nothing else leaves the plugin. No Dify user identity, no conversation content,
no prompts, no workflow variables, and no data from any other node are sent
anywhere.

## What the plugin stores

Nothing. The plugin holds no database, writes no files, and keeps no cache. Each
tool invocation opens a connection, reads a response, and discards it. Nothing
persists between invocations.

## What the plugin logs

Nothing. The plugin emits no log output of its own. In particular, the API key
is never written to a log, never included in an error message, and never
returned in a tool result.

## Personal data

The plugin does not collect, process or store personal data belonging to you or
to your users.

The **data it returns** is publicly available professional-sport information:
player names, nationalities, rankings, handedness, dates of birth, match results
and scores. This concerns professional tennis players in their public
professional capacity and is the same information published on tournament
scoreboards and broadcasts. Nothing about the Dify user is involved.

## Credential handling

Your Live Tennis API key is stored by Dify as a `secret-input` credential,
encrypted at rest by your Dify installation. The plugin reads it only to sign
outbound requests to `api.livetennisapi.com`. It is not transmitted to any other
party, not persisted by the plugin, and not exposed in tool output.

To revoke access, remove the credential in Dify or revoke the key at
https://livetennisapi.com.

## Third-party processing

Requests are served by the Live Tennis API, operated by the plugin author. Its
handling of API requests is governed by its own policies:

- Privacy policy: https://livetennisapi.com/privacy
- Terms of service: https://livetennisapi.com/terms

## Scope of access

The plugin performs read-only `GET` requests. It has no write capability of any
kind — it cannot create, modify, delete or transact anything. It executes no
code or commands, runs no SQL, touches no filesystem, drives no browser, and
fetches no user-supplied URL.

## Changes

Material changes to this policy will accompany a new plugin version and be noted
in the changelog of the source repository.

## Contact

https://github.com/livetennisapi/livetennisapi-dify-plugin/issues
