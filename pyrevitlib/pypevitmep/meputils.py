# coding: utf8
from Autodesk.Revit.DB import Element, ConnectorManager, ConnectorSet, Connector, XYZ


def get_connector_manager(element):
    # type: (Element) -> ConnectorManager
    """Return element connector manager"""
    try:
        # Return ConnectorManager for pipes, ducts etc…
        return element.ConnectorManager
    except AttributeError:
        pass

    try:
        # Return ConnectorManager for family instances etc…
        return element.MEPModel.ConnectorManager
    except AttributeError:
        raise AttributeError("Cannot find connector manager in given element")


def get_connector_closest_to(connectors, xyz):
    # type: (ConnectorSet, XYZ) -> Connector
    """Get connector from connector set or any iterable closest to an XYZ point"""
    min_distance = float("inf")
    closest_connector = None
    for connector in connectors:
        distance = connector.Origin.DistanceTo(xyz)
        if distance < min_distance:
            min_distance = distance
            closest_connector = connector
    return closest_connector


