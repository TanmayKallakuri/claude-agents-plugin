import os
import json
import tempfile
import unittest
from unittest.mock import patch
from agent_tree import cmd_log, TreeStore, parse_frontmatter

class TestCmdLog(unittest.TestCase):
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
                    "id": "task-1", "title": "Task One", "status": "working",
                    "parent": "root", "file": "task-1.md", "created": now,
                    "updated": now, "children": [], "tags": [], "blocked_by": None,
                }
            },
            "root_children": ["task-1"],
        })
        md = (
            "---\nid: task-1\ntitle: Task One\nstatus: working\n"
            "parent: root\ncreated: 2026-01-01T00:00:00+00:00\n"
            "updated: 2026-01-01T00:00:00+00:00\nchildren: []\ntags: []\n"
            "blocked_by: null\n---\n\n# Task One\n\n## Objective\nDo stuff\n\n## Log\n"
        )
        with open(os.path.join(self.agents_dir, "task-1.md"), "w") as f:
            f.write(md)

    @patch("agent_tree.TreeStore.find_agents_dir")
    def test_appends_log_entry(self, mock_find):
        mock_find.return_value = self.agents_dir
        args = type("Args", (), {"id": "task-1", "message": "Started implementation"})()
        cmd_log(args)
        with open(os.path.join(self.agents_dir, "task-1.md")) as f:
            content = f.read()
        self.assertIn("### ", content)
        self.assertIn("Started implementation", content)

    @patch("agent_tree.TreeStore.find_agents_dir")
    def test_updates_timestamp_in_tree(self, mock_find):
        mock_find.return_value = self.agents_dir
        args = type("Args", (), {"id": "task-1", "message": "Progress note"})()
        cmd_log(args)
        store = TreeStore(self.agents_dir)
        data = store.load()
        self.assertNotEqual(data["agents"]["task-1"]["updated"], "2026-01-01T00:00:00+00:00")

    @patch("agent_tree.TreeStore.find_agents_dir")
    def test_updates_timestamp_in_md(self, mock_find):
        mock_find.return_value = self.agents_dir
        args = type("Args", (), {"id": "task-1", "message": "Progress note"})()
        cmd_log(args)
        with open(os.path.join(self.agents_dir, "task-1.md")) as f:
            content = f.read()
        meta, _ = parse_frontmatter(content)
        self.assertNotEqual(meta["updated"], "2026-01-01T00:00:00+00:00")

    @patch("agent_tree.TreeStore.find_agents_dir")
    def test_error_on_missing_agent(self, mock_find):
        mock_find.return_value = self.agents_dir
        args = type("Args", (), {"id": "nonexistent", "message": "Oops"})()
        with self.assertRaises(SystemExit):
            cmd_log(args)
