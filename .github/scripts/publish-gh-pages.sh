#!/usr/bin/env bash
# Publish to (or remove from) the gh-pages branch without touching the rest of it.
#
#   publish-gh-pages.sh version <site-dir> <dev|X.Y>
#   publish-gh-pages.sh publish <site-dir> pr-preview/pr-<number>
#   publish-gh-pages.sh remove  pr-preview/pr-<number>
#
# "version" publishes the docs of a release (X.Y) or of develop (dev) into
# <version>/ and lets docs_versions.py update versions.json, latest/ and the
# root redirects. "publish" and "remove" manage pull request previews. No mode
# touches another version or another preview.
#
# Environment:
#   PAGES_DIR       checkout of the gh-pages branch with push access (default: gh-pages)
#   COMMIT_MESSAGE  commit message (default: derived from the arguments)
#
# The push is retried on top of a fresh fetch, so concurrent deploys of other
# previews do not make this one fail.
set -euo pipefail

BRANCH="gh-pages"
PREVIEW_ROOT="pr-preview"
PAGES_DIR="${PAGES_DIR:-gh-pages}"
SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"

mode="${1:-}"
case "$mode" in
  version) site="${2:?site directory required}"; target="${3:?version required}" ;;
  publish) site="${2:?site directory required}"; target="${3:?target required}" ;;
  remove)  site=""; target="${2:?target required}" ;;
  *) echo "usage: $0 version <site-dir> <dev|X.Y> | publish <site-dir> <target> | remove <target>" >&2; exit 2 ;;
esac

if [[ "$mode" == "version" ]]; then
  if [[ ! "$target" =~ ^(dev|[0-9]+\.[0-9]+)$ ]]; then
    echo "error: version must be 'dev' or 'X.Y', got '$target'" >&2
    exit 2
  fi
elif [[ ! "$target" =~ ^${PREVIEW_ROOT}/pr-[0-9]+$ ]]; then
  echo "error: target must be '${PREVIEW_ROOT}/pr-<number>', got '$target'" >&2
  exit 2
fi
if [[ "$mode" != "remove" ]]; then
  [[ -f "$site/index.html" ]] || { echo "error: $site/index.html not found" >&2; exit 1; }
  [[ ! -e "$site/$PREVIEW_ROOT" ]] || { echo "error: site must not contain $PREVIEW_ROOT/" >&2; exit 1; }
  site="$(cd "$site" && pwd)"
fi

apply() {
  rm -rf "./$target"
  if [[ "$mode" != "remove" ]]; then
    mkdir -p "./$target"
    cp -a "$site/." "./$target/"
    rm -f "./$target/CNAME"
  fi
  if [[ "$mode" == "version" ]]; then
    [[ -f CNAME || ! -f "$site/CNAME" ]] || cp "$site/CNAME" CNAME
    "$PYTHON" "$SCRIPTS_DIR/docs_versions.py" . "$target"
  fi
  touch .nojekyll
}

changed="false"
cd "$PAGES_DIR"
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

for attempt in 1 2 3 4 5; do
  git fetch --quiet --depth 1 origin "$BRANCH"
  git reset --quiet --hard FETCH_HEAD
  git clean --quiet -fdx
  apply
  git add --all
  if git diff --cached --quiet; then
    echo "Nothing to change for '$target'."
    break
  fi
  git commit --quiet -m "${COMMIT_MESSAGE:-docs: $mode $target}"
  if git push --quiet origin "HEAD:$BRANCH"; then
    changed="true"
    echo "Pushed '$mode $target' to $BRANCH."
    break
  fi
  if [[ "$attempt" == 5 ]]; then
    echo "error: could not push to $BRANCH after $attempt attempts" >&2
    exit 1
  fi
  echo "Push rejected, retrying ($attempt/5)..."
  sleep $((attempt * 3))
done

if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  echo "changed=$changed" >> "$GITHUB_OUTPUT"
fi
