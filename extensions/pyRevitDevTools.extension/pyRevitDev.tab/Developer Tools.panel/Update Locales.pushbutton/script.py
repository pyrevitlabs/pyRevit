"""Updates tool locales from the given files."""
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
import os.path as op

from pyrevit.coreutils import yaml
from pyrevit.coreutils import applocales
from pyrevit.extensions import extensionmgr
from pyrevit import forms
from pyrevit import script


__title__ = 'Update\nLocales'
__context__ = 'zero-doc'

logger = script.get_logger()
output = script.get_output()


DEFAULT_LOCAL_KEY = applocales.DEFAULT_LOCALE.locale_codes[0]
DEFAULT_BUNDLE_FILENAME = 'bundle.yaml'


def localize_property(mdata, prop_name, default_key):
    value = mdata.get(prop_name, {})
    if isinstance(value, str):
        mdata[prop_name] = {default_key: value}
    else:
        mdata[prop_name] = value
    return mdata


def get_prop_from_comp(prop_name, bcomp):
    if prop_name == 'title':
        return getattr(bcomp, 'ui_title')


def update_bundle_property(bdata, bcomp, prop_name):
    # bdata is bundle locale data
    # bcomp is bundle component
    locale_data = bdata.get(bcomp.name, [])
    if locale_data:
        # ensure there is bundle metadata file
        meta_file = bcomp.meta_file
        if not meta_file:
            print('creating bundle file for \"%s\"' % bcomp)
            meta_file = op.join(bcomp.directory, DEFAULT_BUNDLE_FILENAME)
            yaml.dump_dict({
                prop_name: {
                    DEFAULT_LOCAL_KEY: get_prop_from_comp(prop_name, bcomp)
                }}, meta_file)

        meta = yaml.load_as_dict(meta_file)
        meta = localize_property(meta, prop_name, DEFAULT_LOCAL_KEY)
        print('updating bundle locale data for \"%s\"' % bcomp)
        for locale_code, locale_str in locale_data.items():
            if locale_str:
                if locale_code in meta[prop_name]:
                    print('updating existing locale \"%s\" -> \"%s\"'
                          % (meta[prop_name][locale_code], locale_str))
                else:
                    print('adding locale \"%s\" -> \"%s\"'
                          % (locale_code, locale_str))
                meta[prop_name][locale_code] = locale_str

        yaml.dump_dict(meta, meta_file)

    if bcomp.is_container:
        for child_comp in bcomp:
            update_bundle_property(bdata, child_comp, prop_name)


# 1) ==========================================================================
# update title locales in bundle files from input csv file
csv_file = forms.pick_file(files_filter='CSV Title Locale File |*.csv')
if not csv_file:
    script.exit()

# load, parse and prepare the bundle local data
title_locales_data = {}
csv_data = script.load_csv(csv_file)
# translate language names in csv header to language codes
locale_code_fields = []
for locale_name in csv_data[0][1:]: # grabs first csv line and columns 1:
    logger.debug('finding locale codes for \"%s\"', locale_name)
    applocale = applocales.get_applocale_by_lang_name(locale_name)
    if applocale:
        locale_code_fields.append(applocale.locale_codes[0])
    else:
        logger.error('can not determine langauge code for \"%s\"', locale_name)
        script.exit()

for csv_record in csv_data[1:]:
    name = csv_record[0]
    locales = {}
    for field_idx, field_value in enumerate(csv_record[1:]):
        locales[locale_code_fields[field_idx]] = field_value
    title_locales_data[name] = locales

if title_locales_data:
    selected_extensions = forms.SelectFromList.show(
        extensionmgr.get_installed_ui_extensions(),
        title='Select Extention',
        multiselect=True
    )
    for ui_ext in selected_extensions:
        print('updating bundle locale data for ext \"%s\"' % ui_ext.name)
        update_bundle_property(title_locales_data, ui_ext, 'title')

print('done...')
