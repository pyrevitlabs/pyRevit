#!/bin/bash
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-.}"

if ! command -v dotnet >/dev/null; then
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq dotnet-sdk-10.0
fi

uv python install --quiet 3.14
command -v pipenv >/dev/null || uv tool install --quiet pipenv

git submodule update --init --recursive

hashes=.venv/.session-start.sha256
if ! sha256sum --check --status "$hashes" 2>/dev/null; then
  rm -f "$hashes"
  PIPENV_VENV_IN_PROJECT=1 PIPENV_YES=1 pipenv install --dev --python "$(uv python find 3.14)"
  sha256sum .claude/hooks/session-start.sh Pipfile Pipfile.lock > "$hashes"
fi

pipenv run pre-commit install >/dev/null

echo 'export EnableWindowsTargeting=true' >> "$CLAUDE_ENV_FILE"
