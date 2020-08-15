"""Wrapping needed airtable api functions"""
import os
import logging
from collections import namedtuple
import requests


logger = logging.getLogger()


AUTH_TOKEN = os.environ.get("AIRTABLEAUTH", None)
API_ROOT = "https://api.airtable.com/v0/appovr6nWz1C6nz4Z/"
TOOL_TABLE_ROOT = API_ROOT + "pyRevit%20Tools%20Names"


ToolLocales = namedtuple("ToolLocales", "name,langs")


def _call_airtable(url):
    headers = {}
    # if no api token is provided, calls will be rate limited
    if AUTH_TOKEN:
        headers = {"Authorization": "Bearer " + AUTH_TOKEN}
    return requests.get(url, headers=headers)


def get_tool_locales():
    """Download the language table from airtable source"""
    records = []
    offset = ""
    logger.debug("getting tools names info")
    while True:
        uri = TOOL_TABLE_ROOT + (f"?offset={offset}" if offset else "")
        res = _call_airtable(uri)
        if res.ok:
            data = res.json()
            offset = data.get("offset", None)
            for record in data.get("records", []):
                fields = record["fields"]
                rname = fields.get("Name (English US)", None)
                if rname:
                    records.append(ToolLocales(name=rname, langs=fields))
            if not offset:
                break
    return records
