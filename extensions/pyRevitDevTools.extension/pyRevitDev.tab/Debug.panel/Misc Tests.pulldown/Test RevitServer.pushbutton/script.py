from rpws import RevitServer


__fullframeengine__ = True
__context__ = 'zero-doc'


rs = RevitServer('rshil02', '2017')

for parent, folders, files, models in rs.walk():
    print(parent)
    for fd in folders:
        print('\t@d {}'.format(fd.path))
    for f in files:
        print('\t@f {}'.format(f.path))
    for m in models:
        print('\t@m {}'.format(m.path))
