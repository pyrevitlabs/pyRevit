"""Event telemetry management."""
#pylint: disable=invalid-name,broad-except
from pyrevit import HOST_APP
from pyrevit.coreutils import logger



mlogger = logger.get_logger(__name__)


# event telemetry configurations are controlled by a binary flag
# flag is assumed to be 16 bytes long (128 bits)
# although both python and C# implementation use flexible integers
# the flags are sorted by the index of EventType enum values
ALL_EVENTS = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF

# flag for a suggested configuration for event telementry
SUGGESTED_EVENTS = 0x1d17e7f7ff59


def register_event_telemetry(handler, flags):
    """Registers application event telemetry handlers based on given flags.

    Args:
        handler (EventTelemetry): event telemetry handler
        flags (int): event flags
    """
    try:
        handler.RegisterEventTelemetry(HOST_APP.uiapp, flags)
    except Exception as ex:
        mlogger.debug(
            "Error registering event telementry with flags: %s | %s",
            str(flags), ex)


def unregister_event_telemetry(handler, flags):
    """Unregisters application event telemetry handlers based on given flags.

    Args:
        handler (EventTelemetry): event telemetry handler
        flags (int): event flags
    """
    try:
        handler.UnRegisterEventTelemetry(HOST_APP.uiapp, flags)
    except Exception as ex:
        mlogger.debug(
            "Error unregistering event telementry with flags: %s | %s",
            str(flags), ex)


def unregister_all_event_telemetries(handler):
    """Unregisters all available application event telemetry handlers."""
    unregister_event_telemetry(handler, ALL_EVENTS)
