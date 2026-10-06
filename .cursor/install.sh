#!/usr/bin/env bash
# Cloud Agent bootstrap for pyRevit's Linux-supported development surface:
# the mkdocs documentation site, ruff docstring linting, and the Go CLI
# autocomplete generator. The Revit add-in and product DLLs are built only on
# Windows (see .github/workflows/ci.yml) and are intentionally out of scope on
# a Linux Cloud Agent. Kept idempotent so it can rerun against cached state.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Python 3.14 toolchain, matching .github/workflows/docs.yml and the Pipfile.
if ! command -v python3.14 >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y software-properties-common
  sudo add-apt-repository -y ppa:deadsnakes/ppa
  sudo apt-get update
  sudo apt-get install -y python3.14 python3.14-venv python3.14-dev
fi

# pipenv on the system PATH so `pipenv run ...` works in any shell.
if ! command -v pipenv >/dev/null 2>&1; then
  sudo pip3 install pipenv --break-system-packages
fi

# Docs and lint dependencies, resolved from the committed Pipfile.lock.
export PIPENV_VENV_IN_PROJECT=1
pipenv --python /usr/bin/python3.14 sync

# Go modules for the pyRevit CLI autocomplete generator.
if command -v go >/dev/null 2>&1; then
  (cd dev/pyRevitLabs/pyRevitCLIAutoComplete && go mod download)
fi
