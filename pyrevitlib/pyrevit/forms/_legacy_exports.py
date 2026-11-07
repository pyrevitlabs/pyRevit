"""IronPython-only names ``pyrevit.forms`` exported before the engine split.

Only the IronPython facade (``_ipy_legacy``) exports them. Under CPython,
``pyrevit.forms`` reports them as unsupported features rather than as missing
attributes: ``wpf`` and ``pyevent`` are IronPython modules, and ``Autodesk`` is
the namespace IronPython binds by importing the InfoCenter classes. Every
engine-neutral pre-split export lives in ``_common.__all__`` instead.

Note:
    ``LEGACY_EXPORTS`` must stay a literal list; tooling reads it without
    importing the module. This module must stay importable by IronPython 2.7.
"""

LEGACY_EXPORTS = [
    "Autodesk",
    "pyevent",
    "wpf",
]
