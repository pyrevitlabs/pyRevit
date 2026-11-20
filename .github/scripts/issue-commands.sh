#!/usr/bin/env bash
# Slash commands that maintainers type as the first line of an issue comment,
# and the follow-up that clears the needs-more-info label once someone outside
# the team answers. Commands from anyone else are ignored.
#
#   /more-info     adds the needs-more-info label (issues only)
#   /install-fix   posts .github/issue-replies/install-fix.md (issues only)
#
# In a reply, "{{ author }}" is replaced with the login of the issue author.
#
# Environment:
#   GH_TOKEN            token with issues and pull-requests write access
#   GH_REPO             owner/name of the repository
#   ISSUE_NUMBER        issue or pull request the comment was posted on
#   ISSUE_AUTHOR        login of the issue or pull request author
#   ISSUE_LABELS        JSON array of the label names at the time of the comment
#   IS_PULL_REQUEST     "true" when the comment is on a pull request
#   COMMENT_BODY        text of the comment
#   AUTHOR_ASSOCIATION  association of the commenter with the repository
set -euo pipefail

PENDING_LABEL="needs-more-info"
REPLIES_DIR="$(dirname "$0")/../issue-replies"
ISSUE_API="repos/$GH_REPO/issues/$ISSUE_NUMBER"

post_reply() {
  local body
  body="$(cat "$REPLIES_DIR/$1.md")"
  gh api "$ISSUE_API/comments" -f body="${body//'{{ author }}'/$ISSUE_AUTHOR}" --silent
}

run_command() {
  case "$1" in
    more-info) gh api "$ISSUE_API/labels" -f "labels[]=$PENDING_LABEL" --silent ;;
    install-fix) post_reply install-fix ;;
    *) echo "Unknown command, nothing to do." ;;
  esac
}

case "$AUTHOR_ASSOCIATION" in
  OWNER | MEMBER | COLLABORATOR) from_team=true ;;
  *) from_team=false ;;
esac

first_line="$(printf '%s\n' "$COMMENT_BODY" | head -n 1 | tr -d '\r' | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"

if [[ "$from_team" == "true" ]]; then
  if [[ "$IS_PULL_REQUEST" != "true" && "$first_line" == /?* ]]; then
    command="${first_line#/}"
    run_command "${command%%[[:space:]]*}"
  fi
  exit 0
fi

if jq -e --arg label "$PENDING_LABEL" 'index($label) != null' <<< "$ISSUE_LABELS" > /dev/null; then
  gh api --method DELETE "$ISSUE_API/labels/$PENDING_LABEL" --silent
fi
