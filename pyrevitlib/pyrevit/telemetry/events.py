"""Event telemetry management."""
#pylint: disable=invalid-name,broad-except
from pyrevit import HOST_APP
from pyrevit.coreutils import logger
from pyrevit.coreutils.loadertypes import EventTelemetry


mlogger = logger.get_logger(__name__)


# event telemetry configurations are controlled by a binary flag
# flag is assumed to be 16 bytes long (128 bits)
# although both python and C# implementation use flexible integers
# the flags are sorted by the index of EventType enum values
ALL_EVENTS = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF


EVENT_TELEMETRY = EventTelemetry()


def get_event_telemetry_registries():
    return EVENT_TELEMETRY


def get_all_event_telemetry_registries():
    return [EVENT_TELEMETRY]


def register_event_telemetry(flags, event_telemetry=None):
    """Registers application event telemetry handlers based on given flags.

    Args:
        flags (int): event flags
    """
    try:
        if not event_telemetry:
            event_telemetry = get_event_telemetry_registries()
        event_telemetry.RegisterEventTelemetry(HOST_APP.uiapp, flags)
    except Exception as ex:
        mlogger.debug(
            "Error registering event telementry with flags: %s | %s",
            str(flags), ex)


def unregister_event_telemetry(flags, event_telemetry=None):
    """Unregisters application event telemetry handlers based on given flags.

    Args:
        flags (int): event flags
    """
    try:
        if not event_telemetry:
            event_telemetry = get_event_telemetry_registries()
        event_telemetry.UnRegisterEventTelemetry(HOST_APP.uiapp, flags)
    except Exception as ex:
        mlogger.debug(
            "Error unregistering event telementry with flags: %s | %s",
            str(flags), ex)


def unregister_all_event_telemetries():
    """Unregisters all available application event telemetry handlers."""
    for event_telemetry in get_all_event_telemetry_registries():
        unregister_event_telemetry(ALL_EVENTS, event_telemetry=event_telemetry)
