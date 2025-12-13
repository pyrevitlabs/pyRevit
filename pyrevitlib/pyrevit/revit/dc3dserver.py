# -*- coding: utf-8 -*-
"""DirectContext3DServer wrapper and utilities."""

from collections import namedtuple
import traceback

from pyrevit import DB
from pyrevit.api import ExternalService as es
from pyrevit.api import DirectContext3D as dc3d
from pyrevit.coreutils import Guid
from pyrevit.interop import stl

Edge = namedtuple("Edge", ["a", "b", "color"])
Triangle = namedtuple("Triangle", ["a", "b", "c", "normal", "color"])


class Mesh(object):
    """Geometry container class to generate DirectContext3DServer buffers."""

    def __init__(self, edges, triangles):
        if not isinstance(edges, list):
            raise ValueError("List of Edges should be provided")
        self.edges = edges
        if not isinstance(triangles, list):
            raise ValueError("List of Triangles should be provided")
        self.triangles = triangles

        vertices = []
        for edge in self.edges:
            vertices.extend([edge.a, edge.b])
        for triangle in self.triangles:
            vertices.extend([triangle.a, triangle.b, triangle.c])
        self.vertices = vertices

    @staticmethod
    def calculate_triangle_normal(a, b, c):
        return (c - a).CrossProduct(b - a)

    @classmethod
    def from_solid(cls, doc, solid):
        try:
            if not isinstance(solid, DB.Solid):
                raise TypeError("Provided object has to be a Revit Solid!")
            triangles = []
            edges = []
            for face in solid.Faces:
                if face.MaterialElementId == DB.ElementId.InvalidElementId:
                    # make it white if material is <By Category>
                    color = DB.ColorWithTransparency(255, 255, 255, 0)
                else:
                    material = doc.GetElement(face.MaterialElementId)
                    color = DB.ColorWithTransparency(
                        material.Color.Red,
                        material.Color.Green,
                        material.Color.Blue,
                        int(material.Transparency / 100 * 255),
                    )
                face_mesh = face.Triangulate()
                triangle_count = face_mesh.NumTriangles
                for idx in range(triangle_count):
                    mesh_triangle = face_mesh.get_Triangle(idx)
                    if (
                        face_mesh.DistributionOfNormals
                        == DB.DistributionOfNormals.OnePerFace
                    ):
                        normal = face_mesh.GetNormal(0)
                    elif (
                        face_mesh.DistributionOfNormals
                        == DB.DistributionOfNormals.OnEachFacet
                    ):
                        normal = face_mesh.GetNormal(idx)
                    elif (
                        face_mesh.DistributionOfNormals
                        == DB.DistributionOfNormals.AtEachPoint
                    ):
                        normal = (
                            face_mesh.GetNormal(mesh_triangle.get_Index(0))
                            + face_mesh.GetNormal(mesh_triangle.get_Index(1))
                            + face_mesh.GetNormal(mesh_triangle.get_Index(2))
                        ).Normalize()
                    triangles.append(
                        Triangle(
                            mesh_triangle.get_Vertex(0),
                            mesh_triangle.get_Vertex(1),
                            mesh_triangle.get_Vertex(2),
                            normal,
                            color,
                        )
                    )
            for edge in solid.Edges:
                pts = edge.Tessellate()
                for idx in range(len(pts) - 1):
                    edges.append(
                        Edge(
                            pts[idx], pts[idx + 1], DB.ColorWithTransparency(0, 0, 0, 0)
                        )
                    )
            return cls(edges, triangles)
        except:
            print(traceback.format_exc())

    @classmethod
    def from_boundingbox(cls, bounding_box, color, black_edges=True):
        """Generates a Mesh object from the input BoundigBoxXYZ.

        Args:
            bounding_box (DB.BoundingBoxXYZ): The source object.
            color (DB.ColorWithTransparency): The desired color.
            black_edges (bool, optional):
                To have black edges instead of the provided color.
                Defaults to True.

        Returns:
            (Mesh): The resulting Mesh
        """
        try:
            # get all untransformed vertices of the boundingbox
            vertices = [
                [
                    DB.XYZ(bounding_box.Min.X, bounding_box.Min.Y, bounding_box.Min.Z),
                    DB.XYZ(bounding_box.Min.X, bounding_box.Max.Y, bounding_box.Min.Z),
                    DB.XYZ(bounding_box.Max.X, bounding_box.Max.Y, bounding_box.Min.Z),
                    DB.XYZ(bounding_box.Max.X, bounding_box.Min.Y, bounding_box.Min.Z),
                ],
                [
                    DB.XYZ(bounding_box.Min.X, bounding_box.Min.Y, bounding_box.Max.Z),
                    DB.XYZ(bounding_box.Min.X, bounding_box.Max.Y, bounding_box.Max.Z),
                    DB.XYZ(bounding_box.Max.X, bounding_box.Max.Y, bounding_box.Max.Z),
                    DB.XYZ(bounding_box.Max.X, bounding_box.Min.Y, bounding_box.Max.Z),
                ],
            ]
            # apply it's transform if it has any
            vertices = [
                [bounding_box.Transform.OfPoint(pt) for pt in vertices[idx]]
                for idx in range(len(vertices))
            ]

            if black_edges:
                edge_color = DB.ColorWithTransparency(0, 0, 0, 0)
            else:
                edge_color = color

            edges = []
            # creating top and bottom face triangles
            triangles = [
                Triangle(
                    vertices[0][0],
                    vertices[0][2],
                    vertices[0][1],
                    Mesh.calculate_triangle_normal(
                        vertices[0][0], vertices[0][2], vertices[0][1]
                    ),
                    color,
                ),
                Triangle(
                    vertices[0][0],
                    vertices[0][3],
                    vertices[0][2],
                    Mesh.calculate_triangle_normal(
                        vertices[0][0], vertices[0][3], vertices[0][2]
                    ),
                    color,
                ),
                Triangle(
                    vertices[1][0],
                    vertices[1][1],
                    vertices[1][2],
                    Mesh.calculate_triangle_normal(
                        vertices[1][0], vertices[1][1], vertices[1][2]
                    ),
                    color,
                ),
                Triangle(
                    vertices[1][0],
                    vertices[1][2],
                    vertices[1][3],
                    Mesh.calculate_triangle_normal(
                        vertices[1][0], vertices[1][2], vertices[1][3]
                    ),
                    color,
                ),
            ]

            # creating edges and face triangles for the sides
            for idx in range(4):
                edges.extend(
                    [
                        Edge(vertices[0][idx], vertices[1][idx], edge_color),
                        Edge(vertices[0][idx], vertices[0][idx - 1], edge_color),
                        Edge(vertices[1][idx], vertices[1][idx - 1], edge_color),
                    ]
                )
                triangles.extend(
                    [
                        Triangle(
                            vertices[0][idx],
                            vertices[1][idx],
                            vertices[0][idx - 1],
                            Mesh.calculate_triangle_normal(
                                vertices[0][idx], vertices[1][idx], vertices[0][idx - 1]
                            ),
                            color,
                        ),
                        Triangle(
                            vertices[1][idx],
                            vertices[1][idx - 1],
                            vertices[0][idx - 1],
                            Mesh.calculate_triangle_normal(
                                vertices[1][idx],
                                vertices[1][idx - 1],
                                vertices[0][idx - 1],
                            ),
                            color,
                        ),
                    ]
                )

            return cls(edges, triangles)
        except Exception:
            print(traceback.format_exc())

    @classmethod
    def from_stl(cls, stl_filepath, color, transform=None, black_edges=True):
        """Generates a Mesh object from an STL file.

        Args:
            stl_filepath (str): Path to the STL file.
            color (DB.ColorWithTransparency): The desired color.
            transform (DB.Transform, optional):
                Transform to apply to the mesh (for positioning, scaling, rotation).
                Defaults to None (identity transform).
            black_edges (bool, optional):
                To have black edges instead of the provided color.
                Defaults to True.

        Returns:
            (Mesh): The resulting Mesh
        """
        try:
            stl_mesh = stl.load(stl_filepath)

            if not stl_mesh or not stl_mesh.triangles:
                raise ValueError("STL file contains no triangles")

            edges = []
            triangles = []

            if black_edges:
                edge_color = DB.ColorWithTransparency(0, 0, 0, 0)
            else:
                edge_color = color

            for stl_triangle in stl_mesh.triangles:
                v1_tuple = stl_triangle["vertices"][0]
                v2_tuple = stl_triangle["vertices"][1]
                v3_tuple = stl_triangle["vertices"][2]
                n_tuple = stl_triangle["normal"]

                v1 = DB.XYZ(v1_tuple[0], v1_tuple[1], v1_tuple[2])
                v2 = DB.XYZ(v2_tuple[0], v2_tuple[1], v2_tuple[2])
                v3 = DB.XYZ(v3_tuple[0], v3_tuple[1], v3_tuple[2])
                normal = DB.XYZ(n_tuple[0], n_tuple[1], n_tuple[2])

                if transform is not None:
                    v1 = transform.OfPoint(v1)
                    v2 = transform.OfPoint(v2)
                    v3 = transform.OfPoint(v3)
                    normal = transform.OfVector(normal)

                try:
                    normal = normal.Normalize()
                except:
                    normal = cls.calculate_triangle_normal(v1, v2, v3)
                    try:
                        normal = normal.Normalize()
                    except:
                        normal = DB.XYZ(0, 0, 1)

                triangles.append(Triangle(v1, v2, v3, normal, color))

                edges.append(Edge(v1, v2, edge_color))
                edges.append(Edge(v2, v3, edge_color))
                edges.append(Edge(v3, v1, edge_color))

            return cls(edges, triangles)

        except Exception:
            print(traceback.format_exc())
            return None


class Buffer(object):
    """Buffer container for DirectContext3DServer."""

    def __init__(
        self,
        display_style,
        vertex_buffer,
        vertex_count,
        index_buffer,
        index_count,
        vertex_format,
        effect_instance,
        primitive_type,
        start,
        primitive_count,
    ):
        self.display_style = display_style
        self.vertex_buffer = vertex_buffer
        self.vertex_count = vertex_count
        self.index_buffer = index_buffer
        self.index_count = index_count
        self.vertex_format = vertex_format
        self.effect_instance = effect_instance
        self.primitive_type = primitive_type
        self.start = start
        self.primitive_count = primitive_count

    def is_valid(self, display_style):
        return all(
            [
                self.display_style == display_style,
                self.vertex_buffer.IsValid,
                self.index_buffer.IsValid,
                self.vertex_format.IsValid,
                self.effect_instance.IsValid,
            ]
        )

    @classmethod
    def build_edge_buffer(cls, display_style, meshes):
        try:
            if not meshes:
                return
            edges = [edge for edges in [m.edges for m in meshes] for edge in edges]

            format_bits = dc3d.VertexFormatBits.PositionColored
            vertex_format = dc3d.VertexFormat(format_bits)

            effect_instance = dc3d.EffectInstance(format_bits)

            vertex_count = dc3d.VertexPositionColored.GetSizeInFloats() * len(edges) * 2
            vertex_buffer = dc3d.VertexBuffer(vertex_count)

            index_count = dc3d.IndexLine.GetSizeInShortInts() * len(edges)
            index_buffer = dc3d.IndexBuffer(index_count)

            vertex_buffer.Map(vertex_count)
            index_buffer.Map(index_count)
            vertex_stream_pos = vertex_buffer.GetVertexStreamPositionColored()
            index_stream_pos = index_buffer.GetIndexStreamLine()
            for edge_index, edge in enumerate(edges):
                first_idx = edge_index * 2
                vertex_stream_pos.AddVertex(
                    dc3d.VertexPositionColored(edge.a, edge.color)
                )
                vertex_stream_pos.AddVertex(
                    dc3d.VertexPositionColored(edge.b, edge.color)
                )
                index_stream_pos.AddLine(dc3d.IndexLine(first_idx, first_idx + 1))
            vertex_buffer.Unmap()
            index_buffer.Unmap()

            return cls(
                display_style,
                vertex_buffer,
                vertex_count,
                index_buffer,
                index_count,
                vertex_format,
                effect_instance,
                dc3d.PrimitiveType.LineList,
                0,
                len(edges),
            )
        except:
            print(traceback.format_exc())

    @classmethod
    def build_triangle_buffer(cls, display_style, meshes, transparent=False):
        try:
            if not meshes:
                return
            triangles = [
                triangle
                for triangles in [m.triangles for m in meshes]
                for triangle in triangles
                if transparent == (triangle.color.GetTransparency() > 0)
            ]

            if not triangles:
                return

            shaded = any(
                [
                    display_style == DB.DisplayStyle.Shading,
                    display_style == DB.DisplayStyle.ShadingWithEdges,
                ]
            )

            format_bits = dc3d.VertexFormatBits.PositionNormalColored
            vertex_format = dc3d.VertexFormat(format_bits)

            if shaded:
                effect_instance = dc3d.EffectInstance(
                    dc3d.VertexFormatBits.PositionNormalColored
                )
            else:
                effect_instance = dc3d.EffectInstance(
                    dc3d.VertexFormatBits.PositionColored
                )

            vertex_count = (
                dc3d.VertexPositionNormalColored.GetSizeInFloats() * len(triangles) * 3
            )
            vertex_buffer = dc3d.VertexBuffer(vertex_count)

            index_count = dc3d.IndexTriangle.GetSizeInShortInts() * len(triangles)
            index_buffer = dc3d.IndexBuffer(index_count)

            vertex_buffer.Map(vertex_count)
            index_buffer.Map(index_count)
            vertex_stream_pos = vertex_buffer.GetVertexStreamPositionNormalColored()
            index_stream_pos = index_buffer.GetIndexStreamTriangle()
            for triangle_index, triangle in enumerate(triangles):
                if display_style == DB.DisplayStyle.HLR:
                    color = DB.ColorWithTransparency(
                        255, 255, 255, triangle.color.GetTransparency()
                    )
                else:
                    color = triangle.color
                normal = triangle.normal
                first_idx = triangle_index * 3
                vertex_stream_pos.AddVertex(
                    dc3d.VertexPositionNormalColored(triangle.a, normal, color)
                )
                vertex_stream_pos.AddVertex(
                    dc3d.VertexPositionNormalColored(triangle.b, normal, color)
                )
                vertex_stream_pos.AddVertex(
                    dc3d.VertexPositionNormalColored(triangle.c, normal, color)
                )
                index_stream_pos.AddTriangle(
                    dc3d.IndexTriangle(first_idx, first_idx + 1, first_idx + 2)
                )
            vertex_buffer.Unmap()
            index_buffer.Unmap()

            return cls(
                display_style,
                vertex_buffer,
                vertex_count,
                index_buffer,
                index_count,
                vertex_format,
                effect_instance,
                dc3d.PrimitiveType.TriangleList,
                0,
                len(triangles),
            )
        except:
            print(traceback.format_exc())

    def flush(self):
        dc3d.DrawContext.FlushBuffer(
            self.vertex_buffer,
            self.vertex_count,
            self.index_buffer,
            self.index_count,
            self.vertex_format,
            self.effect_instance,
            self.primitive_type,
            self.start,
            self.primitive_count,
        )


class Server(dc3d.IDirectContext3DServer):
    """A generic DirectContext3dServer interface implementation."""

    def __init__(
        self,
        guid=None,
        uidoc=None,
        name="pyRevit DirectContext3DServer",
        description="Displaying temporary geometries",
        vendor_id="pyRevit",
        register=True,
    ):
        """Initalize a DirectContext3DServer instance.

        Args:
            guid (System.Guid, optional):
                The guid of the server, auto-generated if None.
                Defaults to None.
            uidoc (UI.UIDocument, optional):
                Required only, if the geometry is Document specific.
                Defaults to None.
            name (str, optional):
                The name of the server.
                Defaults to "pyRevit DirectContext3DServer".
            description (str, optional):
                The descritpion of the server.
                Defaults to "Displaying temporary geometries".
            vendor_id (str, optional):
                The name of the vendor. Defaults to "pyRevit".
            register (bool, optional):
                To register the server on initalization.
                Defaults to True.
        """
        try:
            if guid is None:
                self.guid = Guid.NewGuid()
            else:
                self.guid = guid
            self.uidoc = uidoc
            self.name = name
            self.description = description
            self.vendor_id = vendor_id
            self.meshes = []
            self._line_buffer = None
            self._transparent_buffer = None
            self._opaque_buffer = None
            self.enabled_view_types = [
                DB.ViewType.ThreeD,
                DB.ViewType.Elevation,
                DB.ViewType.Section,
                DB.ViewType.FloorPlan,
                DB.ViewType.CeilingPlan,
                DB.ViewType.EngineeringPlan,
            ]

            if register:
                self.add_server()

        except Exception:
            print(traceback.format_exc())

    # region Interface methods
    def CanExecute(self, view):
        if any(vt == view.ViewType for vt in self.enabled_view_types):
            if self.uidoc is not None:
                return self.uidoc.Document.Equals(view.Document)
            return True
        return False

    def GetApplicationId(self):
        return ""

    def GetBoundingBox(self, view):
        try:
            if not self.meshes:
                return

            vertices = [
                vertex
                for vertices in [m.vertices for m in self.meshes]
                for vertex in vertices
            ]

            if not len(vertices) > 1:
                return

            outline = DB.Outline(vertices[0], vertices[1])

            for idx in range(2, len(vertices)):
                outline.AddPoint(vertices[idx])

            return outline
        except:
            print(traceback.format_exc())

    def GetDescription(self):
        return self.description

    def GetName(self):
        return self.name

    def GetServerId(self):
        return self.guid

    def GetServiceId(self):
        return es.ExternalServices.BuiltInExternalServices.DirectContext3DService

    def GetSourceId(self):
        return ""

    def GetVendorId(self):
        return self.vendor_id

    def UsesHandles(self):
        return False

    def UseInTransparentPass(self, view):
        return True

    def RenderScene(self, view, display_style):
        try:
            if self.meshes:
                if all(
                    [
                        self._line_buffer is None,
                        self._opaque_buffer is None,
                        self._transparent_buffer is None,
                    ]
                ) or any(
                    [
                        (
                            self._line_buffer is not None
                            and not self._line_buffer.is_valid(display_style)
                        ),
                        (
                            self._opaque_buffer is not None
                            and not self._opaque_buffer.is_valid(display_style)
                        ),
                        (
                            self._transparent_buffer is not None
                            and not self._transparent_buffer.is_valid(display_style)
                        ),
                    ]
                ):
                    self.update_buffers(display_style)

                if dc3d.DrawContext.IsTransparentPass():
                    if (
                        self._transparent_buffer is not None
                        and display_style != DB.DisplayStyle.Wireframe
                    ):
                        self._transparent_buffer.flush()
                else:
                    if (
                        self._opaque_buffer is not None
                        and display_style != DB.DisplayStyle.Wireframe
                    ):
                        self._opaque_buffer.flush()
                    if (
                        self._line_buffer is not None
                        and display_style != DB.DisplayStyle.Rendering
                        and display_style != DB.DisplayStyle.Shading
                    ):
                        self._line_buffer.flush()
        except:
            print(traceback.format_exc())

    # endregion

    @property
    def meshes(self):
        """The container for the source geometries."""
        return self._meshes

    @meshes.setter
    def meshes(self, meshes):
        self._meshes = meshes
        try:
            self._meshes = meshes
            self._line_buffer = None
            self._opaque_buffer = None
            self._transparent_buffer = None
        except Exception:
            print(traceback.format_exc())

    def add_server(self):
        service = es.ExternalServiceRegistry.GetService(self.GetServiceId())
        # check for leftovers
        if service.IsRegisteredServerId(self.GetServerId()):
            self.remove_server()
        service.AddServer(self)
        server_ids = service.GetActiveServerIds()
        server_ids.Add(self.GetServerId())
        service.SetActiveServers(server_ids)

    def remove_server(self):
        service = es.ExternalServiceRegistry.GetService(self.GetServiceId())
        if service.IsRegisteredServerId(self.GetServerId()):
            service.RemoveServer(self.GetServerId())

    def update_buffers(self, display_style):
        self._line_buffer = Buffer.build_edge_buffer(display_style, self.meshes)
        self._opaque_buffer = Buffer.build_triangle_buffer(
            display_style, self.meshes, transparent=False
        )
        self._transparent_buffer = Buffer.build_triangle_buffer(
            display_style, self.meshes, transparent=True
        )
