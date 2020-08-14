"""Test standard input in pyRevit console window."""
# pylint: disable-all
__context__ = 'zero-doc'
__fullframeengine__ = True

import sys
PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3


print("stdout: %s", sys.stdout.__class__)
print("stdin: %s", sys.stdin.__class__)
print("stderr: %s", sys.stderr.__class__)
sys.stdout.write("Hello")
print("Enter anything:")
print(sys.stdin.read())

# test raw_input in py2
if PY2: 
    m = raw_input("Enter raw input (py2):")
    print(m)

    # this fails in py2 since it is wrapped in eval
    # https://ironpython-test.readthedocs.io/en/latest/library/functions.html#input
    m = input("Enter expression (e.g. 1+2):")
    print(m)

    m = raw_input("Select File:")
    print(m)
else:
    m = input("Enter string:")
    print(m)

