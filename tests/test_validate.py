import os
import tempfile
import unittest
from unittest.mock import patch
from io import StringIO
from agent_tree import cmd_validate, TreeStore


class TestCmdValidate(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.agents_dir = os.path.join(self.tmpdir, ".claude-agents")
        os.makedirs(self.agents_dir)

    def _make_tree(self, agents_dict, root_children=None):
        store = TreeStore(self.agents_dir)
        now = "2026-01-01T00:00:00+00:00"
        store.save({
            "version": 1, "objective": "Test", "created": now,
            "agents": agents_dict,
            "root_children": root_children or [],
        })

    @patch("sys.stdout", new_callable=StringIO)
    @patch("agent_tree.TreeStore.find_agents_dir")
    def test_valid_tree_passes(self, mock_find, mock_stdout):
        mock_find.return_value = self.agents_dir
        self._make_tree({
            "task-1": {
                "id": "task-1", "title": "T1", "status": "done",
                "parent": "root", "file": "task-1.md", "children": [],
                "tags": [], "blocked_by": None,
            }
        }, ["task-1"])
        with open(os.path.join(self.agents_dir, "task-1.md"), "w") as f:
            f.write("---\nid: task-1\n---\n# T1\n")
        args = type("Args", (), {"id": None})()
        cmd_validate(args)
        output = mock_stdout.getvalue()
        self.assertIn("valid", output.lower())

    @patch("sys.stdout", new_callable=StringIO)
    @patch("agent_tree.TreeStore.find_agents_dir")
    def test_missing_file_reported(self, mock_find, mock_stdout):
        mock_find.return_value = self.agents_dir
        self._make_tree({
            "ghost": {
                "id": "ghost", "title": "Ghost", "status": "pending",
                "parent": "root", "file": "ghost.md", "children": [],
                "tags": [], "blocked_by": None,
            }
        }, ["ghost"])
        args = type("Args", (), {"id": None})()
        cmd_validate(args)
        output = mock_stdout.getvalue()
        self.assertIn("ghost", output)
        self.assertIn("missing", output.lower())

    @patch("sys.stdout", new_callable=StringIO)
    @patch("agent_tree.TreeStore.find_agents_dir")
    def test_orphan_parent_reported(self, mock_find, mock_stdout):
        mock_find.return_value = self.agents_dir
        self._make_tree({
            "orphan": {
                "id": "orphan", "title": "Orphan", "status": "pending",
                "parent": "nonexistent", "file": "orphan.md", "children": [],
                "tags": [], "blocked_by": None,
            }
        })
        with open(os.path.join(self.agents_dir, "orphan.md"), "w") as f:
            f.write("---\nid: orphan\n---\n# Orphan\n")
        args = type("Args", (), {"id": None})()
        cmd_validate(args)
        output = mock_stdout.getvalue()
        self.assertIn("orphan", output.lower())


if __name__ == "__main__":
    unittest.main()
