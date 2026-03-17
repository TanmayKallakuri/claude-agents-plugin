"""Tests for cmd_spawn command."""
import sys
import os
import json
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent_tree import cmd_init, cmd_spawn, parse_frontmatter


class _InitArgs:
    def __init__(self, objective="Build a webapp", force=False):
        self.objective = objective
        self.force = force


class _SpawnArgs:
    def __init__(self, id, parent="root", title="Task", objective="Do stuff",
                 tags=None, max_agents=50, force=False):
        self.id = id
        self.parent = parent
        self.title = title
        self.objective = objective
        self.tags = tags or []
        self.max_agents = max_agents
        self.force = force


class TestCmdSpawn(unittest.TestCase):
    def setUp(self):
        self._orig_cwd = os.getcwd()
        self._tmpdir = tempfile.TemporaryDirectory()
        os.chdir(self._tmpdir.name)
        cmd_init(_InitArgs())

    def tearDown(self):
        os.chdir(self._orig_cwd)
        self._tmpdir.cleanup()

    def _load_tree(self):
        tree_path = os.path.join(self._tmpdir.name, ".claude-agents", "tree.json")
        with open(tree_path) as f:
            return json.load(f)

    def test_creates_md_and_updates_tree(self):
        cmd_spawn(_SpawnArgs(id="task-1", title="Auth Module", tags=["auth", "backend"]))
        data = self._load_tree()
        self.assertIn("task-1", data["agents"])
        agent = data["agents"]["task-1"]
        self.assertEqual(agent["status"], "pending")
        self.assertEqual(agent["title"], "Auth Module")
        self.assertEqual(agent["tags"], ["auth", "backend"])
        self.assertIsNone(agent["blocked_by"])
        # MD file should exist
        md_path = os.path.join(self._tmpdir.name, ".claude-agents", agent["file"])
        self.assertTrue(os.path.isfile(md_path))
        with open(md_path) as f:
            content = f.read()
        meta, body = parse_frontmatter(content)
        self.assertEqual(meta["id"], "task-1")
        self.assertEqual(meta["tags"], ["auth", "backend"])

    def test_rejects_duplicate_id(self):
        cmd_spawn(_SpawnArgs(id="task-1"))
        with self.assertRaises(SystemExit):
            cmd_spawn(_SpawnArgs(id="task-1"))

    def test_rejects_invalid_parent(self):
        with self.assertRaises(SystemExit):
            cmd_spawn(_SpawnArgs(id="task-1", parent="nonexistent"))

    def test_enforces_max_agents(self):
        # Spawn up to max
        for i in range(3):
            cmd_spawn(_SpawnArgs(id=f"t-{i}", max_agents=3))
        with self.assertRaises(SystemExit):
            cmd_spawn(_SpawnArgs(id="t-overflow", max_agents=3))

    def test_enforces_max_depth(self):
        # Create chain: root -> d1 -> d2 -> d3 -> d4 (depth 4 ok)
        cmd_spawn(_SpawnArgs(id="d1", parent="root"))
        cmd_spawn(_SpawnArgs(id="d2", parent="d1"))
        cmd_spawn(_SpawnArgs(id="d3", parent="d2"))
        cmd_spawn(_SpawnArgs(id="d4", parent="d3"))
        # Depth 5 should fail
        with self.assertRaises(SystemExit):
            cmd_spawn(_SpawnArgs(id="d5", parent="d4"))

    def test_subfolder_move_on_first_child(self):
        cmd_spawn(_SpawnArgs(id="parent-1", parent="root"))
        agents_dir = os.path.join(self._tmpdir.name, ".claude-agents")
        # Initially parent-1.md should be flat
        self.assertTrue(os.path.isfile(os.path.join(agents_dir, "parent-1.md")))

        # Spawn first child - should trigger subfolder move
        cmd_spawn(_SpawnArgs(id="child-1", parent="parent-1"))
        data = self._load_tree()

        # Parent should now be in subfolder
        parent_file = data["agents"]["parent-1"]["file"]
        self.assertEqual(parent_file, "parent-1/parent-1.md")
        self.assertTrue(os.path.isfile(os.path.join(agents_dir, parent_file)))
        # Old flat file should be gone
        self.assertFalse(os.path.isfile(os.path.join(agents_dir, "parent-1.md")))

        # Child should be in parent subfolder
        child_file = data["agents"]["child-1"]["file"]
        self.assertEqual(child_file, "parent-1/child-1.md")
        self.assertTrue(os.path.isfile(os.path.join(agents_dir, child_file)))

    def test_tags_stored_in_tree_json(self):
        cmd_spawn(_SpawnArgs(id="tagged", tags=["api", "v2"]))
        data = self._load_tree()
        self.assertEqual(data["agents"]["tagged"]["tags"], ["api", "v2"])


if __name__ == "__main__":
    unittest.main()
