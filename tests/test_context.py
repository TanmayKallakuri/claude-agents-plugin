import os
import tempfile
import unittest
from unittest.mock import patch
from io import StringIO
from agent_tree import cmd_context, TreeStore

class TestCmdContext(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.agents_dir = os.path.join(self.tmpdir, ".claude-agents")
        os.makedirs(self.agents_dir)
        store = TreeStore(self.agents_dir)
        now = "2026-01-01T00:00:00+00:00"
        store.save({
            "version": 1, "objective": "Build auth", "created": now,
            "agents": {
                "api": {
                    "id": "api", "title": "API Routes", "status": "working",
                    "parent": "root", "file": "api.md", "created": now,
                    "updated": now, "children": ["endpoints"], "tags": ["backend"], "blocked_by": None,
                },
                "endpoints": {
                    "id": "endpoints", "title": "Endpoints", "status": "blocked",
                    "parent": "api", "file": "api/endpoints.md", "created": now,
                    "updated": now, "children": [], "tags": [], "blocked_by": "db",
                },
                "db": {
                    "id": "db", "title": "Database", "status": "working",
                    "parent": "root", "file": "db.md", "created": now,
                    "updated": now, "children": [], "tags": ["backend"], "blocked_by": None,
                },
            },
            "root_children": ["api", "db"],
        })

    @patch("sys.stdout", new_callable=StringIO)
    @patch("agent_tree.TreeStore.find_agents_dir")
    def test_shows_parent_chain(self, mock_find, mock_stdout):
        mock_find.return_value = self.agents_dir
        args = type("Args", (), {"id": "endpoints"})()
        cmd_context(args)
        output = mock_stdout.getvalue()
        self.assertIn("api", output)
        self.assertIn("Build auth", output)

    @patch("sys.stdout", new_callable=StringIO)
    @patch("agent_tree.TreeStore.find_agents_dir")
    def test_shows_blocker(self, mock_find, mock_stdout):
        mock_find.return_value = self.agents_dir
        args = type("Args", (), {"id": "endpoints"})()
        cmd_context(args)
        output = mock_stdout.getvalue()
        self.assertIn("db", output)
        self.assertIn("blocked", output.lower())

    @patch("sys.stdout", new_callable=StringIO)
    @patch("agent_tree.TreeStore.find_agents_dir")
    def test_shows_children(self, mock_find, mock_stdout):
        mock_find.return_value = self.agents_dir
        args = type("Args", (), {"id": "api"})()
        cmd_context(args)
        output = mock_stdout.getvalue()
        self.assertIn("endpoints", output)
