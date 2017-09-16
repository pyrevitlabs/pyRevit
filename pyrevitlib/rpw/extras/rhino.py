"""
Rhino - Rhino3dmIO

Rhino3dmIO is a subset of RhinoCommon and it gives you access to openNurbs,
allowing you to, amongst other things, read and write 3dm files.

Usage:

    >>> from rpw.extras.rhino import Rhino as rc
    >>> pt1 = rc.Geometry.Point3d(0,0,0)
    >>> pt2 = rc.Geometry.Point3d(10,10,0)
    >>> line1 = rc.Geometry.Line(pt1, pt2)
    >>> line1.Length
    14.142135623730951
    >>>
    >>> pt1 = rc.Geometry.Point3d(10,0,0)
    >>> pt2 = rc.Geometry.Point3d(0,10,0)
    >>> line2 = rc.Geometry.Line(pt1, pt2)
    >>>
    >>> rc.Geometry.Intersect.Intersection.LineLine(line1, line2)
    (True, 0.5, 0.5)
    >>>
    >>> file3dm = f = rc.FileIO.File3dm()
    >>> file3md_options = rc.FileIO.File3dmWriteOptions()
    >>> file3dm.Objects.AddLine(line1)
    >>> filepath = 'c:/folder/test.3dm'
    >>> file3dm.Write(filepath, file3md_options)

.. note::
    Although the openNURBS toolkit appears to be a full-featured geometry
    library, it is not.     The toolkit does not include a
    number of important features, including:

    *   Closest point calculations
    *   Intersection calculations
    *   Surface tessellation (meshing)
    *   Interpolation
    *   Booleans
    *   Area and mass property calculations
    *   Other miscellaneous geometry calculations

    [ Note from McNeel's website on openNURBS ]


More Information about openNURBES in the links below:
    * `Github Repo <https://github.com/mcneel/rhinocommon/tree/rhino3dmio>`_
    * `RhinoCommon API <http://developer.rhino3d.com/api/>`_
    * `openNURBS <http://developer.rhino3d.com/guides/opennurbs/what-is-opennurbs/>`_

"""
from rpw.utils.dotnet import clr
clr.AddReference('Rhino3dmIO')

import Rhino
