"""Provides options for overriding values on selected dimensions."""

from collections import OrderedDict

from pyrevit.framework import List
from pyrevit import revit, DB, UI
from pyrevit import forms


__authors__ = ['{{author}}', 'SILMAN']
__context__ = 'OST_Dimensions'


def grab_dims():
    dims = []
    for el in revit.get_selection():
        if isinstance(el, DB.Dimension):
            if len(list(el.Segments)) > 0:
                for seg in el.Segments:
                    dims.append(seg)
            else:
                dims.append(el)
    return dims


def set_dim_overrides(dims, txn_name='Dimension Overrides',
                      value=None,
                      above=None, below=None,
                      prefix=None, suffix=None):
    with revit.Transaction(txn_name):
        for seg in dims:
            if value is not None:
                seg.ValueOverride = value
            if above is not None:
                seg.Above = above
            if below is not None:
                seg.Below = below
            if prefix is not None:
                seg.Prefix = prefix
            if suffix is not None:
                seg.Suffix = suffix


def bake_dim_value():
    with revit.Transaction('Overrride dims value'):
        for seg in grab_dims():
            seg.ValueOverride = u'\u200e' + seg.ValueString


def clear_overrides():
    set_dim_overrides(grab_dims(), txn_name='Reset Dimension Overrides',
                      value='', above='', below='', prefix='', suffix='')


def set_to_eq():
    set_dim_overrides(grab_dims(), txn_name='EQ Dims',
                      value='EQ')


def set_to_vfrmfr():
    set_dim_overrides(grab_dims(), txn_name='RO VIF Dims',
                      below='VERIFY W/ MFR', suffix='R.O.')


def set_to_question():
    set_dim_overrides(grab_dims(), txn_name='(?) Dims',
                      suffix='(?)')


def set_to_zero():
    set_dim_overrides(grab_dims(), txn_name='Zero Dims',
                      value='0"', above='', below='', prefix='', suffix='')


def set_to_classb_lapsplice():
    set_dim_overrides(grab_dims(),
                      txn_name='Dimension "Class B Lap Splice"',
                      value='CLASS B TENSION',
                      above='', below='LAP SPLICE', prefix='', suffix='')


def set_to_tension_dev_length():
    set_dim_overrides(grab_dims(),
                      txn_name='Dimension "Tension Development Length"',
                      value='DEVELOPMENT',
                      above='TENSION', below='LENGTH', prefix='', suffix='')


def add_plusminus_prefix():
    set_dim_overrides(grab_dims(), txn_name='PlusMinus Dims',
                      prefix=u'\xb1')


def add_plusminus_suffix():
    set_dim_overrides(grab_dims(), txn_name='PlusMinus Dims',
                      suffix=u'\xb1')


def set_to_vif_below():
    set_dim_overrides(grab_dims(), txn_name='VIF Dims',
                      below='VIF')


def set_to_vif_suffix():
    set_dim_overrides(grab_dims(), txn_name='VIF Dims',
                      suffix='VIF')


def set_to_typ_below():
    set_dim_overrides(grab_dims(), txn_name='TYP Dims',
                      below='TYP')


def set_to_typ_suffix():
    set_dim_overrides(grab_dims(), txn_name='TYP Dims',
                      suffix='TYP')


def set_to_min_below():
    set_dim_overrides(grab_dims(), txn_name='MIN Dims',
                      below='MIN')


def set_to_min_suffix():
    set_dim_overrides(grab_dims(), txn_name='MIN Dims',
                      suffix='MIN')


def set_to_max_below():
    set_dim_overrides(grab_dims(), txn_name='MAX Dims',
                      below='MAX')


def set_to_max_suffix():
    set_dim_overrides(grab_dims(), txn_name='MAX Dims',
                      suffix='MAX')


def set_to_clr_below():
    set_dim_overrides(grab_dims(), txn_name='CLR Dims',
                      below='CLR')


def set_to_clr_suffix():
    set_dim_overrides(grab_dims(), txn_name='CLR Dims',
                      suffix='CLR')


def set_to_uno_below():
    set_dim_overrides(grab_dims(), txn_name='UNO Dims',
                      below='UNO')


def set_to_uno_suffix():
    set_dim_overrides(grab_dims(), txn_name='UNO Dims',
                      suffix='UNO')


def set_to_pd():
    set_dim_overrides(grab_dims(), txn_name='PD Dims',
                      suffix='P.D.')


def set_to_pd_beow():
    set_dim_overrides(grab_dims(), txn_name='PD Dims',
                      below='P.D.')


def set_to_ro():
    set_dim_overrides(grab_dims(), txn_name='RO Dims',
                      suffix='R.O.')


def set_to_ro_below():
    set_dim_overrides(grab_dims(), txn_name='RO Dims',
                      below='R.O.')


options = OrderedDict()
options['Reset Dimension Overrides'] = clear_overrides
options['Bake Dimension Value'] = bake_dim_value
options['Equal (EQ)'] = set_to_eq
options['Zero Inch (0")'] = set_to_zero
options['Class B Lap Splice'] = set_to_classb_lapsplice
options['Tension Development Length'] = set_to_tension_dev_length
options['Prefix: Plus/Minus'] = add_plusminus_prefix
options['Suffix: Plus/Minus'] = add_plusminus_suffix
options['Suffix: R.O. Below: VIF MFR'] = set_to_vfrmfr
options['Suffix: VIF'] = set_to_vif_suffix
options['Below: VIF'] = set_to_vif_below
options['Suffix: (?)'] = set_to_question
options['Suffix: P.D.'] = set_to_pd
options['Below: P.D.'] = set_to_pd_beow
options['Suffix: R.O.'] = set_to_ro
options['Below: R.O.'] = set_to_ro_below
options['Below: TYP'] = set_to_typ_below
options['Suffix: TYP'] = set_to_typ_suffix
options['Below: MIN'] = set_to_min_below
options['Suffix: MIN'] = set_to_min_suffix
options['Below: MAX'] = set_to_max_below
options['Suffix: MAX'] = set_to_max_suffix
options['Below: CLR'] = set_to_clr_below
options['Suffix: CLR'] = set_to_clr_suffix
options['Below: UNO'] = set_to_uno_below
options['Suffix: UNO'] = set_to_uno_suffix


selected_switch = \
    forms.CommandSwitchWindow.show(options.keys(),
                                   message='Pick override option:')

if selected_switch:
    options[selected_switch]()
