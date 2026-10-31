"""Host-free tests for the DevTools fill pattern preview geometry."""

import ast
import math
import os
import types
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
SCRIPT_PATH = os.path.join(
    REPO_ROOT,
    "extensions",
    "pyRevitDevTools.extension",
    "pyRevitDev.tab",
    "Debug.panel",
    "Unit Tests.pulldown",
    "Test FillPatternViewer.pushbutton",
    "script.py",
)
PURE_NAMES = {"MAX_LINES_PER_GRID", "MIN_DASH", "_round_cap_dashes", "_grid_lines"}


def _load_pure_helpers():
    with open(SCRIPT_PATH, encoding="utf-8") as script_file:
        tree = ast.parse(script_file.read(), SCRIPT_PATH)
    nodes = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in PURE_NAMES:
            nodes.append(node)
        elif isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id in PURE_NAMES
            for target in node.targets
        ):
            nodes.append(node)
    found = {
        node.name if isinstance(node, ast.FunctionDef) else target.id
        for node in nodes
        for target in ([node] if isinstance(node, ast.FunctionDef) else node.targets)
        if isinstance(node, ast.FunctionDef) or isinstance(target, ast.Name)
    }
    missing = PURE_NAMES - found
    if missing:
        raise AssertionError(
            "{} no longer defines {}; update PURE_NAMES".format(
                SCRIPT_PATH, ", ".join(sorted(missing))
            )
        )
    namespace = {"math": math}
    exec(
        compile(ast.Module(body=nodes, type_ignores=[]), SCRIPT_PATH, "exec"), namespace
    )
    return types.SimpleNamespace(**namespace)


def _grid(angle=0.0, offset=1.0, shift=0.0, origin=(0.0, 0.0)):
    return types.SimpleNamespace(
        Angle=angle,
        Offset=offset,
        Shift=shift,
        Origin=types.SimpleNamespace(U=origin[0], V=origin[1]),
    )


def _normal_distance(fill_grid, point):
    return -math.sin(fill_grid.Angle) * point[0] + math.cos(fill_grid.Angle) * point[1]


class GridLinesTests(unittest.TestCase):
    """Check that preview lines cover the whole canvas, even when thinned."""

    def setUp(self):
        """Load the pure preview helpers from the button script."""
        self.viewer = _load_pure_helpers()

    def _distances(self, fill_grid, scale, radius):
        return [
            _normal_distance(fill_grid, start) * scale
            for start, _, _ in self.viewer._grid_lines(fill_grid, scale, radius)
        ]

    def test_sparse_grid_keeps_every_line(self):
        """Keep each line when the grid is below the line limit."""
        fill_grid = _grid(offset=0.01)
        distances = self._distances(fill_grid, 4000.0, 200.0)
        self.assertEqual(len(distances), 11)
        self.assertAlmostEqual(min(distances), -200.0)
        self.assertAlmostEqual(max(distances), 200.0)

    def test_dense_grid_is_thinned_across_full_range(self):
        """Thin dense grids evenly so lines reach both canvas edges."""
        for angle in (0.0, math.pi / 4, math.pi / 2, 2.0):
            for origin in ((0.0, 0.0), (0.37, -1.2)):
                fill_grid = _grid(
                    angle=angle, offset=0.0001, shift=0.00003, origin=origin
                )
                distances = self._distances(fill_grid, 4000.0, 200.0)
                self.assertLessEqual(len(distances), self.viewer.MAX_LINES_PER_GRID)
                spacing = 0.0001 * 4000.0 * math.ceil(1001 / 250.0)
                self.assertLess(min(distances), -200.0 + spacing)
                self.assertGreater(max(distances), 200.0 - spacing)

    def test_negative_offset_covers_full_range(self):
        """Cover the canvas when the grid offset is negative."""
        fill_grid = _grid(angle=1.0, offset=-0.0001)
        distances = self._distances(fill_grid, 4000.0, 200.0)
        self.assertLessEqual(len(distances), self.viewer.MAX_LINES_PER_GRID)
        self.assertLess(min(distances), -198.0)
        self.assertGreater(max(distances), 198.0)


class RoundCapDashesTests(unittest.TestCase):
    """Check dash compensation for WPF round caps."""

    def setUp(self):
        """Load the pure preview helpers from the button script."""
        self.viewer = _load_pure_helpers()

    def test_dot_becomes_tiny_dash_with_same_period(self):
        """Draw zero-length dots as tiny round-capped dashes."""
        dashes = self.viewer._round_cap_dashes([0.0, 10.0], 1.0)
        self.assertEqual(dashes[0], self.viewer.MIN_DASH)
        self.assertAlmostEqual(sum(dashes), 10.0)

    def test_long_dash_shrinks_by_cap_length(self):
        """Shorten dashes by the cap length and widen gaps to match."""
        self.assertEqual(self.viewer._round_cap_dashes([5.0, 3.0], 1.0), [4.0, 4.0])

    def test_mixed_pattern_keeps_period(self):
        """Preserve the pattern period with dots and dashes mixed."""
        segments = [8.0, 2.0, 0.0, 2.0, 0.5, 1.0]
        dashes = self.viewer._round_cap_dashes(segments, 1.0)
        self.assertAlmostEqual(sum(dashes), sum(segments))
        self.assertTrue(all(dash > 0 for dash in dashes))


if __name__ == "__main__":
    unittest.main()
