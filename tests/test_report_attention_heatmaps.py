import json
import textwrap
import unittest
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np


NOTEBOOK_PATH = Path(__file__).resolve().parents[1] / "CITS4012_15_1018.ipynb"
CELL_TITLE = "# @title Standalone report attention heat maps"
PLOTTING_MARKER = "# Shared report plotting helpers"


def load_plotting_source():
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
    source = matches[0]
    marker_index = source.index(PLOTTING_MARKER)
    return source[source.rfind("#", 0, marker_index):]


def render_report_figures():
    tokens = ["rub", "bar", "soap", "on", "drawer", "s", "runners"]
    token_attention = np.asarray([0.14, 0.12, 0.13, 0.11, 0.16, 0.15, 0.19])
    matrix = np.eye(len(tokens), dtype=float)
    row = {
        "goal": "Loosen stuck drawers.",
        "sol1": "Rub bar soap on drawer's hands.",
        "sol2": "Rub bar soap on drawer's runners.",
    }
    namespace = {
        "np": np,
        "plt": plt,
        "Rectangle": Rectangle,
        "textwrap": textwrap,
        "full_goal_tokens": ["loosen", "stuck", "drawers"],
        "full_sol1_tokens": tokens,
        "full_sol2_tokens": tokens,
        "failure_sol1_tokens": tokens,
        "failure_sol2_tokens": tokens,
        "full_attention": {
            "sol1_alpha": token_attention,
            "sol2_alpha": token_attention,
            "goal_alpha": np.asarray([0.29, 0.33, 0.38]),
            "sol1_align": matrix,
            "sol2_align": matrix,
        },
        "failure_attention": {
            "sol1_alpha": token_attention,
            "sol2_alpha": token_attention,
        },
        "full_sol1_different": {6},
        "full_sol2_different": {6},
        "failure_sol1_different": {6},
        "failure_sol2_different": {6},
        "validation_rows": [row],
        "SUCCESS_INDEX": 0,
        "failure_index": 0,
        "full_gold": 1,
        "full_prediction": 1,
        "failure_gold": 1,
        "failure_prediction": 0,
        "full_probabilities": np.asarray([0.383, 0.617]),
        "failure_probabilities": np.asarray([0.938, 0.062]),
        "failure_confidence": 0.938,
        "failure_lambda": 0.810,
    }
    original_show = plt.show
    plt.show = lambda: None
    try:
        exec(compile(load_plotting_source(), str(NOTEBOOK_PATH), "exec"), namespace)
    finally:
        plt.show = original_show
    return namespace


class TestReportAttentionHeatmapTypography(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.namespace = render_report_figures()
        cls.success_figure = cls.namespace["success_figure"]
        cls.failure_figure = cls.namespace["failure_figure"]

    @classmethod
    def tearDownClass(cls):
        plt.close(cls.success_figure)
        plt.close(cls.failure_figure)

    def test_figures_are_compact_enough_for_report_page_scaling(self):
        success_width, success_height = self.success_figure.get_size_inches()
        failure_width, failure_height = self.failure_figure.get_size_inches()
        self.assertLessEqual(success_width, 13.0)
        self.assertLessEqual(success_height, 10.5)
        self.assertLessEqual(failure_width, 13.0)
        self.assertLessEqual(failure_height, 7.8)

    def test_titles_ticks_and_cell_values_remain_readable_after_embedding(self):
        self.assertGreaterEqual(self.success_figure._suptitle.get_fontsize(), 18)
        self.assertGreaterEqual(self.failure_figure._suptitle.get_fontsize(), 18)

        data_axes = [
            self.namespace["success_a1_sol1_ax"],
            self.namespace["success_a1_sol2_ax"],
            self.namespace["success_a2_ax"],
            self.namespace["success_a3_12_ax"],
            self.namespace["success_a3_21_ax"],
            self.namespace["failure_sol1_ax"],
            self.namespace["failure_sol2_ax"],
        ]
        for axis in data_axes:
            self.assertGreaterEqual(axis.title.get_fontsize(), 14)
            for tick in axis.get_xticklabels() + axis.get_yticklabels():
                self.assertGreaterEqual(tick.get_fontsize(), 12)
            for annotation in axis.texts:
                self.assertGreaterEqual(annotation.get_fontsize(), 11)

    def test_side_by_side_a1_titles_do_not_overlap(self):
        self.success_figure.canvas.draw()
        renderer = self.success_figure.canvas.get_renderer()
        left_bounds = self.namespace["success_a1_sol1_ax"].title.get_window_extent(renderer)
        right_bounds = self.namespace["success_a1_sol2_ax"].title.get_window_extent(renderer)
        self.assertLessEqual(left_bounds.x1 + 5, right_bounds.x0)

    def test_token_heatmap_cell_labels_are_compact(self):
        token_axes = [
            self.namespace["success_a1_sol1_ax"],
            self.namespace["success_a1_sol2_ax"],
            self.namespace["success_a2_ax"],
            self.namespace["failure_sol1_ax"],
            self.namespace["failure_sol2_ax"],
        ]
        for axis in token_axes:
            for annotation in axis.texts:
                self.assertRegex(annotation.get_text(), r"^\d\.\d{2}$")

    def test_metadata_captions_and_colorbars_use_report_sized_text(self):
        narrative_axes = [
            self.namespace["success_info_ax"],
            self.namespace["success_caption_ax"],
            self.namespace["failure_info_ax"],
            self.namespace["failure_caption_ax"],
        ]
        for axis in narrative_axes:
            self.assertTrue(axis.texts)
            for text in axis.texts:
                self.assertGreaterEqual(text.get_fontsize(), 12)

        data_axes = {
            self.namespace["success_a1_sol1_ax"],
            self.namespace["success_a1_sol2_ax"],
            self.namespace["success_a2_ax"],
            self.namespace["success_a3_12_ax"],
            self.namespace["success_a3_21_ax"],
            self.namespace["failure_sol1_ax"],
            self.namespace["failure_sol2_ax"],
            self.namespace["success_info_ax"],
            self.namespace["success_caption_ax"],
            self.namespace["failure_info_ax"],
            self.namespace["failure_caption_ax"],
        }
        colorbar_axes = [
            axis
            for figure in (self.success_figure, self.failure_figure)
            for axis in figure.axes
            if axis not in data_axes
        ]
        self.assertEqual(len(colorbar_axes), 4)
        for axis in colorbar_axes:
            self.assertGreaterEqual(axis.yaxis.label.get_fontsize(), 12)
            for tick in axis.get_yticklabels():
                self.assertGreaterEqual(tick.get_fontsize(), 11)


if __name__ == "__main__":
    unittest.main()
