"""ApiDocs API wrapper"""
import json
from collections import namedtuple

from pyrevit import HOST_APP
from pyrevit import coreutils


APIDOCS_INDEX = r'https://static.apidocs.co/apidocs_index.json'
APIDOCS_LOOKUP_TEMPLATE = \
    'https://api.apidocs.co/resolve/{app_name}/{app_version}/'\
        '?asset_id={asset_type}:{asset_id}'


APIDocsApp = namedtuple('APIDocsApp', ['apptitle', 'appslug', 'versionslug'])


def get_apps():
    apidoc_apps = []
    for app in json.loads(coreutils.read_url(APIDOCS_INDEX)):
        apidoc_apps.append(
            APIDocsApp(
                apptitle=app['apptitle'],
                appslug=app['appslug'],
                versionslug=app['versionslug']
            )
        )
    return apidoc_apps


def _make_uri(asset_type, asset_id, app_name, app_version):
    return APIDOCS_LOOKUP_TEMPLATE.format(
        asset_type=asset_type,
        asset_id=asset_id,
        app_name=app_name,
        app_version=app_version,
        )


def make_namespace_uri(namespace,
                       app_name="revit",
                       app_version=str(HOST_APP.version)):
    return _make_uri(
        asset_type="N",
        asset_id=namespace,
        app_name=app_name,
        app_version=app_version,
        )


def make_type_uri(type_name,
                  app_name="revit",
                  app_version=str(HOST_APP.version)):
    return _make_uri(
        asset_type="T",
        asset_id=type_name,
        app_name=app_name,
        app_version=app_version,
        )


def make_event_uri(event_name,
                   app_name="revit",
                   app_version=str(HOST_APP.version)):
    return _make_uri(
        asset_type="E",
        asset_id=event_name,
        app_name=app_name,
        app_version=app_version,
        )
