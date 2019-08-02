"""Event telemetry management."""
#pylint: disable=invalid-name
from pyrevit import HOST_APP
from pyrevit.coreutils.loadertypes import EventTelemetry


# event telemetry configurations are controlled by a binary flag
# flag is assumed to be 16 bytes long (128 bits)
# although both python and C# implementation use flexible integers
# the flags are sorted by the index of EventType enum values
ALL_EVENTS = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF


def register_event_telemetry(flags):
    """Registers application event telemetry handlers based on given flags.

    Args:
        flags (int): event flags
    """
    EventTelemetry.RegisterEventTelemetry(HOST_APP.uiapp, flags)


def unregister_event_telemetry(flags):
    """Unregisters application event telemetry handlers based on given flags.

    Args:
        flags (int): event flags
    """
    EventTelemetry.UnRegisterEventTelemetry(HOST_APP.uiapp, flags)


def unregister_all_event_telemetries():
    """Unregisters all available application event telemetry handlers."""
    unregister_event_telemetry(ALL_EVENTS)
