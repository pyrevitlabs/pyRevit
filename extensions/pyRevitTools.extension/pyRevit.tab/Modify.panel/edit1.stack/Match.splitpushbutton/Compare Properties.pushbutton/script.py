"""Compare instance and type properties between two elements."""
# pylint: disable=import-error,invalid-name,broad-except
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script


logger = script.get_logger()
output = script.get_output()


EXCLUDE_PARAMS = set([
    'Family and Type',
    'Type Id',
])


class PropPair(object):
    def __init__(self, leftp, rightp):
        self.leftp = leftp
        self.rightp = rightp

    def __repr__(self):
        return '<{} {} % {}>'.format(
            self.__class__.__name__,
            self.leftp_name,
            self.rightp_name
            )

    @property
    def leftp_name(self):
        return self.leftp.Definition.Name

    @property
    def rightp_name(self):
        return self.rightp.Definition.Name

    def compare(self):
        leftv = revit.query.get_param_value(self.leftp)
        rightv = revit.query.get_param_value(self.rightp)
        if leftv == rightv:
            print(":white_heavy_check_mark: {} == {}"
                  .format(self.leftp_name, self.rightp_name))
        else:
            print(":cross_mark: {} != {}"
                  .format(self.leftp_name, self.rightp_name))


def grab_props(src_element):
    return [x for x in src_element.Parameters
            if x.Definition.Name not in EXCLUDE_PARAMS]


def compare_view_filters(view1, view2):
    output.print_md("### View Filters")

    filters1 = set(view1.GetFilters())
    filters2 = set(view2.GetFilters())

    filter_names1 = {view1.Document.GetElement(fid).Name: fid for fid in filters1}
    filter_names2 = {view2.Document.GetElement(fid).Name: fid for fid in filters2}

    shared_filters = set(filter_names1.keys()).intersection(set(filter_names2.keys()))
    only_in_1 = set(filter_names1.keys()) - set(filter_names2.keys())
    only_in_2 = set(filter_names2.keys()) - set(filter_names1.keys())

    if only_in_1 or only_in_2:
        rows = [[n, ""] for n in sorted(only_in_1)]
        rows.extend([["", n] for n in sorted(only_in_2)])
        output.print_table(
            rows,
            columns=["Only in Source View", "Only in Target View"],
            title="Different Filter Assignments",
        )

    for fname in sorted(shared_filters):
        fid1 = filter_names1[fname]
        fid2 = filter_names2[fname]

        ov1 = view1.GetFilterOverrides(fid1)
        ov2 = view2.GetFilterOverrides(fid2)

        differences = []

        # Compare properties of OverrideGraphicSettings
        ov_attrs = [
            # Colors
            "ProjectionLineColor",
            "SurfaceForegroundPatternColor",
            "SurfaceBackgroundPatternColor",
            "CutLineColor",
            "CutForegroundPatternColor",
            "CutBackgroundPatternColor",

            # Pattern IDs
            "SurfaceForegroundPatternId",
            "SurfaceBackgroundPatternId",
            "CutForegroundPatternId",
            "CutBackgroundPatternId",
            "ProjectionLinePatternId",
            "CutLinePatternId",

            # Line weights
            "ProjectionLineWeight",
            "CutLineWeight",

            # Visibility flags
            "IsSurfaceForegroundPatternVisible",
            "IsSurfaceBackgroundPatternVisible",
            "IsCutForegroundPatternVisible",
            "IsCutBackgroundPatternVisible",

            # Other
            "Transparency",
            "Halftone",
        ]

        for attr in ov_attrs:
            val1 = getattr(ov1, attr)
            val2 = getattr(ov2, attr)

            if isinstance(val1, DB.Color):
                if val1.IsValid and val2.IsValid:
                    if val1.Red != val2.Red or val1.Green != val2.Green or val1.Blue != val2.Blue:
                        differences.append(attr)
                elif val1.IsValid != val2.IsValid:
                    differences.append(attr)
            else:
                if val1 != val2:
                    differences.append(attr)

        # More general stuff
        if view1.GetIsFilterEnabled(fid1) != view2.GetIsFilterEnabled(fid2):
            differences.append("Enabled Status")

        if view1.GetFilterVisibility(fid1) != view2.GetFilterVisibility(fid2):
            differences.append("Visibility Status")

        if differences:
            output.print_md(
                ":warning: **Filter '{}' has different overrides:** {}"
                .format(fname, ", ".join(differences)))
        else:
            output.print_md(
                ":white_heavy_check_mark: Filter '{}' overrides match.".format(fname))


def compare_props(src_element, tgt_element):
    output.print_md("### Instance Properties")
    src_type = revit.query.get_type(src_element)
    tgt_type = revit.query.get_type(tgt_element)

    src_props = set([x.Definition.Name for x in grab_props(src_element)])
    tgt_props = set([x.Definition.Name for x in grab_props(tgt_element)])

    # find shared propeties
    shared_props = src_props.intersection(tgt_props)
    for sprop in sorted(shared_props):
        proppair = PropPair(
            src_element.LookupParameter(sprop),
            tgt_element.LookupParameter(sprop)
            )
        proppair.compare()

    # list unique properties
    src_unique = src_props.difference(tgt_props)
    tgt_unique = tgt_props.difference(src_props)
    unique_props = [[x, ''] for x in src_unique]
    unique_props.extend([['', x] for x in tgt_unique])
    if unique_props:
        output.print_table(
            unique_props,
            columns=['Source Element', 'Target Element'],
            title='Unique Properties'
            )

    # list type properties
    if src_type and tgt_type:
        output.print_md("### Type Properties")
        src_tprops = set([x.Definition.Name for x in grab_props(src_type)])
        tgt_tprops = set([x.Definition.Name for x in grab_props(tgt_type)])

        shared_tprops = src_tprops.intersection(tgt_tprops)
        for stprop in sorted(shared_tprops):
            tproppair = PropPair(
                src_type.LookupParameter(stprop),
                tgt_type.LookupParameter(stprop)
                )
            tproppair.compare()

        # list unique properties
        src_tunique = src_tprops.difference(tgt_tprops)
        tgt_tunique = tgt_tprops.difference(src_tprops)
        unique_tprops = [[x, ''] for x in src_tunique]
        unique_tprops.extend([['', x] for x in tgt_tunique])
        if unique_tprops:
            output.print_table(
                unique_tprops,
                columns=['Source Element Type', 'Target Element Type'],
                title='Unique Type Properties'
                )

    # If both are views, compare filters
    if isinstance(src_element, DB.View) and isinstance(tgt_element, DB.View):
        compare_view_filters(src_element, tgt_element)


# main
# try use selected elements
selected_elements = revit.get_selection().elements
if len(selected_elements) == 1 and forms.alert(
    "Use selected %s?"
    % ("view" if isinstance(selected_elements[0], DB.View) else "element"),
    yes=True,
    no=True,
):
    source_element = selected_elements[0]
    target_type = "Views" if isinstance(source_element, DB.View)\
        else "Elements"
else:
    source_element = None
    # ask for type of elements to match
    # some are not selectable in graphical views
    target_type = \
        forms.CommandSwitchWindow.show(
            ["Elements", "Views", "View Templates"],
            message="Pick type of targets:")

    # determine source element
    if target_type == "Elements":
        with forms.WarningBar(title="Pick source element:"):
            source_element = revit.pick_element(message="Pick source element:")
    elif target_type == "Views":
        source_element = \
            forms.select_views(title="Select Source View", multiple=False)
    elif target_type == "View Templates":
        source_element = \
            forms.select_viewtemplates(title="Select Source View Template", multiple=False)

# grab parameters from source element
if source_element:
    target_element = None

    def exclude_source(el):
        return el.Id != source_element.Id

    if target_type == "Elements":
        with forms.WarningBar(title="Pick target object:"):
            target_element = revit.pick_element(message="Pick target element:")
    elif target_type == "Views":
        target_element = \
            forms.select_views(title="Select Target View", multiple=False, filterfunc=exclude_source)
    elif target_type == "View Templates":
        target_element = \
            forms.select_viewtemplates(title="Select Target View Template", multiple=False, filterfunc=exclude_source)
    if target_element:
        compare_props(source_element, target_element)
