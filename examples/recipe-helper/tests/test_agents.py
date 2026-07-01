"""Recipe helper agent 骨架的最小单测(0 依赖,跑起来证明 wiring 通)。"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents import Dish, RecipeState, search_node, recipe_node, nutrition_node


class RecipeSkeletonTest(unittest.TestCase):
    def test_search_creates_candidates(self):
        state = RecipeState(input_text="土豆 牛肉")
        out = search_node(state)
        self.assertGreater(len(out["items"]), 0)
        self.assertTrue(all(isinstance(d, Dish) for d in out["items"]))

    def test_recipe_fills_steps(self):
        state = RecipeState(input_text="x", items=[Dish(name="a", verdict="keep")])
        out = recipe_node(state)
        self.assertIsNotNone(out["items"][0].recipe)
        self.assertEqual(out["items"][0].difficulty, 3)

    def test_nutrition_writes_summary(self):
        state = RecipeState(input_text="x", items=[
            Dish(name="炒饭", verdict="keep", difficulty=2),
            Dish(name="番茄蛋汤", verdict="skip"),
        ])
        out = nutrition_node(state)
        self.assertIn("炒饭", out["travelogue_md"])
        self.assertNotIn("番茄蛋汤", out["travelogue_md"])  # skip 不出现在总结


if __name__ == "__main__":
    unittest.main()
