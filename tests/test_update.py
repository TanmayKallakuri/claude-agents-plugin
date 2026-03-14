import os
import json
import tempfile
import unittest
from unittest.mock import patch
from agent_tree import cmd_update, TreeStore, parse_frontmatter

class TestCmdUpdate(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.agents_dir = os.path.join(self.tmpdir, ".claude-agents")
        os.makedirs(self.agents_dir)
        store = TreeStore(self.agents_dir)
        now = "2026-01-01T00:00:00+00:00"
        store.save({
            "version": 1, "objective": "Test", "created": now,
            "agents": {
                "task-1": {
                    "id": "task-1", "title": "Old Title", "status": "pending",
                    "parent": "root", "file": "task-1.md", "created": now,
                    "updated": now, "children": [], "tags": ["old"], "blocked_by": None,
                }
            },
            "root_children": ["task-1"],
        })
        md = (
            "---\nid: task-1\ntitle: Old Title\nstatus: pending\nparent: root\n"
            "created: 2026-01-01T00:00:00+00:00\nupdated: 2026-01-01T00:00:00+00:00\n"
            "children: []\ntags: [old]\nblocked_by: null\n---\n\n# Old Title\n\n## Objective\nOld objective\n\n## Log\n"
        )
        with open(os.path.join(self.agents_dir, "task-1.md"), "w") as f:
            f.write(md)

    @patch("agent_tree.TreeStore.find_agents_dir")
    def test_update_title(self, mock_find):
        mock_find.return_value = self.agents_dir
        args = type("Args", (), {"id": "task-1", "title": "New Title", "objective": None, "tags": None})()
        cmd_update(args)
        store = TreeStore(self.agents_dir)
        data = store.load()
        self.assertEqual(data["agents"]["task-1"]["title"], "New Title")
        with open(os.path.join(self.agents_dir, "task-1.md")) as f:
            meta, _ = parse_frontmatter(f.read())
        self.assertEqual(meta["title"], "New Title")

    @patch("agent_tree.TreeStore.find_agents_dir")
    def test_update_tags(self, mock_find):
        mock_find.return_value = self.agents_dir
        args = type("Args", (), {"id": "task-1", "title": None, "objective": None, "tags": ["new", "updated"]})()
        cmd_update(args)
        store = TreeStore(self.agents_dir)
        data = store.load()
        self.assertEqual(data["agents"]["task-1"]["tags"], ["new", "updated"])

    @patch("agent_tree.TreeStore.find_agents_dir")
    def test_update_nothing_exits(self, mock_find):
        mock_find.return_value = self.agents_dir
        args = type("Args", (), {"id": "task-1", "title": None, "objective": None, "tags": None})()
        with self.assertRaises(SystemExit):
            cmd_update(args)

    @patch("agent_tree.TreeStore.find_agents_dir")
    def test_error_on_missing_agent(self, mock_find):
        mock_find.return_value = self.agents_dir
        args = type("Args", (), {"id": "nope", "title": "X", "objective": None, "tags": None})()
        with self.assertRaises(SystemExit):
            cmd_update(args)
