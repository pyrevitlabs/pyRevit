import os
import os.path as op


def assert_folder(folder):
    if not op.exists(folder):
        try:
            os.makedirs(folder)
        except:
            return False
    return True