"""Tests for cmd_tree command."""
import sys
import os
import json
import tempfile
import unittest
from io import StringIO

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent_tree import cmd_init, cmd_spawn, cmd_tree, parse_frontmatter, write_frontmatter


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


class _TreeArgs:
    def __init__(self, verbose=False, tag=None):
        self.verbose = verbose
        self.tag = tag


class TestCmdTree(unittest.TestCase):
    def setUp(self):
        self._orig_cwd = os.getcwd()
        self._tmpdir = tempfile.TemporaryDirectory()
        os.chdir(self._tmpdir.name)
        cmd_init(_InitArgs(objective="Build a webapp"))

    def tearDown(self):
        os.chdir(self._orig_cwd)
        self._tmpdir.cleanup()

    def _capture_tree(self, args):
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            cmd_tree(args)
            return sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout

    def test_tree_shows_objective_and_agents(self):
        cmd_spawn(_SpawnArgs(id="task-1", title="Auth"))
        cmd_spawn(_SpawnArgs(id="task-2", title="API"))
        output = self._capture_tree(_TreeArgs())
        self.assertIn("Build a webapp", output)
        self.assertIn("[objective]", output)
        self.assertIn("task-1", output)
        self.assertIn("task-2", output)
        # Box chars
        self.assertTrue(
            any(c in output for c in ["├── ", "└── "])
        )

    def test_tree_tag_filtering(self):
        cmd_spawn(_SpawnArgs(id="task-1", title="Auth", tags=["auth"]))
        cmd_spawn(_SpawnArgs(id="task-2", title="API", tags=["api"]))
        output = self._capture_tree(_TreeArgs(tag="auth"))
        self.assertIn("task-1", output)
        self.assertNotIn("task-2", output)

    def test_tree_verbose_shows_log(self):
        cmd_spawn(_SpawnArgs(id="task-1", title="Auth", objective="Implement auth"))
        # Manually append a log entry to the MD file
        agents_dir = os.path.join(self._tmpdir.name, ".claude-agents")
        tree_path = os.path.join(agents_dir, "tree.json")
        with open(tree_path) as f:
            data = json.load(f)
        md_path = os.path.join(agents_dir, data["agents"]["task-1"]["file"])
        with open(md_path) as f:
            content = f.read()
        content += "\n### 2026-01-01 Progress\nDid some work on auth\n"
        with open(md_path, "w") as f:
            f.write(content)
        output = self._capture_tree(_TreeArgs(verbose=True))
        self.assertIn("task-1", output)
        self.assertIn("Did some work on auth", output)

    def test_tree_with_children(self):
        cmd_spawn(_SpawnArgs(id="parent", title="Parent Task"))
        cmd_spawn(_SpawnArgs(id="child", parent="parent", title="Child Task"))
        output = self._capture_tree(_TreeArgs())
        self.assertIn("parent", output)
        self.assertIn("child", output)


if __name__ == "__main__":
    unittest.main()
