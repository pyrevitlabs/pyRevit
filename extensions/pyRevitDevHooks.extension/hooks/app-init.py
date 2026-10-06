# python3
# pylint: skip-file

import hooks_logger as hl

hl.log_hook(__file__, {"engine": "cpython"})

print("app-init.py hook running")
