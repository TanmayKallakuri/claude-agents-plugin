import os
import tempfile
import unittest
from unittest.mock import patch
from io import StringIO
from agent_tree import cmd_sync, TreeStore, write_frontmatter


class TestCmdSync(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.agents_dir = os.path.join(self.tmpdir, ".claude-agents")
        os.makedirs(self.agents_dir)

    @patch("sys.stdout", new_callable=StringIO)
    @patch("agent_tree.TreeStore.find_agents_dir")
    def test_removes_entries_for_deleted_files(self, mock_find, mock_stdout):
        mock_find.return_value = self.agents_dir
        store = TreeStore(self.agents_dir)
        now = "2026-01-01T00:00:00+00:00"
        store.save({
            "version": 1, "objective": "Test", "created": now,
            "agents": {
                "exists": {
                    "id": "exists", "title": "Exists", "status": "working",
                    "parent": "root", "file": "exists.md", "children": [],
                    "tags": [], "blocked_by": None,
                },
                "gone": {
                    "id": "gone", "title": "Gone", "status": "working",
                    "parent": "root", "file": "gone.md", "children": [],
                    "tags": [], "blocked_by": None,
                },
            },
            "root_children": ["exists", "gone"],
        })
        meta = {"id": "exists", "title": "Exists", "status": "working", "parent": "root"}
        with open(os.path.join(self.agents_dir, "exists.md"), "w") as f:
            f.write(write_frontmatter(meta, "\n# Exists\n"))

        args = type("Args", (), {})()
        cmd_sync(args)

        data = store.load()
        self.assertIn("exists", data["agents"])
        self.assertNotIn("gone", data["agents"])
        output = mock_stdout.getvalue()
        self.assertIn("gone", output)

    @patch("sys.stdout", new_callable=StringIO)
    @patch("agent_tree.TreeStore.find_agents_dir")
    def test_syncs_status_from_md(self, mock_find, mock_stdout):
        mock_find.return_value = self.agents_dir
        store = TreeStore(self.agents_dir)
        now = "2026-01-01T00:00:00+00:00"
        store.save({
            "version": 1, "objective": "Test", "created": now,
            "agents": {
                "task-1": {
                    "id": "task-1", "title": "T1", "status": "pending",
                    "parent": "root", "file": "task-1.md", "children": [],
                    "tags": [], "blocked_by": None,
                },
            },
            "root_children": ["task-1"],
        })
        meta = {"id": "task-1", "title": "T1", "status": "done", "parent": "root"}
        with open(os.path.join(self.agents_dir, "task-1.md"), "w") as f:
            f.write(write_frontmatter(meta, "\n# T1\n"))

        args = type("Args", (), {})()
        cmd_sync(args)

        data = store.load()
        self.assertEqual(data["agents"]["task-1"]["status"], "done")


if __name__ == "__main__":
    unittest.main()
