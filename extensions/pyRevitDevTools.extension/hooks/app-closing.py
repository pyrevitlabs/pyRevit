# pylint: skip-file
import os.path as op
USER_DESKTOP = op.expandvars('%userprofile%\\desktop')

with open(op.join(USER_DESKTOP, 'hooks.txt'), 'a') as f:
    f.write('\n'.join([
        'Application Closing '.ljust(80, '-'),
        'Cancellable? ' + str(__eventargs__.Cancellable) + '\n']))
