# from six import u, iteritems, iterkeys # pylint: disable=unused-import

# grabbed all imports and placed here for compatibility with
# IronPython running on non-fullframe engine in Revit


def iterkeys(d, **kw):
    return d.iterkeys(**kw)


def iteritems(d, **kw):
    return d.iteritems(**kw)


def u(s):
    return unicode(s.replace(r'\\', r'\\\\'), "unicode_escape")
