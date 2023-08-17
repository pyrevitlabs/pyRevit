"""ApiDocs API wrapper."""
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
    """Returns a list of application available on apidocs.

    Returns:
        (list[APIDocsApp]): applictations documented on apidocs
    """
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
    """Returns a URI for the given asset.

    Args:
        asset_type (str): Asset type
        asset_id (str): Asset ID
        app_name (str): Application name
        app_version (str): Application version

    Returns:
        (str): URI
    """
    return APIDOCS_LOOKUP_TEMPLATE.format(
        asset_type=asset_type,
        asset_id=asset_id,
        app_name=app_name,
        app_version=app_version,
        )


def make_namespace_uri(namespace,
                       app_name="revit",
                       app_version=str(HOST_APP.version)):
    """Returns the URI of a namespace.

    Args:
        namespace (str): name of the namespace
        app_name (str, optional): name of the application. Defaults to "revit".
        app_version (str, optional): version of the application. Defaults to str(HOST_APP.version).

    Returns:
        (str): URI of the namespace
    """
    return _make_uri(
        asset_type="N",
        asset_id=namespace,
        app_name=app_name,
        app_version=app_version,
        )


def make_type_uri(type_name,
                  app_name="revit",
                  app_version=str(HOST_APP.version)):
    """Returns the URI of a type.

    Args:
        type_name (str): name of the type
        app_name (str, optional): name of the application. Defaults to "revit".
        app_version (str, optional): version of the application. Defaults to str(HOST_APP.version).

    Returns:
        (str): URI of the type
    """
    return _make_uri(
        asset_type="T",
        asset_id=type_name,
        app_name=app_name,
        app_version=app_version,
        )


def make_event_uri(event_name,
                   app_name="revit",
                   app_version=str(HOST_APP.version)):
    """Returns the URI of an event.

    Args:
        event_name (str): name of the event.
        app_name (str): name of the application. Defaults to "revit".
        app_version (str): version of the application.
        

    Returns:
        (str): URI of the event
    """
    return _make_uri(
        asset_type="E",
        asset_id=event_name,
        app_name=app_name,
        app_version=app_version,
        )
