"""Tests for cmd_status command."""
import sys
import os
import json
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent_tree import cmd_init, cmd_spawn, cmd_status, parse_frontmatter


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


class _StatusArgs:
    def __init__(self, id, new_status, blocked_by=None):
        self.id = id
        self.new_status = new_status
        self.blocked_by = blocked_by


class TestCmdStatus(unittest.TestCase):
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

    def test_updates_md_and_tree(self):
        cmd_spawn(_SpawnArgs(id="task-1"))
        cmd_status(_StatusArgs(id="task-1", new_status="working"))
        data = self._load_tree()
        self.assertEqual(data["agents"]["task-1"]["status"], "working")
        # Check MD
        agents_dir = os.path.join(self._tmpdir.name, ".claude-agents")
        md_path = os.path.join(agents_dir, data["agents"]["task-1"]["file"])
        with open(md_path) as f:
            meta, _ = parse_frontmatter(f.read())
        self.assertEqual(meta["status"], "working")

    def test_blocked_requires_blocked_by(self):
        cmd_spawn(_SpawnArgs(id="task-1"))
        with self.assertRaises(SystemExit):
            cmd_status(_StatusArgs(id="task-1", new_status="blocked"))

    def test_blocked_stores_blocked_by(self):
        cmd_spawn(_SpawnArgs(id="task-a"))
        cmd_spawn(_SpawnArgs(id="task-b"))
        cmd_status(_StatusArgs(id="task-a", new_status="blocked", blocked_by="task-b"))
        data = self._load_tree()
        self.assertEqual(data["agents"]["task-a"]["blocked_by"], "task-b")
        # Check MD
        agents_dir = os.path.join(self._tmpdir.name, ".claude-agents")
        md_path = os.path.join(agents_dir, data["agents"]["task-a"]["file"])
        with open(md_path) as f:
            meta, _ = parse_frontmatter(f.read())
        self.assertEqual(meta["blocked_by"], "task-b")

    def test_rejects_direct_circular(self):
        """A blocked by B, then B blocked by A should fail."""
        cmd_spawn(_SpawnArgs(id="a"))
        cmd_spawn(_SpawnArgs(id="b"))
        cmd_status(_StatusArgs(id="a", new_status="blocked", blocked_by="b"))
        with self.assertRaises(SystemExit):
            cmd_status(_StatusArgs(id="b", new_status="blocked", blocked_by="a"))

    def test_rejects_transitive_circular(self):
        """A blocked by B, B blocked by C, C blocked by A should fail."""
        cmd_spawn(_SpawnArgs(id="a"))
        cmd_spawn(_SpawnArgs(id="b"))
        cmd_spawn(_SpawnArgs(id="c"))
        cmd_status(_StatusArgs(id="a", new_status="blocked", blocked_by="b"))
        cmd_status(_StatusArgs(id="b", new_status="blocked", blocked_by="c"))
        with self.assertRaises(SystemExit):
            cmd_status(_StatusArgs(id="c", new_status="blocked", blocked_by="a"))

    def test_clearing_blocked_status(self):
        cmd_spawn(_SpawnArgs(id="task-a"))
        cmd_spawn(_SpawnArgs(id="task-b"))
        cmd_status(_StatusArgs(id="task-a", new_status="blocked", blocked_by="task-b"))
        cmd_status(_StatusArgs(id="task-a", new_status="working"))
        data = self._load_tree()
        self.assertIsNone(data["agents"]["task-a"]["blocked_by"])


if __name__ == "__main__":
    unittest.main()
