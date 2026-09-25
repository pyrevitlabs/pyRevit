"""Regression tests for IronPython 3 branch reachability in the static checker."""

import ast
import unittest

from check_py3_compat import _is_engine_guarded


def _unicode_reachability(source):
    tree = ast.parse(source)
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    return [
        _is_engine_guarded(node, parents)
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and node.id == "unicode"
    ]


class EngineGuardTests(unittest.TestCase):
    """Engine guards only suppress code that cannot run on IronPython 3."""

    def test_ironpython_branch_remains_reachable(self):
        """IRONPY includes IronPython 3 and must not hide Python 2 names."""
        self.assertEqual([False], _unicode_reachability("if IRONPY:\n    unicode(1)"))

    def test_python_two_branch_is_unreachable(self):
        """Python 2 branches are safe to exclude from the IPY3 scan."""
        self.assertEqual([True], _unicode_reachability("if PY2:\n    unicode(1)"))

    def test_python_two_else_branch_is_reachable(self):
        """The opposite side of a false condition still needs checking."""
        self.assertEqual(
            [False], _unicode_reachability("if PY2:\n    pass\nelse:\n    unicode(1)")
        )

    def test_composite_branch_uses_known_flag_values(self):
        """An unknown condition cannot hide a definitely false IPY3 branch."""
        self.assertEqual(
            [True],
            _unicode_reachability("if IRONPY and PY2 and custom:\n    unicode(1)"),
        )

    def test_skip_unless_ironpython_does_not_hide_body(self):
        """A test enabled on IPY3 still needs its body checked."""
        self.assertEqual(
            [False],
            _unicode_reachability(
                "@unittest.skipUnless(IRONPY, 'reason')\ndef test():\n    unicode(1)"
            ),
        )

    def test_skip_unless_python_two_hides_body(self):
        """A test disabled on IPY3 does not execute its body there."""
        self.assertEqual(
            [True],
            _unicode_reachability(
                "@unittest.skipUnless(PY2, 'reason')\ndef test():\n    unicode(1)"
            ),
        )


if __name__ == "__main__":
    unittest.main()
