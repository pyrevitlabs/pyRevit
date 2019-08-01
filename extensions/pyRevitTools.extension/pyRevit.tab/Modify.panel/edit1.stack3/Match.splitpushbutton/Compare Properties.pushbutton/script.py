"""Compare instance and type properties between two elements."""
#pylint: disable=import-error,invalid-name,broad-except
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script

__author__ = "{{author}}"

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

# main
source_element = None
with forms.WarningBar(title="Pick source object:"):
    source_element = revit.pick_element()

# grab parameters from source element
if source_element:
    target_element = revit.pick_element(message="Pick target element:")
    compare_props(source_element, target_element)
