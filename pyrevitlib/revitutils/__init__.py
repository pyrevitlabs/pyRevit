from pyrevit.coreutils.logger import get_logger


logger = get_logger(__name__)


try:
    from revitutils._project import doc, uidoc, all_docs, project, curview

    from revitutils._selectutils import CurrentElementSelection
    selection = CurrentElementSelection(doc, uidoc)

    from revitutils._transaction import Action, ActionGroup

except Exception as ru_setup_err:
    logger.error('Error setting up revitutils | {}'.format(ru_setup_err))
