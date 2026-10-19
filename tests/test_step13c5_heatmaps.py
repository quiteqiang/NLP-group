import ast
import json
import textwrap
import unittest
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np


class MatplotlibHeatmapAdapter:
    """Small local stand-in that preserves the Matplotlib artists we inspect."""

    @staticmethod
    def heatmap(
        values,
        *,
        ax,
        cmap,
        vmin,
        vmax,
        center,
        xticklabels,
        yticklabels,
        annot,
        fmt,
        annot_kws,
        linewidths,
        cbar_kws,
    ):
        del center, linewidths
        values = np.asarray(values, dtype=float)
        image = ax.imshow(values, cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
        ax.set_xticks(np.arange(len(xticklabels)), labels=xticklabels)
        ax.set_yticks(np.arange(len(yticklabels)), labels=yticklabels)
        if annot:
            for row in range(values.shape[0]):
                for column in range(values.shape[1]):
                    ax.text(
                        column,
                        row,
                        format(values[row, column], fmt),
                        ha="center",
                        va="center",
                        **annot_kws,
                    )
        ax.figure.colorbar(image, ax=ax, label=cbar_kws["label"])
        return ax


NOTEBOOK_PATH = Path(__file__).resolve().parents[1] / "CITS4012_15_1018.ipynb"
CELL_TITLE = "# @title Step 13C.5:"
FUNCTION_NAMES = {
    "step15c_positive_limit",
    "draw_step15c_metric_heatmap",
    "draw_step15c_configuration_comparison",
}
CONSTANT_PREFIX = "STEP15C_REPORT_"
TEMPERATURE_MODES = ("unscaled", "fixed_sqrt_d", "learned_temperature")


def load_plotting_functions():
    notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
    matches = [
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
        and "".join(cell.get("source", [])).startswith(CELL_TITLE)
    ]
    if len(matches) != 1:
        raise AssertionError(
            f"Expected exactly one {CELL_TITLE!r} cell, found {len(matches)}."
        )
    tree = ast.parse(matches[0])
    selected_nodes = [
        node
        for node in tree.body
        if (
            isinstance(node, ast.FunctionDef)
            and node.name in FUNCTION_NAMES
        )
        or (
            isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name)
                and target.id.startswith(CONSTANT_PREFIX)
                for target in node.targets
            )
        )
    ]
    function_names = {
        node.name for node in selected_nodes if isinstance(node, ast.FunctionDef)
    }
    if function_names != FUNCTION_NAMES:
        raise AssertionError("Step 13C.5 plotting functions are incomplete.")
    namespace = {
        "np": np,
        "plt": plt,
        "sns": MatplotlibHeatmapAdapter,
        "textwrap": textwrap,
        "STEP15C_TEMPERATURE_MODES": TEMPERATURE_MODES,
        "STEP15C_DISPLAY_NAMES": {"example": "Example configuration"},
    }
    module = ast.Module(body=selected_nodes, type_ignores=[])
    exec(compile(module, str(NOTEBOOK_PATH), "exec"), namespace)
    return namespace


def build_prepared_run(token_count=23):
    ascending = np.arange(1, token_count + 1, dtype=float)
    descending = ascending[::-1].copy()
    attention_rows = (
        ascending / ascending.sum(),
        np.full(token_count, 1.0 / token_count),
        descending / descending.sum(),
    )
    prepared_run = {}
    for mode_index, mode in enumerate(TEMPERATURE_MODES):
        alpha = attention_rows[mode_index]
        solution_result = {
            "scaled_score": np.linspace(-1.0, 1.0, token_count)
            / (mode_index + 1),
            "alpha": alpha,
            "normalized_entropy": 0.90 + 0.04 * mode_index,
            "max_alpha": float(alpha.max()),
        }
        prepared_run[("example", mode)] = {
            "result": {
                "temperature": (1.0, 14.1421, 13.3059)[mode_index],
                "solutions": {
                    "sol1": solution_result,
                    "sol2": {
                        **solution_result,
                        "scaled_score": solution_result["scaled_score"][::-1].copy(),
                        "alpha": alpha[::-1].copy(),
                    },
                },
            }
        }
    return prepared_run


def render_step13c5_figure():
    namespace = load_plotting_functions()
    tokens = [f"token_{index}" for index in range(23)]
    original_show = plt.show
    plt.show = lambda: None
    try:
        figure = namespace["draw_step15c_configuration_comparison"](
            "example",
            build_prepared_run(),
            tokens,
            tokens,
            {"goal": "Choose the best practical solution for the described task."},
            1,
            0,
            635,
        )
    finally:
        plt.show = original_show
    return figure


class TestStep13C5ReportTypography(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.figure = render_step13c5_figure()
        cls.data_axes = [axis for axis in cls.figure.axes if axis.get_title()]
        cls.colorbar_axes = [
            axis
            for axis in cls.figure.axes
            if axis.get_ylabel()
            in {"scaled attention logit", "attention weight", "delta attention weight"}
        ]

    @classmethod
    def tearDownClass(cls):
        plt.close(cls.figure)

    def test_figure_is_compact_enough_for_report_page_scaling(self):
        width, height = self.figure.get_size_inches()
        self.assertLessEqual(width, 12.5)
        self.assertLessEqual(height, 17.0)

    def test_heatmap_text_remains_readable_after_embedding(self):
        self.assertGreaterEqual(self.figure._suptitle.get_fontsize(), 20)
        self.assertEqual(len(self.data_axes), 6)
        for axis in self.data_axes:
            self.assertGreaterEqual(axis.title.get_fontsize(), 16)
            self.assertGreaterEqual(axis.xaxis.label.get_fontsize(), 14)
            self.assertGreaterEqual(axis.yaxis.label.get_fontsize(), 14)
            for tick in axis.get_xticklabels() + axis.get_yticklabels():
                self.assertGreaterEqual(tick.get_fontsize(), 12)
            self.assertTrue(axis.texts)
            for annotation in axis.texts:
                self.assertGreaterEqual(annotation.get_fontsize(), 11)

    def test_colorbars_are_readable(self):
        self.assertEqual(len(self.colorbar_axes), 6)
        for axis in self.colorbar_axes:
            self.assertGreaterEqual(axis.yaxis.label.get_fontsize(), 12)
            for tick in axis.get_yticklabels():
                self.assertGreaterEqual(tick.get_fontsize(), 11)

    def test_primary_heatmaps_show_only_mode_names(self):
        expected = ["unscaled", "fixed sqrt(d)", "learned T"]
        primary_axes = [
            axis for axis in self.data_axes if "change in alpha" not in axis.get_title()
        ]
        self.assertEqual(len(primary_axes), 4)
        for axis in primary_axes:
            self.assertEqual(
                [tick.get_text() for tick in axis.get_yticklabels()],
                expected,
            )

    def test_heatmaps_use_space_reclaimed_from_removed_statistics(self):
        self.figure.canvas.draw()
        for axis in self.data_axes:
            self.assertLessEqual(axis.get_position().x0, 0.18)

    def test_cell_annotations_are_short_enough_for_23_token_rows(self):
        for axis in self.data_axes:
            for annotation in axis.texts:
                self.assertLessEqual(len(annotation.get_text()), 5)

    def test_row_label_lines_are_short_enough_to_preserve_heatmap_width(self):
        for axis in self.data_axes:
            for tick in axis.get_yticklabels():
                self.assertLessEqual(len(tick.get_text().splitlines()), 2)
                for line in tick.get_text().splitlines():
                    self.assertLessEqual(len(line), 22)

    def test_adjacent_row_labels_do_not_overlap(self):
        self.figure.canvas.draw()
        renderer = self.figure.canvas.get_renderer()
        for axis in self.data_axes:
            bounds = sorted(
                (tick.get_window_extent(renderer) for tick in axis.get_yticklabels()),
                key=lambda box: box.y0,
            )
            for lower, upper in zip(bounds, bounds[1:]):
                self.assertLessEqual(lower.y1 + 2, upper.y0)


if __name__ == "__main__":
    unittest.main()
