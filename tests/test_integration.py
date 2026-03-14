"""End-to-end integration test: init → spawn → log → status → complete → tree → delete."""
import os
import subprocess
import sys
import tempfile
import unittest

AGENT_TREE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "agent_tree.py")

class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def _run(self, *cli_args):
        result = subprocess.run(
            [sys.executable, AGENT_TREE] + list(cli_args),
            capture_output=True, text=True, cwd=self.tmpdir,
        )
        return result

    def test_full_workflow(self):
        # Init
        r = self._run("init", "Build auth system")
        self.assertEqual(r.returncode, 0)
        self.assertIn("Initialized", r.stdout)

        # Spawn two root agents
        r = self._run("spawn", "auth-api", "--parent", "root", "--title", "Auth API", "--objective", "Build endpoints", "--tags", "backend")
        self.assertEqual(r.returncode, 0)

        r = self._run("spawn", "auth-db", "--parent", "root", "--title", "Auth DB", "--objective", "Design schema", "--tags", "backend", "db")
        self.assertEqual(r.returncode, 0)

        # Spawn child under auth-api
        r = self._run("spawn", "login-endpoint", "--parent", "auth-api", "--title", "Login Endpoint", "--objective", "POST /login")
        self.assertEqual(r.returncode, 0)

        # Set status
        r = self._run("status", "auth-api", "working")
        self.assertEqual(r.returncode, 0)

        # Block login-endpoint on auth-db
        r = self._run("status", "login-endpoint", "blocked", "--blocked-by", "auth-db")
        self.assertEqual(r.returncode, 0)

        # Log progress
        r = self._run("log", "auth-db", "Created users table")
        self.assertEqual(r.returncode, 0)

        # Read agent
        r = self._run("read", "auth-db")
        self.assertEqual(r.returncode, 0)
        self.assertIn("Auth DB", r.stdout)

        # Tree
        r = self._run("tree")
        self.assertEqual(r.returncode, 0)
        self.assertIn("auth-api", r.stdout)
        self.assertIn("auth-db", r.stdout)
        self.assertIn("login-endpoint", r.stdout)

        # Verbose tree
        r = self._run("tree", "--verbose")
        self.assertEqual(r.returncode, 0)
        self.assertIn("Created users table", r.stdout)

        # Context
        r = self._run("context", "login-endpoint")
        self.assertEqual(r.returncode, 0)
        self.assertIn("auth-api", r.stdout)
        self.assertIn("auth-db", r.stdout)

        # Complete auth-db
        r = self._run("complete", "auth-db", "--summary", "Schema deployed")
        self.assertEqual(r.returncode, 0)

        # Unblock login-endpoint
        r = self._run("status", "login-endpoint", "working")
        self.assertEqual(r.returncode, 0)

        # Complete login-endpoint
        r = self._run("complete", "login-endpoint", "--summary", "Endpoint working")
        self.assertEqual(r.returncode, 0)

        # Update auth-api
        r = self._run("update", "auth-api", "--title", "Auth API v2")
        self.assertEqual(r.returncode, 0)

        # Validate
        r = self._run("validate")
        self.assertEqual(r.returncode, 0)
        self.assertIn("valid", r.stdout.lower())

        # Sync
        r = self._run("sync")
        self.assertEqual(r.returncode, 0)

        # Delete with cascade
        r = self._run("delete", "auth-api", "--cascade")
        self.assertEqual(r.returncode, 0)
        self.assertIn("Deleted", r.stdout)

        # Verify deletion
        r = self._run("tree")
        self.assertEqual(r.returncode, 0)
        self.assertNotIn("auth-api", r.stdout)
        self.assertNotIn("login-endpoint", r.stdout)
        self.assertIn("auth-db", r.stdout)

    def test_fail_workflow(self):
        self._run("init", "Test project")
        self._run("spawn", "flaky", "--parent", "root", "--title", "Flaky Task", "--objective", "Might fail")
        r = self._run("fail", "flaky", "--reason", "External API down")
        self.assertEqual(r.returncode, 0)
        r = self._run("read", "flaky")
        self.assertIn("FAILED", r.stdout)
        self.assertIn("External API down", r.stdout)

if __name__ == "__main__":
    unittest.main()
