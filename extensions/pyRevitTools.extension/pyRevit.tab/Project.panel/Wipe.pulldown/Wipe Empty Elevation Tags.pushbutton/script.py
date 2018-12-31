from pyrevit import revit, DB
from pyrevit import script


__doc__ = 'Genrally if all elevations creates by an elevation tag are '\
          'deleted from the model, the empty elevation tag still remains '\
          'in its location. This script will delete all empty elevation ' \
          'tags from the model.'


logger = script.get_logger()


def removeallemptyelevationmarkers():
    with revit.Transaction('Remove All Elevation Markers'):
        print('REMOVING ELEVATION MARKERS...\n')
        elevmarkers = DB.FilteredElementCollector(revit.doc)\
                        .OfClass(DB.ElevationMarker)\
                        .WhereElementIsNotElementType()\
                        .ToElements()

        for em in elevmarkers:
            if em.CurrentViewCount == 0:
                emtype = revit.doc.GetElement(em.GetTypeId())
                print('ID: {0}\tELEVATION TYPE: {1}'
                      .format(em.Id,
                              revit.query.get_name(emtype)))
                try:
                    revit.doc.Delete(em.Id)
                except Exception as e:
                    logger.error('Error removing marker: {} | {}'
                                 .format(em.Id, e))
                    continue


removeallemptyelevationmarkers()
