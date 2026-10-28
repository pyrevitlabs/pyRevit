"""Stand in for IronPython's ``wpf`` module under CPython.

``pyrevit.framework.wpf`` is this module under CPython. It populates plain CLR
objects from XAML the way IronPython's ``wpf.LoadComponent`` does, for
example ``wpf.LoadComponent(DataTemplate(), StringReader(xaml))``.

Note:
    Python classes deriving from WPF types, such as a ``Window`` or
    ``UserControl`` subclass, cannot be loaded this way under CPython: their
    XAML event handlers and named elements need IronPython's dynamic loader.
    Use ``pyrevit.forms.WPFWindow`` or ``WPFPanel`` instead.
"""

import clr

clr.AddReference("System.Xaml")
clr.AddReference("System.Xml")
clr.AddReference("PresentationFramework")

import System  # noqa: E402
from System.Windows.Markup import XamlReader  # noqa: E402
from System.Xaml import (  # noqa: E402
    XamlObjectWriter,
    XamlObjectWriterSettings,
    XamlServices,
    XamlXmlReader,
    XamlXmlReaderSettings,
)


def _is_python_class(cls):
    clr_type = clr.GetClrType(cls)
    if clr_type.GetInterface("IPythonDerivedType") is not None:
        return True
    return cls.__module__ != clr_type.Namespace


def LoadComponent(target, source):  # noqa: N802
    """Apply XAML whose root describes ``target`` to ``target`` itself.

    Args:
        target (object): CLR object to populate, such as a new
            ``DataTemplate``; the XAML root element must be of its type.
        source (str | System.IO.TextReader): XAML file path or reader.

    Returns:
        (object): ``target``, populated.

    Raises:
        PyRevitCPythonNotSupported: ``target`` is an instance of a Python
            class, such as a ``Window`` or ``UserControl`` subclass.
    """
    if _is_python_class(type(target)):
        from pyrevit import PyRevitCPythonNotSupported

        raise PyRevitCPythonNotSupported(
            "wpf.LoadComponent for Python-derived {} (use forms.WPFWindow "
            "or forms.WPFPanel)".format(type(target).__name__)
        )
    reader_settings = XamlXmlReaderSettings()
    if isinstance(source, str):
        reader_settings.BaseUri = System.Uri(System.IO.Path.GetFullPath(source))
        text = System.IO.StreamReader(source)
    else:
        text = source
    context = XamlReader.GetWpfSchemaContext()
    xml = System.Xml.XmlReader.Create(text)
    try:
        reader = XamlXmlReader(xml, context, reader_settings)
        writer_settings = XamlObjectWriterSettings()
        writer_settings.RootObjectInstance = target
        writer = XamlObjectWriter(context, writer_settings)
        XamlServices.Transform(reader, writer)
        return writer.Result
    finally:
        xml.Dispose()
        if text is not source:
            text.Dispose()
