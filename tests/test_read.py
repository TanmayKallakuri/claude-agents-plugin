"""Tests for cmd_read command."""
import sys
import os
import tempfile
import unittest
from io import StringIO

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent_tree import cmd_init, cmd_spawn, cmd_read


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


class _ReadArgs:
    def __init__(self, id):
        self.id = id


class TestCmdRead(unittest.TestCase):
    def setUp(self):
        self._orig_cwd = os.getcwd()
        self._tmpdir = tempfile.TemporaryDirectory()
        os.chdir(self._tmpdir.name)
        cmd_init(_InitArgs())

    def tearDown(self):
        os.chdir(self._orig_cwd)
        self._tmpdir.cleanup()

    def test_outputs_md_content(self):
        cmd_spawn(_SpawnArgs(id="task-1", title="Auth Module", objective="Implement auth"))
        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            cmd_read(_ReadArgs(id="task-1"))
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        self.assertIn("task-1", output)
        self.assertIn("Auth Module", output)
        self.assertIn("Implement auth", output)

    def test_error_on_missing_agent(self):
        with self.assertRaises(SystemExit):
            cmd_read(_ReadArgs(id="nonexistent"))


if __name__ == "__main__":
    unittest.main()
