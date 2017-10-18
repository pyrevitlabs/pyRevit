__fullframeengine__ = True

from rpws import RevitServer

rs = RevitServer('rno03p1rvtap01.teslamotors.com', '2015')

for parent, folders, files, models in rs.walk():
    print(parent)
    for fd in folders:
        print('\t@d {}'.format(fd.path))
    for f in files:
        print('\t@f {}'.format(f.path))
    for m in models:
        print('\t@m {}'.format(m.path))
