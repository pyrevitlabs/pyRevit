from pyrevit import script, revit


output = script.get_output()
selection = revit.get_selection()


if len(selection.element_ids) > 0:
    output.set_width(300)

    if len(selection.element_ids) < 2000:
        print("{}".format(output.linkify(selection.element_ids, title="All Elements")))

    elements = sorted(
        (
            (revit.query.get_name(element), element)
            for element in selection.elements
        ),
        key=lambda x: x[0].lower()
    )

    for idx, (name, element) in enumerate(elements, 1):
        print(
            "{}: {} {}".format(
                idx, output.linkify(element.Id), name
            )
        )
