#!/usr/bin/env bash
# Create or update the single docs-preview comment on a pull request.
#
#   pr-sticky-comment.sh <pr-number> <body-file> [--update-only]
#
# Needs GH_TOKEN and GITHUB_REPOSITORY. With --update-only nothing is posted
# when the pull request has no docs-preview comment yet.
set -euo pipefail

MARKER="<!-- pyrevit-docs-preview -->"
pr="${1:?pull request number required}"
body_file="${2:?body file required}"
update_only="${3:-}"

[[ "$pr" =~ ^[0-9]+$ ]] || { echo "error: invalid pull request number" >&2; exit 2; }

body="$(printf '%s\n%s\n' "$MARKER" "$(cat "$body_file")")"

comment_id="$(gh api "repos/$GITHUB_REPOSITORY/issues/$pr/comments" --paginate \
  | jq -r --arg marker "$MARKER" \
      '.[] | select(.user.login == "github-actions[bot]") | select(.body | startswith($marker)) | .id' \
  | head -n 1)"

if [[ -n "$comment_id" ]]; then
  gh api -X PATCH "repos/$GITHUB_REPOSITORY/issues/comments/$comment_id" -f body="$body" > /dev/null
elif [[ "$update_only" != "--update-only" ]]; then
  gh api -X POST "repos/$GITHUB_REPOSITORY/issues/$pr/comments" -f body="$body" > /dev/null
fi
