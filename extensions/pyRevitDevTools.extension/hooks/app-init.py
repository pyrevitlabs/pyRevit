# pylint: skip-file
import os.path as op
USER_DESKTOP = op.expandvars('%userprofile%\\desktop')

with open(op.join(USER_DESKTOP, 'hooks.txt'), 'a') as f:
    f.write('\n'.join([
        'Application Init '.ljust(80, '-'),
        'Event Args? ' + str(__eventargs__) + '\n']))
