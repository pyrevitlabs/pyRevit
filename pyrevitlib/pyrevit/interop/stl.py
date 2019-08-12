"""Read and Write STL Binary and ASCII Files."""
#
# import struct
#
#
# def load(inputfile):
#     pass
#
#
# def dump(outputfile):
#     struct.pack('<I', bboxe_count * 12)
#     for bbox in bboxes:
#         minx = bbox.Min.X
#         miny = bbox.Min.Y
#         minz = bbox.Min.Z
#         maxx = bbox.Max.X
#         maxy = bbox.Max.Y
#         maxz = bbox.Max.Z
#         facets = [
#             [(0.0, -1.0, 0.0), [(minx, miny, minz),
#                                 (maxx, miny, minz),
#                                 (minx, miny, maxz)]],
#             [(0.0, -1.0, 0.0), [(minx, miny, maxz),
#                                 (maxx, miny, minz),
#                                 (maxx, miny, maxz)]],
#             [(0.0, 1.0, 0.0), [(minx, maxy, minz),
#                                (maxx, maxy, minz),
#                                (minx, maxy, maxz)]],
#             [(0.0, 1.0, 0.0), [(minx, maxy, maxz),
#                                (maxx, maxy, minz),
#                                (maxx, maxy, maxz)]],
#             [(-1.0, 0.0, 0.0), [(minx, miny, minz),
#                                 (minx, miny, maxz),
#                                 (minx, maxy, minz)]],
#             [(-1.0, 0.0, 0.0), [(minx, maxy, minz),
#                                 (minx, miny, maxz),
#                                 (minx, maxy, maxz)]],
#             [(1.0, 0.0, 0.0), [(maxx, miny, minz),
#                                (maxx, miny, maxz),
#                                (maxx, maxy, minz)]],
#             [(1.0, 0.0, 0.0), [(maxx, maxy, minz),
#                                (maxx, miny, maxz),
#                                (maxx, maxy, maxz)]],
#             [(0.0, 0.0, -1.0), [(minx, miny, minz),
#                                 (minx, maxy, minz),
#                                 (maxx, miny, minz)]],
#             [(0.0, 0.0, -1.0), [(maxx, miny, minz),
#                                 (minx, maxy, minz),
#                                 (maxx, maxy, minz)]],
#             [(0.0, 0.0, 1.0), [(minx, miny, maxz),
#                                (minx, maxy, maxz),
#                                (maxx, miny, maxz)]],
#             [(0.0, 0.0, 1.0), [(maxx, miny, maxz),
#                                (minx, maxy, maxz),
#                                (maxx, maxy, maxz)]],
#             ]
#         for facet in facets:
#             bboxfile.write(struct.pack('<3f', *facet[0]))
#             for vertix in facet[1]:
#                 bboxfile.write(struct.pack('<3f', *vertix))
#             # attribute byte count (should be 0 per specs)
#             bboxfile.write('\0\0')
