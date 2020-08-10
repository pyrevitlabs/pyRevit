"""Simple github api v3 io"""
import os
import logging
from collections import namedtuple
import requests


logger = logging.getLogger()


AUTH_TOKEN = os.environ.get('GITHUBAUTH', '')
API_ROOT ='https://api.github.com/repos/eirannejad/pyRevit/'
API_ISSUES = API_ROOT +'issues/{ticket}'


TicketInfo = namedtuple("TicketInfo", ["url", "title"])


def get_ticket(ticket: str):
    """Get title of a github issue"""
    logger.debug('getting ticket info for #%s', ticket)
    ticket_url = API_ISSUES.format(ticket=ticket)
    res = requests.get(ticket_url, headers={'Authorization': 'token ' + AUTH_TOKEN})
    if res.ok:
        issue = res.json()
        logger.debug('found ticket %s', issue)
        return TicketInfo(url=issue["url"], title=issue["title"])
    return None
