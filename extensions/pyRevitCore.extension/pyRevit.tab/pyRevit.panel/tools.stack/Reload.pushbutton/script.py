"""Reload pyRevit into new session."""

# -*- coding=utf-8 -*-
# pylint: disable=import-error,invalid-name,broad-except

from pyrevit import script
from pyrevit.loader import sessionmgr

logger = script.get_logger()
results = script.get_results()

# Re-load pyrevit session.
logger.info("Reloading....")
newsession = sessionmgr.reload_pyrevit()

try:
    results.newsession = newsession
except Exception as result_err:
    logger.debug(
        "Session results dictionary unavailable after reload "
        "(runtime was reset by session load): %s | new session: %s",
        result_err,
        newsession,
    )
