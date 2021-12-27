"""Wrapping needed github api v3 functions"""
import os
import logging
from collections import namedtuple
import requests


logger = logging.getLogger()


AUTH_TOKEN = os.environ.get("GITHUBTOKEN", "")
API_ROOT = "https://api.github.com/repos/eirannejad/pyRevit/"

API_ISSUES = API_ROOT + "issues/{ticket}"
API_RELEASES = API_ROOT + "releases"

TicketInfo = namedtuple("TicketInfo", ["url", "title", "data"])
ReleaseInfo = namedtuple("ReleaseInfo", ["name", "tag", "assets", "data"])
AssetInfo = namedtuple("AssetInfo", ["name", "downloads", "data"])


def _call_github(url):
    headers = {}
    # if no api token is provided, calls will be rate limited
    if AUTH_TOKEN:
        headers = {"Authorization": "token " + AUTH_TOKEN}
    return requests.get(url, headers=headers)


def get_ticket(ticket: str):
    """Get issue info"""
    logger.debug("getting ticket info for #%s", ticket)
    ticket_url = API_ISSUES.format(ticket=ticket)
    res = _call_github(ticket_url)
    if res.ok:
        issue = res.json()
        logger.debug("found ticket %s", issue)
        return TicketInfo(url=issue["url"], title=issue["title"], data=issue)
    return None


def get_releases():
    """Get all release infos"""
    releases = []
    res = _call_github(API_RELEASES)
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
