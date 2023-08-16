"""Read and Write Bounding Box Files."""


def load(inputfile):
    """Read list of bounding boxes from file.

    Args:
        inputfile (str): path to input file

    Returns:
        (list[tuple[tuple[float, float, float], tuple[float, float, float]]]):
            bounding boxes
    """
    bboxes = []
    with open(inputfile, 'r') as bbxfile:
        # bbox_count = int(bbxfile.readline())   #noqa
        for line in bbxfile:
            data = line.split(' ')
            bboxes.append(
                ((float(data[0]), float(data[1]), float(data[2])),
                 (float(data[3]), float(data[4]), float(data[5])))
                )
    return bboxes


def dump(outputfile, bbox_list):
    """Write list of bounding boxes to file.

    Args:
        outputfile (str): path to output file
        bbox_list (list[tuple[tuple[float, float, float], tuple[float, float, float]]]): 
            bounding boxes
    """
    bbox_count = len(bbox_list)
    with open(outputfile, 'w') as bbxfile:
        bbxfile.write(str(bbox_count) + '\n')
        for bbox in bbox_list:
            minx, miny, minz = bbox[0]
            maxx, maxy, maxz = bbox[1]
            bbxfile.write(
                '{:.02f} {:.02f} {:.02f} {:.02f} {:.02f} {:.02f}\n'
                .format(minx, miny, minz, maxx, maxy, maxz)
                )
