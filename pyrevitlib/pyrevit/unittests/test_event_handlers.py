"""Cover event-handler cleanup across reloads without importing Revit APIs."""

import ast
import io
import os
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def _load_functions(relative_path, names, namespace):
    with io.open(
        os.path.join(ROOT, relative_path), encoding="utf-8-sig"
    ) as source_file:
        tree = ast.parse(source_file.read())
    tree.body = [node for node in tree.body if getattr(node, "name", None) in names]
    exec(compile(tree, relative_path, "exec"), namespace)
    return namespace


class _Namespace(object):
    def __init__(self, **values):
        self.__dict__.update(values)


class _Hashtable(dict):
    @property
    def Keys(self):
        return list(self)

    def ContainsKey(self, key):
        return key in self

    def Remove(self, key):
        self.pop(key, None)


class _AppDomain(object):
    def __init__(self):
        self.data = {}

    def GetData(self, key):
        return self.data.get(key)

    def SetData(self, key, value):
        self.data[key] = value


def _load_event_functions(app_domain, removed_handlers):
    namespace = {
        "framework": _Namespace(AppDomain=_Namespace(CurrentDomain=app_domain)),
        "Hashtable": _Hashtable,
        "_REGISTERED_HANDLERS_KEY": "pyRevitRegisteredEventHandlers",
        "add_handler": lambda event_name, handler_func: event_name + "-delegate",
        "remove_handler": lambda event_name, event_handler: removed_handlers.append(
            (event_name, event_handler)
        ),
    }
    functions = _load_functions(
        "pyrevitlib/pyrevit/revit/events.py",
        {
            "_get_registered_handlers",
            "register_handler",
            "unregister_handler",
            "unregister_exec_handlers",
            "unregister_all_exec_handlers",
        },
        namespace,
    )
    namespace["REGISTERED_HANDLERS"] = functions["_get_registered_handlers"]()
    return functions


class EventHandlerCleanupTests(unittest.TestCase):
    """Cover event unsubscription behavior during session reloads."""

    def test_reload_engine_cleans_handlers_registered_in_another_engine(self):
        """Share registrations across engines so reload removes every callback."""
        app_domain = _AppDomain()
        removed_handlers = []
        script_engine = _load_event_functions(app_domain, removed_handlers)
        reload_engine = _load_event_functions(app_domain, removed_handlers)
        self.assertIs(
            script_engine["REGISTERED_HANDLERS"],
            reload_engine["REGISTERED_HANDLERS"],
        )
        for event_name in ("doc-changed", "view-activated"):
            script_engine["register_handler"](event_name, object(), "script-exec")
        reload_engine["register_handler"]("doc-opened", object(), "reload-exec")

        reload_engine["unregister_all_exec_handlers"]()

        self.assertEqual(dict(script_engine["REGISTERED_HANDLERS"]), {})
        self.assertEqual(
            set(removed_handlers),
            {
                ("doc-changed", "doc-changed-delegate"),
                ("view-activated", "view-activated-delegate"),
                ("doc-opened", "doc-opened-delegate"),
            },
        )

    def test_reload_cleans_handlers_before_loading_session(self):
        """Run event cleanup before invoking the session loader."""
        calls = []
        namespace = {
            "mlogger": type(
                "Logger",
                (),
                {"info": lambda self, message: calls.append(("log", message))},
            )(),
            "revit": type(
                "Revit",
                (),
                {
                    "events": type(
                        "Events",
                        (),
                        {
                            "unregister_all_exec_handlers": lambda self: calls.append(
                                ("cleanup",)
                            )
                        },
                    )()
                },
            )(),
            "load_session": lambda: calls.append(("load",)) or "new-session",
        }
        _load_functions(
            "pyrevitlib/pyrevit/loader/sessionmgr.py",
            {"reload_pyrevit"},
            namespace,
        )

        self.assertEqual(namespace["reload_pyrevit"](), "new-session")
        self.assertEqual(
            calls,
            [
                ("log", "Reloading...."),
                ("cleanup",),
                ("load",),
            ],
        )
