#!/bin/sh
# Truth pin for product copy. POSIX sh, no dependencies beyond git + grep.
#
# Forbids stale product facts anywhere in tracked text files, and requires the
# current ones where quotas are stated. CHANGELOG.md is exempt (it describes
# history), as are the binary dist/ packages, the icon, and this script.
set -u

fail=0

files=$(git ls-files | grep -v -e '^CHANGELOG\.md$' -e '^dist/' -e '\.png$' -e '^scripts/truthcheck\.sh$')

forbid() {
    pattern=$1
    label=$2
    # shellcheck disable=SC2086
    hits=$(printf '%s\n' "$files" | xargs grep -riEln -- "$pattern" 2>/dev/null || true)
    if [ -n "$hits" ]; then
        echo "TRUTHCHECK FAIL: $label"
        printf '%s\n' "$hits" | sed 's/^/  /'
        fail=1
    fi
}

# Stale quota copy: the free tier is 100/day (since 2026-08-06); no tier is
# "100,000/day" and free was never 1,000/day after the change.
forbid '100[,.]?000 requests (per|a) day' 'stale "100,000 requests per day" quota copy'
forbid '100k (requests|calls)' 'stale "100k requests" quota copy'
forbid 'free[^.]{0,40}1[,.]?000 (requests|calls)? ?(per|a|/) ?day' 'free tier described as 1,000/day (it is 100/day)'
forbid 'free[^.]{0,40}1k (per|a|/) ?day' 'free tier described as 1k/day (it is 100/day)'

# The docs live at docs.livetennisapi.com, never livetennisapi.com/docs.
forbid 'livetennisapi\.com/docs' 'wrong docs URL (use docs.livetennisapi.com)'

# Org identity, not a personal account.
forbid 'bensynapse' 'personal account name in repo content'

# The daily reset is an absolute local-midnight-derived instant, never UTC midnight.
forbid 'midnight UTC' 'daily reset described as "midnight UTC"'

# If the repo states quotas at all, the current facts must be present.
if printf '%s\n' "$files" | xargs grep -riEl -- 'per day|/day' 2>/dev/null | grep -q .; then
    if ! printf '%s\n' "$files" | xargs grep -riEl -- '100 (requests )?(per|a|/) ?day|100/day' 2>/dev/null | grep -q .; then
        echo 'TRUTHCHECK FAIL: quotas are stated but the FREE 100/day figure is missing'
        fail=1
    fi
    if ! printf '%s\n' "$files" | xargs grep -rlF -- 'docs.livetennisapi.com' 2>/dev/null | grep -q .; then
        echo 'TRUTHCHECK FAIL: quotas are stated but docs.livetennisapi.com is not linked'
        fail=1
    fi
fi

if [ "$fail" -eq 0 ]; then
    echo 'truthcheck: OK'
fi
exit "$fail"
