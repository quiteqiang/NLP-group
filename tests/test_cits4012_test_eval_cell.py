import ast
import json
import re
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
import torch


NOTEBOOK_PATH = Path(__file__).resolve().parents[1] / "CITS4012_15.ipynb"
CELL_TITLE = "# @title [RUN ONCE] Test-set evaluation: No attention vs Full model"
TABLE_CELL_TITLE = "# @title Test-set accuracy summary table"


def load_test_eval_cell_source():
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
    return matches[0]


def load_table_cell_source():
    notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
    matches = [
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
        and "".join(cell.get("source", [])).startswith(TABLE_CELL_TITLE)
    ]
    if len(matches) != 1:
        raise AssertionError(
            f"Expected exactly one {TABLE_CELL_TITLE!r} cell, found {len(matches)}."
        )
    return matches[0]


def literal_assignment(tree, name):
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise AssertionError(f"Missing literal assignment for {name}.")


def load_function(source, function_name, extra_globals=None):
    tree = ast.parse(source)
    function_nodes = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function_name
    ]
    if len(function_nodes) != 1:
        raise AssertionError(
            f"Expected exactly one function named {function_name}, found {len(function_nodes)}."
        )
    namespace = dict(extra_globals or {})
    module = ast.Module(body=function_nodes, type_ignores=[])
    exec(compile(module, filename=str(NOTEBOOK_PATH), mode="exec"), namespace)
    return namespace[function_name]


class TestStandaloneTestEvaluationCell(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = load_test_eval_cell_source()
        cls.tree = ast.parse(cls.source)

    def test_cell_compiles_and_fixes_the_official_runs_and_seeds(self):
        compile(self.source, filename=str(NOTEBOOK_PATH), mode="exec")
        self.assertEqual(literal_assignment(self.tree, "TEST_EVAL_SEEDS"), (0, 1, 2))
        self.assertEqual(
            literal_assignment(self.tree, "TEST_EVAL_NO_ATTENTION_RUN_ID"),
            "20261014T125621Z_e5d231e1",
        )
        self.assertEqual(
            literal_assignment(self.tree, "TEST_EVAL_FULL_RUN_ID"),
            "20261015T042116Z_d9f514ea",
        )
        self.assertEqual(
            literal_assignment(self.tree, "TEST_EVAL_FULL_CONFIG"),
            "goal_guided_solution_attention_mean_mix_with_goal_and_cross_attention_"
            "learned_temperature_full_goal_attention",
        )

    def test_cell_contains_no_training_or_drive_upload_calls(self):
        forbidden_names = {"train_model", "backward", "step", "zero_grad"}
        forbidden_attributes = {
            "backward",
            "step",
            "zero_grad",
            "create",
            "upload",
        }
        violations = []
        for node in ast.walk(self.tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name) and node.func.id in forbidden_names:
                violations.append(node.func.id)
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr in forbidden_attributes
            ):
                violations.append(node.func.attr)
        self.assertEqual(violations, [])

    def test_checkpoint_filenames_cover_both_models_and_all_three_seeds(self):
        filename_function = load_function(
            self.source,
            "test_eval_checkpoint_filenames",
        )
        no_attention = [filename_function("no_attention", seed) for seed in (0, 1, 2)]
        full = [filename_function("full_model", seed) for seed in (0, 1, 2)]
        self.assertEqual(
            no_attention[0],
            (
                "attention_ablation_20261014T125621Z_e5d231e1_no_attention_seed0.json",
                "attention_ablation_20261014T125621Z_e5d231e1_no_attention_seed0.pt",
            ),
        )
        self.assertEqual(
            full[2],
            (
                "step15e_20261015T042116Z_d9f514ea_"
                "goal_guided_solution_attention_mean_mix_with_goal_and_cross_attention_"
                "learned_temperature_full_goal_attention_seed2.json",
                "step15e_20261015T042116Z_d9f514ea_"
                "goal_guided_solution_attention_mean_mix_with_goal_and_cross_attention_"
                "learned_temperature_full_goal_attention_seed2.pt",
            ),
        )
        self.assertEqual(len(set(no_attention + full)), 6)

    def test_checkpoint_record_rejects_out_of_range_validation_accuracy(self):
        validate_record = load_function(
            self.source,
            "test_eval_validate_record",
            {
                "re": re,
                "TEST_EVAL_NO_ATTENTION_CONFIG": "no_attention",
                "TEST_EVAL_FULL_CONFIG": (
                    "goal_guided_solution_attention_mean_mix_with_goal_and_cross_attention_"
                    "learned_temperature_full_goal_attention"
                ),
                "TEST_EVAL_FULL_RUN_ID": "20261015T042116Z_d9f514ea",
            },
        )
        checkpoint_name = (
            "attention_ablation_20261014T125621Z_e5d231e1_"
            "no_attention_seed0.pt"
        )
        record = {
            "configuration": "no_attention",
            "seed": 0,
            "checkpoint_filename": checkpoint_name,
            "checkpoint_sha256": "0" * 64,
            "best_validation_accuracy": 1.5,
            "cache_spec": {"settings": {}},
        }
        with self.assertRaisesRegex(ValueError, "best_validation_accuracy"):
            validate_record("no_attention", 0, record, checkpoint_name)

    def test_predict_accuracy_batches_all_examples_and_counts_correct_predictions(self):
        predict_accuracy = load_function(
            self.source,
            "test_eval_predict_accuracy",
            {"np": np, "torch": torch},
        )

        class DeterministicModel(torch.nn.Module):
            def forward(self, goal, sol1, sol2):
                del sol1, sol2
                choose_one = goal[:, 0].float()
                logits = torch.stack((1.0 - choose_one, choose_one), dim=1)
                return logits, {}

        goal = np.asarray([[0], [1], [1]], dtype=np.int64)
        sol1 = np.zeros((3, 1), dtype=np.int64)
        sol2 = np.zeros((3, 1), dtype=np.int64)
        labels = np.asarray([0, 1, 0], dtype=np.int64)
        correct, total, accuracy = predict_accuracy(
            DeterministicModel(),
            (goal, sol1, sol2, labels),
            torch.device("cpu"),
            batch_size=2,
        )
        self.assertEqual((correct, total), (2, 3))
        self.assertAlmostEqual(accuracy, 2 / 3)


class TestTestAccuracySummaryTableCell(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = load_table_cell_source()
        cls.tree = ast.parse(cls.source)
        cls.build_table = load_function(cls.source, "build_test_eval_markdown_table")

    def setUp(self):
        self.results_df = pd.DataFrame([
            {"model": "No attention", "seed": 0, "correct": 1074, "total": 1838,
             "test_accuracy": 1074 / 1838},
            {"model": "No attention", "seed": 1, "correct": 1062, "total": 1838,
             "test_accuracy": 1062 / 1838},
            {"model": "No attention", "seed": 2, "correct": 1103, "total": 1838,
             "test_accuracy": 1103 / 1838},
            {"model": "Full model", "seed": 0, "correct": 1134, "total": 1838,
             "test_accuracy": 1134 / 1838},
            {"model": "Full model", "seed": 1, "correct": 1092, "total": 1838,
             "test_accuracy": 1092 / 1838},
            {"model": "Full model", "seed": 2, "correct": 1117, "total": 1838,
             "test_accuracy": 1117 / 1838},
        ])
        self.summary_df = pd.DataFrame([
            {
                "model": "No attention",
                "test_mean": 0.587414,
                "test_sd": 0.009364,
                "seed_accuracies": [0.584331, 0.577802, 0.600109],
            },
            {
                "model": "Full model",
                "test_mean": 0.606275,
                "test_sd": 0.009385,
                "seed_accuracies": [0.616975, 0.594124, 0.607726],
            },
        ])

    def test_builds_step_13e4_style_markdown_table_from_evaluation_results(self):
        markdown = self.build_table(self.results_df, self.summary_df)
        self.assertEqual(
            markdown,
            "\n".join([
                "| model | test mean | population SD | seed accuracies | delta vs No attention |",
                "|:---|---:|---:|:---|---:|",
                "| No attention | 0.5874 | 0.0094 | [0.5843, 0.5778, 0.6001] | +0.0000 |",
                "| Full model | 0.6063 | 0.0094 | [0.6170, 0.5941, 0.6077] | +0.0189 |",
            ]),
        )

    def test_rejects_incomplete_seed_results(self):
        incomplete = self.results_df.loc[
            ~((self.results_df["model"] == "Full model") & (self.results_df["seed"] == 2))
        ]
        with self.assertRaisesRegex(ValueError, "seeds"):
            self.build_table(incomplete, self.summary_df)

    def test_rejects_unexpected_test_set_size(self):
        wrong_total = self.results_df.copy()
        wrong_total.loc[0, "total"] = 1837
        with self.assertRaisesRegex(ValueError, "1,838"):
            self.build_table(wrong_total, self.summary_df)


if __name__ == "__main__":
    unittest.main()
