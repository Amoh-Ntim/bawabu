#!/usr/bin/env bash
# Publishes every test-lab package to the Verdaccio registry.
#
#   BAWABU_REGISTRY=https://…modal.run  ./testlab/publish.sh
#
# Reads VERDACCIO_AUTH_BASIC from .env for the login. Packages are published in folder order,
# so docs-gen-postinstall 1.0.0 lands before docs-gen-postinstall-2's 2.0.0 (making 2.0.0 latest).
# These packages are NEVER published to the public npm — the registry is explicit on every call.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
root="$(dirname "$here")"
registry="${BAWABU_REGISTRY:?set BAWABU_REGISTRY to the Verdaccio URL}"

# shellcheck disable=SC1091
set -a; . "$root/.env"; set +a
: "${VERDACCIO_AUTH_BASIC:?VERDACCIO_AUTH_BASIC missing from .env}"

host="${registry#https://}"; host="${host%/}"

npmrc="$(mktemp)"
trap 'rm -f "$npmrc"' EXIT
cat >"$npmrc" <<EOF
registry=$registry
//$host/:_auth="$VERDACCIO_AUTH_BASIC"
always-auth=true
EOF

# Publish in (name, version) order, not folder order: a hijacked package's clean 1.0.0 must be
# published before its 2.0.0, because Bawabu compares each version with the one published before it.
ordered="$(for d in "$here"/packages/*/; do
  node -e 'const dir = require("path").resolve(process.argv[1]); const p = require(dir + "/package.json"); console.log([p.name, p.version, dir].join("\t"))' "$d"
done | sort -t "$(printf '\t')" -k1,1 -k2,2V)"

published=0
while IFS="$(printf '\t')" read -r name version dir; do
  echo "→ publishing $name@$version"
  if npm publish "$dir" --userconfig "$npmrc" --registry "$registry" 2>&1 | sed 's/^/   /'; then
    published=$((published + 1))
  else
    echo "   (skipped: already published or error above)"
  fi
done <<<"$ordered"
echo "done: $published package versions published to $registry"
