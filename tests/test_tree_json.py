"""Tests for TreeStore class."""
import sys
import os
import json
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent_tree import TreeStore


class TestTreeStore(unittest.TestCase):
    def test_create_new_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            agents_dir = os.path.join(tmp, ".claude-agents")
            os.makedirs(agents_dir)
            store = TreeStore(agents_dir)
            store.create("Build the app")
            data = store.load()
            self.assertEqual(data["version"], 1)
            self.assertEqual(data["objective"], "Build the app")
            self.assertEqual(data["agents"], {})
            self.assertIn("created", data)

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            agents_dir = os.path.join(tmp, ".claude-agents")
            os.makedirs(agents_dir)
            store = TreeStore(agents_dir)
            tree_data = {
                "version": 1,
                "objective": "Test",
                "created": "2026-01-01T00:00:00Z",
                "agents": {"task-1": {"title": "First Task"}},
            }
            store.save(tree_data)
            loaded = store.load()
            self.assertEqual(loaded["agents"]["task-1"]["title"], "First Task")

    def test_find_agents_dir_current(self):
        with tempfile.TemporaryDirectory() as tmp:
            agents_dir = os.path.join(tmp, ".claude-agents")
            os.makedirs(agents_dir)
            found = TreeStore.find_agents_dir(tmp)
            self.assertIsNotNone(found)
            self.assertTrue(found.endswith(".claude-agents"))

    def test_find_agents_dir_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            agents_dir = os.path.join(tmp, ".claude-agents")
            os.makedirs(agents_dir)
            child = os.path.join(tmp, "sub", "deep")
            os.makedirs(child)
            found = TreeStore.find_agents_dir(child)
            self.assertIsNotNone(found)
            self.assertTrue(found.endswith(".claude-agents"))

    def test_find_agents_dir_not_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            found = TreeStore.find_agents_dir(tmp)
            self.assertIsNone(found)

    def test_posix_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            agents_dir = os.path.join(tmp, ".claude-agents")
            os.makedirs(agents_dir)
            store = TreeStore(agents_dir)
            tree_data = {
                "version": 1,
                "objective": "Test",
                "created": "2026-01-01T00:00:00Z",
                "agents": {
                    "task-1": {"file": "some\\path\\to\\file.md"},
                },
            }
            store.save(tree_data)
            loaded = store.load()
            self.assertEqual(
                loaded["agents"]["task-1"]["file"], "some/path/to/file.md"
            )

    def test_version_check_current(self):
        with tempfile.TemporaryDirectory() as tmp:
            agents_dir = os.path.join(tmp, ".claude-agents")
            os.makedirs(agents_dir)
            store = TreeStore(agents_dir)
            store.create("Test")
            data = store.load()
            self.assertEqual(data["version"], 1)

    def test_version_check_newer_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            agents_dir = os.path.join(tmp, ".claude-agents")
            os.makedirs(agents_dir)
            store = TreeStore(agents_dir)
            tree_data = {
                "version": 999,
                "objective": "Test",
                "created": "2026-01-01T00:00:00Z",
                "agents": {},
            }
            with open(store.tree_path, "w") as f:
                json.dump(tree_data, f)
            with self.assertRaises(SystemExit):
                store.load()


if __name__ == "__main__":
    unittest.main()
