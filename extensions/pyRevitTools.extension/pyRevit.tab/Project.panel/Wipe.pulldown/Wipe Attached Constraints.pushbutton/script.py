"""Deletes all attached_constraints attached to the selected object."""
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script


logger = script.get_logger()


constraints_cl = DB.FilteredElementCollector(revit.doc)\
                   .OfCategory(DB.BuiltInCategory.OST_Constraints)\
                   .WhereElementIsNotElementType()

attached_constraints = set()


def list_attached_constraints(src_element, constraints):
    print('This element id: {}'.format(src_element.Id))
    for constraint in constraints:
        refs = [(x.ElementId, x) for x in constraint.References]
        elids = [x[0] for x in refs]
        if src_element.Id in elids:
            attached_constraints.add(constraint)
            print("Removing Constraint of Type: {:28} "
                  "# of References: {:24} "
                  "Constraint id: {}"
                  .format(constraint.GetType().Name,
                          str(constraint.References.Size),
                          constraint.Id))

            for t in refs:
                ref = t[1]
                elid = t[0]
                if elid == src_element.Id:
                    elid = str(elid) + ' (this)'

                elmnt = revit.doc.GetElement(ref.ElementId)
                print("\t{:35} Linked Object Category: {:20} Id: {}"
                      .format(ref.ElementReferenceType.ToString(),
                              elmnt.Category.Name,
                              elid))


# collect and report the attached_constraints
for selected_element in revit.get_selection():
    list_attached_constraints(selected_element, constraints_cl)

# if any, wipe
if attached_constraints:
    with revit.Transaction('Remove associated attached_constraints'):
        for attached_constraint in attached_constraints:
            try:
                revit.doc.Delete(attached_constraint.Id)
                print('Constraint Removed')
            except Exception as dex:
                logger.error(
                    "Failed deleting constraint: %s", attached_constraint)
                continue
else:
    forms.alert("No attached_constraints found.")
