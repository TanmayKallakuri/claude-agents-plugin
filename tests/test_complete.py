import os
import tempfile
import unittest
from unittest.mock import patch
from agent_tree import cmd_complete, TreeStore, parse_frontmatter

class TestCmdComplete(unittest.TestCase):
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
            "---\nid: task-1\ntitle: Task One\nstatus: working\nparent: root\n"
            "created: 2026-01-01T00:00:00+00:00\nupdated: 2026-01-01T00:00:00+00:00\n"
            "children: []\ntags: []\nblocked_by: null\n---\n\n# Task One\n\n## Objective\nDo stuff\n\n## Log\n"
        )
        with open(os.path.join(self.agents_dir, "task-1.md"), "w") as f:
            f.write(md)

    @patch("agent_tree.TreeStore.find_agents_dir")
    def test_sets_status_done(self, mock_find):
        mock_find.return_value = self.agents_dir
        args = type("Args", (), {"id": "task-1", "summary": "All done"})()
        cmd_complete(args)
        store = TreeStore(self.agents_dir)
        data = store.load()
        self.assertEqual(data["agents"]["task-1"]["status"], "done")

    @patch("agent_tree.TreeStore.find_agents_dir")
    def test_appends_summary_to_log(self, mock_find):
        mock_find.return_value = self.agents_dir
        args = type("Args", (), {"id": "task-1", "summary": "Finished the auth module"})()
        cmd_complete(args)
        with open(os.path.join(self.agents_dir, "task-1.md")) as f:
            content = f.read()
        self.assertIn("Finished the auth module", content)
        self.assertIn("DONE", content)

    @patch("agent_tree.TreeStore.find_agents_dir")
    def test_md_frontmatter_status_done(self, mock_find):
        mock_find.return_value = self.agents_dir
        args = type("Args", (), {"id": "task-1", "summary": "Done"})()
        cmd_complete(args)
        with open(os.path.join(self.agents_dir, "task-1.md")) as f:
            meta, _ = parse_frontmatter(f.read())
        self.assertEqual(meta["status"], "done")
