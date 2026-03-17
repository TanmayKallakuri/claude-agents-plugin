"""Tests for cmd_init command."""
import sys
import os
import json
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent_tree import cmd_init


class _Args:
    """Minimal args namespace for testing."""
    def __init__(self, objective="Build a webapp", force=False):
        self.objective = objective
        self.force = force


class TestCmdInit(unittest.TestCase):
    def setUp(self):
        self._orig_cwd = os.getcwd()
        self._tmpdir = tempfile.TemporaryDirectory()
        os.chdir(self._tmpdir.name)

    def tearDown(self):
        os.chdir(self._orig_cwd)
        self._tmpdir.cleanup()

    def test_creates_folder_and_files(self):
        cmd_init(_Args(objective="Build a webapp"))
        agents_dir = os.path.join(self._tmpdir.name, ".claude-agents")
        self.assertTrue(os.path.isdir(agents_dir))
        # objective.md
        obj_path = os.path.join(agents_dir, "objective.md")
        self.assertTrue(os.path.isfile(obj_path))
        with open(obj_path) as f:
            content = f.read()
        self.assertIn("# Objective", content)
        self.assertIn("Build a webapp", content)
        # tree.json
        tree_path = os.path.join(agents_dir, "tree.json")
        self.assertTrue(os.path.isfile(tree_path))
        with open(tree_path) as f:
            data = json.load(f)
        self.assertEqual(data["objective"], "Build a webapp")
        self.assertEqual(data["agents"], {})

    def test_fails_if_exists(self):
        cmd_init(_Args(objective="First"))
        with self.assertRaises(SystemExit) as ctx:
            cmd_init(_Args(objective="Second"))
        self.assertEqual(ctx.exception.code, 1)

    def test_force_resets(self):
        cmd_init(_Args(objective="First"))
        agents_dir = os.path.join(self._tmpdir.name, ".claude-agents")
        # Create a marker file
        marker = os.path.join(agents_dir, "marker.txt")
        with open(marker, "w") as f:
            f.write("old")
        cmd_init(_Args(objective="Second", force=True))
        # Marker should be gone
        self.assertFalse(os.path.exists(marker))
        # New objective should be in place
        tree_path = os.path.join(agents_dir, "tree.json")
        with open(tree_path) as f:
            data = json.load(f)
        self.assertEqual(data["objective"], "Second")


if __name__ == "__main__":
    unittest.main()
