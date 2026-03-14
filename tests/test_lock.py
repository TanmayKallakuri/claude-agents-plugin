"""Tests for PID-based file lock."""
import sys
import os
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent_tree import FileLock


class TestFileLock(unittest.TestCase):
    def test_acquire_and_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = os.path.join(tmp, "test.lock")
            lock = FileLock(lock_path)
            lock.acquire()
            self.assertTrue(os.path.exists(lock_path))
            with open(lock_path) as f:
                pid = int(f.read().strip())
            self.assertEqual(pid, os.getpid())
            lock.release()
            self.assertFalse(os.path.exists(lock_path))

    def test_context_manager(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = os.path.join(tmp, "test.lock")
            with FileLock(lock_path) as lock:
                self.assertTrue(os.path.exists(lock_path))
            self.assertFalse(os.path.exists(lock_path))

    def test_stale_lock_broken(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = os.path.join(tmp, "test.lock")
            with open(lock_path, "w") as f:
                f.write("9999999")
            lock = FileLock(lock_path)
            lock.acquire()
            self.assertTrue(os.path.exists(lock_path))
            with open(lock_path) as f:
                pid = int(f.read().strip())
            self.assertEqual(pid, os.getpid())
            lock.release()

    def test_double_acquire_same_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = os.path.join(tmp, "test.lock")
            lock1 = FileLock(lock_path)
            lock1.acquire()
            lock2 = FileLock(lock_path)
            with self.assertRaises(RuntimeError):
                lock2.acquire()
            lock1.release()

    def test_release_nonexistent_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = os.path.join(tmp, "test.lock")
            lock = FileLock(lock_path)
            lock.release()  # Should not raise


if __name__ == "__main__":
    unittest.main()
