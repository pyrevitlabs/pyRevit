"""Wrapping needed github api v3 functions"""
import os
import logging
import json
from collections import namedtuple
import requests


logger = logging.getLogger()


AUTH_TOKEN = os.environ.get("GITHUB_TOKEN", "")
API_ROOT = "https://api.github.com/repos/pyrevitlabs/pyRevit/"

API_ISSUES = API_ROOT + "issues/{ticket}"
API_ISSUE_COMMENTS = API_ROOT + "issues/{ticket}/comments"
API_RELEASES = API_ROOT + "releases"

LabelInfo = namedtuple("LabelInfo", ["name", "description"])
TicketInfo = namedtuple("TicketInfo", ["url", "title", "data", "labels"])
ReleaseInfo = namedtuple("ReleaseInfo", ["name", "tag", "assets", "data"])
AssetInfo = namedtuple("AssetInfo", ["name", "downloads", "data"])


def _make_headers():
    headers = {"Accept": "application/vnd.github.v3+json"}
    # if no api token is provided, calls will be rate limited
    if AUTH_TOKEN:
        headers["Authorization"] = "token " + AUTH_TOKEN
    return headers


def _get_github(url: str):
    return requests.get(url, headers=_make_headers())


def _post_github(url: str, data: str):
    return requests.post(url, data=data, headers=_make_headers())


def get_ticket(ticket: str):
    """Get issue info"""
    logger.debug("getting ticket info for #%s", ticket)
    ticket_url = API_ISSUES.format(ticket=ticket)
    res = _get_github(ticket_url)
    if res.ok:
        issue = res.json()
        logger.debug("found ticket %s", issue)
        ticket_labels = []
        if labels := issue.get("labels", []):
            ticket_labels = [
                LabelInfo(name=x["name"], description=x.get("description") or "")
                for x in labels
            ]
        else:
            ticket_labels = []

        return TicketInfo(
            url=issue["url"],
            title=issue["title"],
            data=issue,
            labels=ticket_labels,
        )
    return None


def get_releases():
    """Get all release infos"""
    releases = []
    res = _get_github(API_RELEASES)
    if res.ok:
        for release in res.json():
            logger.debug("found release %s", release["name"])
            # logger.debug(release)
            assets = [
                AssetInfo(name=x["name"], downloads=x["download_count"], data=x)
                for x in release["assets"]
            ]
            releases.append(
                ReleaseInfo(
                    name=release["name"],
                    tag=release["tag_name"],
                    assets=assets,
                    data=release,
                )
            )
    return releases


def post_comment(ticket: str, comment: str):
    """Post a comment on an issue thead"""
    logger.debug("posting comment on ticket #%s", ticket)
    ticket_url = API_ISSUE_COMMENTS.format(ticket=ticket)
    _post_github(ticket_url, json.dumps({"body": comment}))
