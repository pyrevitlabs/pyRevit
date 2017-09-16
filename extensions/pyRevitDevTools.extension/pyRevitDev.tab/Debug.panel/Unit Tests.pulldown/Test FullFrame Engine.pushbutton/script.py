__fullframeengine__ = True

from rpws import RevitServer

rs = RevitServer('testserver', '2018')

for parent, folders, files, models in rs.walk():
    print(parent)
    for fd in folders:
        print('\t@d {}'.format(fd.path))
    for f in files:
        print('\t@f {}'.format(f.path))
    for m in models:
        print('\t@m {}'.format(m.path))
