import os
import tempfile
import unittest
from unittest.mock import patch
from agent_tree import cmd_delete, TreeStore

class TestCmdDelete(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.agents_dir = os.path.join(self.tmpdir, ".claude-agents")
        os.makedirs(self.agents_dir)
        store = TreeStore(self.agents_dir)
        now = "2026-01-01T00:00:00+00:00"
        os.makedirs(os.path.join(self.agents_dir, "parent-1"))
        store.save({
            "version": 1, "objective": "Test", "created": now,
            "agents": {
                "parent-1": {
                    "id": "parent-1", "title": "Parent", "status": "working",
                    "parent": "root", "file": "parent-1/parent-1.md", "created": now,
                    "updated": now, "children": ["child-1"], "tags": [], "blocked_by": None,
                },
                "child-1": {
                    "id": "child-1", "title": "Child", "status": "pending",
                    "parent": "parent-1", "file": "parent-1/child-1.md", "created": now,
                    "updated": now, "children": [], "tags": [], "blocked_by": None,
                },
                "solo": {
                    "id": "solo", "title": "Solo", "status": "pending",
                    "parent": "root", "file": "solo.md", "created": now,
                    "updated": now, "children": [], "tags": [], "blocked_by": None,
                },
            },
            "root_children": ["parent-1", "solo"],
        })
        for fname, content in [
            ("parent-1/parent-1.md", "---\nid: parent-1\n---\n# Parent\n"),
            ("parent-1/child-1.md", "---\nid: child-1\n---\n# Child\n"),
            ("solo.md", "---\nid: solo\n---\n# Solo\n"),
        ]:
            path = os.path.join(self.agents_dir, fname)
            with open(path, "w") as f:
                f.write(content)

    @patch("agent_tree.TreeStore.find_agents_dir")
    def test_delete_leaf_agent(self, mock_find):
        mock_find.return_value = self.agents_dir
        args = type("Args", (), {"id": "solo", "cascade": False})()
        cmd_delete(args)
        store = TreeStore(self.agents_dir)
        data = store.load()
        self.assertNotIn("solo", data["agents"])
        self.assertNotIn("solo", data["root_children"])
        self.assertFalse(os.path.exists(os.path.join(self.agents_dir, "solo.md")))

    @patch("agent_tree.TreeStore.find_agents_dir")
    def test_reject_delete_with_children_no_cascade(self, mock_find):
        mock_find.return_value = self.agents_dir
        args = type("Args", (), {"id": "parent-1", "cascade": False})()
        with self.assertRaises(SystemExit):
            cmd_delete(args)

    @patch("agent_tree.TreeStore.find_agents_dir")
    def test_cascade_deletes_children(self, mock_find):
        mock_find.return_value = self.agents_dir
        args = type("Args", (), {"id": "parent-1", "cascade": True})()
        cmd_delete(args)
        store = TreeStore(self.agents_dir)
        data = store.load()
        self.assertNotIn("parent-1", data["agents"])
        self.assertNotIn("child-1", data["agents"])

    @patch("agent_tree.TreeStore.find_agents_dir")
    def test_delete_child_updates_parent(self, mock_find):
        mock_find.return_value = self.agents_dir
        args = type("Args", (), {"id": "child-1", "cascade": False})()
        cmd_delete(args)
        store = TreeStore(self.agents_dir)
        data = store.load()
        self.assertNotIn("child-1", data["agents"]["parent-1"]["children"])
