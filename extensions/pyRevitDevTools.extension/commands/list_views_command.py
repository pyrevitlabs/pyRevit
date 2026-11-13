# -*- coding: utf-8 -*-
"""Reference runner command: logs the view count of every model passed to ``pyrevit run``.

Run it with ``pyrevit run list_views <model_file>``. The runner defines
``__models__`` (model paths) and ``__logfile__`` (log path); output windows
are suppressed, so results go to the logger.
"""

from pyrevit import DB, HOST_APP, script

logger = script.get_logger()

for model_path in __models__:
    model_doc = HOST_APP.app.OpenDocumentFile(model_path)
    try:
        views = DB.FilteredElementCollector(model_doc).OfClass(DB.View)
        view_count = len([view for view in views if not view.IsTemplate])
        logger.info("%s: %d views", model_path, view_count)
    finally:
        model_doc.Close(False)
