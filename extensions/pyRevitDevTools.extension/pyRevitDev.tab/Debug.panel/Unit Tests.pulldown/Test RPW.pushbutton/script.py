# import sys
# from pyrevit.coreutils.logger import get_logger
# logger = get_logger(__commandname__)

from pyrevit.coreutils import Timer

# timer = Timer()
# import imp, sys
# for mod_name, mod in sys.modules.items():
#     if mod_name != 'imp':
#         try:
#             imp.reload(mod)
#             # print('Succeeded reloading: {}'.format(mod_name))
#         except:
#             # print('------- errr reloading: {}'.format(mod_name))
#             pass
# endtime = timer.get_time()
# print('module reload time: {} seconds'.format(endtime))


timer = Timer()
import rpw
from rpw import db, DB, extras
endtime = timer.get_time()
print('rpw load time: {} seconds'.format(endtime))

from scriptutils import this_script
print this_script.info

import sys
# print globals().keys()
print '\n'.join(sorted(sys.modules.keys()))
