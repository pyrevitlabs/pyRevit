"""Read and Write Bounding Box Files."""


def load(inputfile):
    bboxes = []
    with open(inputfile, 'r') as bbxfile:
        bbox_count = int(bbxfile.readline())   #noqa
        for line in bbxfile:
            data = line.split(' ')
            bboxes.append(
                ((float(data[0]), float(data[1]), float(data[2])),
                 (float(data[3]), float(data[4]), float(data[5])))
                )
    return bboxes


def dump(outputfile, bbox_list):
    bbox_count = len(bbox_list)
    with open(outputfile, 'w') as bbxfile:
        bbxfile.write(str(bbox_count) + '\n')
        for bbox in bbox_list:
            bbxfile.write(
                '{:.02f} {:.02f} {:.02f} {:.02f} {:.02f} {:.02f}\n'
                .format(*bbox[0], *bbox[1])
                )
