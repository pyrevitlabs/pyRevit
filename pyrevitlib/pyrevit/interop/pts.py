"""Read and Write PTS PointCloud Files."""


def load(inputfile):
    """Read list of point tuple from PTS file."""
    points = []
    with open(inputfile, 'r') as ptsfile:
        # point_count = int(ptsfile.readline())   #noqa
        for line in ptsfile:
            data = line.split(' ')
            points.append(((float(data[0]), float(data[1]), float(data[2])),
                           int(data[3]),
                           (int(data[4]), int(data[5]), int(data[6])))
                          )
    return points


def dump(outputfile, points):
    """Write list of point tuple to PTS file."""
    point_count = len(points)
    with open(outputfile, 'w') as ptsfile:
        ptsfile.write(str(point_count) + '\n')
        for coord, intensity, color in points:
            x, y, z = coord
            r, g, b = color
            ptsfile.write('{:.10f} {:.10f} {:.10f} '
                          '{} '
                          '{:03} {:03} {:03}\n'.format(x, y, z,
                                                       intensity,
                                                       r, g, b))
