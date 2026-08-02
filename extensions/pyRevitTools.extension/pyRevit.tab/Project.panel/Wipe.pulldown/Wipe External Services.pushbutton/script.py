# -*- coding: utf-8 -*-
from pyrevit import script, forms, revit
from pyrevit.api import ExternalService as es

logger = script.get_logger()

# Short key -> BuiltInExternalServices property name, used for both
# resolving the service and labeling servers in the combined list.
SERVICE_DEFS = [
    ("DirectContext3D", "DirectContext3DService"),
    ("TemporaryGraphics", "TemporaryGraphicsHandlerService"),
]


class ServerOption(object):
    def __init__(self, label, service_key, service, server_id):
        self.label = label
        self.service_key = service_key
        self.service = service
        self.server_id = server_id

    def __str__(self):
        return self.label


def get_service(prop_name):
    """Resolve an ExternalService instance from a BuiltInExternalServices property name."""
    try:
        service_id = getattr(es.ExternalServices.BuiltInExternalServices, prop_name)
        return es.ExternalServiceRegistry.GetService(service_id)
    except Exception as ex:
        logger.exception("Failed resolving service " + prop_name + " : " + str(ex))
        return None


def collect_options(service_key, service):
    """Build ServerOption entries for all active servers on a given service."""
    options = []
    try:
        active_ids = list(service.GetActiveServerIds())
    except Exception as ex:
        logger.exception("Failed reading active server ids for " + service_key + " : " + str(ex))
        return options

    for sid in active_ids:
        try:
            server = service.GetServer(sid)
            if server:
                try:
                    name = server.GetName()
                except Exception:
                    name = "Unnamed Server"
                try:
                    desc = server.GetDescription()
                except Exception:
                    desc = "No Desc"
            else:
                name = "Unknown Server"
                desc = "No Desc"
            label = "[" + service_key + "]  " + name + "  |  " + desc + "  |  " + str(sid)
            options.append(ServerOption(label, service_key, service, sid))
        except Exception as ex:
            logger.exception("Failed reading server info " + str(sid) + " : " + str(ex))
    return options


def main():
    """Let user select which external service server(s) to remove.

    Covers DirectContext3DService and TemporaryGraphicsHandlerService in a
    single combined list, so both can be cleared out in one pass when
    third-party plugins leave misbehaving registrations behind.
    """
    all_options = []

    for service_key, prop_name in SERVICE_DEFS:
        service = get_service(prop_name)
        if not service:
            print("Service unavailable: " + service_key)
            continue
        all_options.extend(collect_options(service_key, service))

    if not all_options:
        print("No active/removable servers found on any service.")
        return

    selection = forms.SelectFromList.show(
        all_options,
        title="Select External Service Server(s) to Remove",
        multiselect=True,
        button_name="Remove Selected Servers",
    )

    if not selection:
        print("Nothing selected.")
        return

    removed = 0
    skipped = 0
    for opt in selection:
        service = opt.service
        sid = opt.server_id
        try:
            if service.IsRegisteredServerId(sid):
                service.RemoveServer(sid)
                removed += 1
                print("Removed: " + opt.label)
            else:
                skipped += 1
        except Exception as ex:
            logger.exception("Failed removing " + str(sid) + " : " + str(ex))
            skipped += 1

    revit.uidoc.RefreshActiveView()
    print("Done. Removed: " + str(removed) + " | Skipped: " + str(skipped))


if __name__ == "__main__":
    main()
