"""Stress tests for agent_tree.py — edge cases, scale, and adversarial inputs."""
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent_tree import (
    TreeStore,
    _validate_agent_id,
    cmd_complete,
    cmd_context,
    cmd_delete,
    cmd_fail,
    cmd_init,
    cmd_log,
    cmd_read,
    cmd_spawn,
    cmd_status,
    cmd_sync,
    cmd_tree,
    cmd_update,
    cmd_validate,
    parse_frontmatter,
    write_frontmatter,
)


# ---------------------------------------------------------------------------
# Arg helpers
# ---------------------------------------------------------------------------

class _InitArgs:
    def __init__(self, objective="Stress test", force=False):
        self.objective = objective
        self.force = force


class _SpawnArgs:
    def __init__(self, id, parent="root", title="Task", objective="Do stuff",
                 tags=None, max_agents=200, force=False):
        self.id = id
        self.parent = parent
        self.title = title
        self.objective = objective
        self.tags = tags or []
        self.max_agents = max_agents
        self.force = force


class _StatusArgs:
    def __init__(self, id, new_status, blocked_by=None):
        self.id = id
        self.new_status = new_status
        self.blocked_by = blocked_by


class _LogArgs:
    def __init__(self, id, message):
        self.id = id
        self.message = message


class _UpdateArgs:
    def __init__(self, id, title=None, objective=None, tags=None):
        self.id = id
        self.title = title
        self.objective = objective
        self.tags = tags


class _CompleteArgs:
    def __init__(self, id, summary="Done"):
        self.id = id
        self.summary = summary


class _FailArgs:
    def __init__(self, id, reason="Failed"):
        self.id = id
        self.reason = reason


class _DeleteArgs:
    def __init__(self, id, cascade=False):
        self.id = id
        self.cascade = cascade


class _ReadArgs:
    def __init__(self, id):
        self.id = id


class _TreeArgs:
    def __init__(self, verbose=False, tag=None):
        self.verbose = verbose
        self.tag = tag


class _ContextArgs:
    def __init__(self, id):
        self.id = id


class _ValidateArgs:
    def __init__(self, id=None):
        self.id = id


class _SyncArgs:
    pass


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class StressTestBase(unittest.TestCase):
    def setUp(self):
        self._orig_cwd = os.getcwd()
        self._tmpdir = tempfile.TemporaryDirectory()
        os.chdir(self._tmpdir.name)
        cmd_init(_InitArgs())

    def tearDown(self):
        os.chdir(self._orig_cwd)
        self._tmpdir.cleanup()

    def _load_tree(self):
        tree_path = os.path.join(self._tmpdir.name, ".claude-agents", "tree.json")
        with open(tree_path) as f:
            return json.load(f)

    @property
    def _agents_dir(self):
        return os.path.join(self._tmpdir.name, ".claude-agents")


# ===========================================================================
# 1. SCALE: Many agents
# ===========================================================================

class TestScaleManyAgents(StressTestBase):
    """Spawn large numbers of agents and verify tree integrity."""

    def test_50_root_agents(self):
        """Spawn 50 root-level agents and verify all exist."""
        for i in range(50):
            cmd_spawn(_SpawnArgs(id=f"agent-{i:03d}", title=f"Agent {i}"))

        data = self._load_tree()
        self.assertEqual(len(data["agents"]), 50)
        self.assertEqual(len(data["root_children"]), 50)

        # Validate tree integrity
        cmd_validate(_ValidateArgs())

    def test_wide_tree_20_children_per_parent(self):
        """One parent with 20 children."""
        cmd_spawn(_SpawnArgs(id="parent"))
        for i in range(20):
            cmd_spawn(_SpawnArgs(id=f"child-{i}", parent="parent", title=f"Child {i}"))

        data = self._load_tree()
        self.assertEqual(len(data["agents"]["parent"]["children"]), 20)
        # Parent should be in subfolder
        self.assertIn("/", data["agents"]["parent"]["file"])

    def test_max_depth_chain(self):
        """Build maximum depth chain (4 levels) and verify depth limit."""
        ids = ["d1", "d2", "d3", "d4"]
        for i, agent_id in enumerate(ids):
            parent = "root" if i == 0 else ids[i - 1]
            cmd_spawn(_SpawnArgs(id=agent_id, parent=parent))

        # Depth 5 should fail
        with self.assertRaises(SystemExit):
            cmd_spawn(_SpawnArgs(id="d5", parent="d4"))

        # But with --force it should work
        cmd_spawn(_SpawnArgs(id="d5", parent="d4", force=True))
        data = self._load_tree()
        self.assertIn("d5", data["agents"])

    def test_bushy_tree_mixed_depths(self):
        """Create a complex tree: 3 root agents, each with 5 children, each child with 3 grandchildren."""
        for r in range(3):
            rid = f"root-{r}"
            cmd_spawn(_SpawnArgs(id=rid))
            for c in range(5):
                cid = f"root-{r}-child-{c}"
                cmd_spawn(_SpawnArgs(id=cid, parent=rid))
                for g in range(3):
                    gid = f"root-{r}-child-{c}-gc-{g}"
                    cmd_spawn(_SpawnArgs(id=gid, parent=cid))

        data = self._load_tree()
        # 3 + 15 + 45 = 63 agents
        self.assertEqual(len(data["agents"]), 63)
        cmd_validate(_ValidateArgs())

    def test_max_agents_limit_enforced(self):
        """Verify max_agents limit prevents excessive spawning."""
        for i in range(10):
            cmd_spawn(_SpawnArgs(id=f"a-{i}", max_agents=10))
        with self.assertRaises(SystemExit):
            cmd_spawn(_SpawnArgs(id="overflow", max_agents=10))


# ===========================================================================
# 2. EDGE CASE IDs AND STRINGS
# ===========================================================================

class TestEdgeCaseStrings(StressTestBase):
    """IDs, titles, and objectives with tricky characters."""

    def test_hyphenated_ids(self):
        cmd_spawn(_SpawnArgs(id="my-complex-agent-id-with-many-hyphens"))
        data = self._load_tree()
        self.assertIn("my-complex-agent-id-with-many-hyphens", data["agents"])

    def test_numeric_id(self):
        cmd_spawn(_SpawnArgs(id="123"))
        data = self._load_tree()
        self.assertIn("123", data["agents"])

    def test_underscore_id(self):
        cmd_spawn(_SpawnArgs(id="my_agent_v2"))
        data = self._load_tree()
        self.assertIn("my_agent_v2", data["agents"])

    def test_dotted_id(self):
        cmd_spawn(_SpawnArgs(id="v1.0.0"))
        data = self._load_tree()
        self.assertIn("v1.0.0", data["agents"])

    def test_title_with_special_yaml_chars(self):
        """Title with colons, brackets, hashes — YAML-hostile."""
        title = "Auth: OAuth [v2] #priority"
        cmd_spawn(_SpawnArgs(id="special-title", title=title))

        # Read back and verify roundtrip
        data = self._load_tree()
        md_path = os.path.join(self._agents_dir, data["agents"]["special-title"]["file"])
        with open(md_path) as f:
            meta, _ = parse_frontmatter(f.read())
        self.assertEqual(meta["title"], title)

    def test_objective_with_markdown(self):
        """Objective containing markdown formatting."""
        obj = "Build **bold** and _italic_ endpoints with `code`"
        cmd_spawn(_SpawnArgs(id="md-obj", objective=obj))
        cmd_read(_ReadArgs(id="md-obj"))  # should not crash

    def test_log_message_with_markdown_headings(self):
        """Log message with ### heading — could confuse log parser."""
        cmd_spawn(_SpawnArgs(id="log-test"))
        cmd_log(_LogArgs(id="log-test", message="### This looks like a heading\nBut it's a log"))
        cmd_log(_LogArgs(id="log-test", message="Normal log after"))

        # Tree verbose should still work
        cmd_tree(_TreeArgs(verbose=True))

    def test_log_message_with_frontmatter_delimiter(self):
        """Log message containing --- which is a frontmatter delimiter."""
        cmd_spawn(_SpawnArgs(id="delim-test"))
        cmd_log(_LogArgs(id="delim-test", message="before\n---\nafter"))

        # Should still parse correctly
        md_path = os.path.join(self._agents_dir, "delim-test.md")
        with open(md_path) as f:
            meta, body = parse_frontmatter(f.read())
        self.assertEqual(meta["id"], "delim-test")
        self.assertIn("before", body)
        self.assertIn("after", body)

    def test_empty_tags_list(self):
        cmd_spawn(_SpawnArgs(id="no-tags", tags=[]))
        data = self._load_tree()
        self.assertEqual(data["agents"]["no-tags"]["tags"], [])

    def test_many_tags(self):
        tags = [f"tag-{i}" for i in range(20)]
        cmd_spawn(_SpawnArgs(id="many-tags", tags=tags))
        data = self._load_tree()
        self.assertEqual(len(data["agents"]["many-tags"]["tags"]), 20)

    def test_very_long_title(self):
        title = "A" * 500
        cmd_spawn(_SpawnArgs(id="long-title", title=title))
        data = self._load_tree()
        self.assertEqual(data["agents"]["long-title"]["title"], title)

    def test_very_long_objective(self):
        obj = "word " * 1000
        cmd_spawn(_SpawnArgs(id="long-obj", objective=obj))
        cmd_read(_ReadArgs(id="long-obj"))  # should not crash

    def test_very_long_log_message(self):
        cmd_spawn(_SpawnArgs(id="long-log"))
        msg = "Log line. " * 500
        cmd_log(_LogArgs(id="long-log", message=msg))
        cmd_tree(_TreeArgs(verbose=True))


# ===========================================================================
# 3. FRONTMATTER PARSER ADVERSARIAL
# ===========================================================================

class TestFrontmatterAdversarial(unittest.TestCase):
    """Adversarial inputs for the YAML frontmatter parser."""

    def test_empty_string(self):
        meta, body = parse_frontmatter("")
        self.assertEqual(meta, {})
        self.assertEqual(body, "")

    def test_only_delimiters(self):
        meta, body = parse_frontmatter("---\n---")
        self.assertEqual(meta, {})
        self.assertEqual(body, "")

    def test_unclosed_frontmatter(self):
        text = "---\nid: test\ntitle: Unclosed"
        meta, body = parse_frontmatter(text)
        # Should treat as no frontmatter since closing --- is missing
        self.assertEqual(meta, {})
        self.assertEqual(body, text)

    def test_multiple_colons_in_value(self):
        text = '---\ntitle: "http://example.com:8080/path"\n---\nBody'
        meta, body = parse_frontmatter(text)
        self.assertEqual(meta["title"], "http://example.com:8080/path")

    def test_value_with_leading_spaces(self):
        text = "---\nid:   spaced-id   \n---\nBody"
        meta, body = parse_frontmatter(text)
        self.assertEqual(meta["id"], "spaced-id")

    def test_single_quoted_value(self):
        text = "---\ntitle: 'single quoted'\n---\nBody"
        meta, body = parse_frontmatter(text)
        self.assertEqual(meta["title"], "single quoted")

    def test_list_with_spaces(self):
        text = "---\ntags: [ auth ,  backend , api ]\n---\nBody"
        meta, body = parse_frontmatter(text)
        self.assertEqual(meta["tags"], ["auth", "backend", "api"])

    def test_nested_brackets_in_value(self):
        """List items that look like they contain brackets."""
        text = '---\ntags: [a, b, c]\n---\nBody'
        meta, body = parse_frontmatter(text)
        self.assertEqual(meta["tags"], ["a", "b", "c"])

    def test_empty_body(self):
        text = "---\nid: test\n---\n"
        meta, body = parse_frontmatter(text)
        self.assertEqual(meta["id"], "test")
        self.assertEqual(body, "")

    def test_body_with_frontmatter_like_content(self):
        text = "---\nid: test\n---\nBody\n---\nid: fake\n---\nMore body"
        meta, body = parse_frontmatter(text)
        self.assertEqual(meta["id"], "test")
        # Body should contain the fake frontmatter
        self.assertIn("id: fake", body)

    def test_write_then_parse_roundtrip_special_chars(self):
        meta = {
            "id": "test-1",
            "title": "Auth: OAuth [v2] #priority",
            "status": "pending",
            "tags": ["backend", "auth"],
            "children": [],
            "blocked_by": "null",
        }
        body = "# Content\n\nWith **markdown** and `code`"
        output = write_frontmatter(meta, body)
        parsed_meta, parsed_body = parse_frontmatter(output)
        self.assertEqual(parsed_meta["id"], "test-1")
        self.assertEqual(parsed_meta["title"], "Auth: OAuth [v2] #priority")
        self.assertEqual(parsed_meta["tags"], ["backend", "auth"])
        self.assertEqual(parsed_body, body)

    def test_numeric_value_stays_string(self):
        text = "---\nid: 42\n---\nBody"
        meta, _ = parse_frontmatter(text)
        # Should be string "42" not int
        self.assertEqual(meta["id"], "42")
        self.assertIsInstance(meta["id"], str)


# ===========================================================================
# 4. BLOCKING / CIRCULAR DEPENDENCY
# ===========================================================================

class TestBlockingEdgeCases(StressTestBase):
    """Circular dependency detection and blocking edge cases."""

    def test_self_block_rejected(self):
        """An agent cannot block itself."""
        cmd_spawn(_SpawnArgs(id="self-blocker"))
        with self.assertRaises(SystemExit):
            cmd_status(_StatusArgs(id="self-blocker", new_status="blocked", blocked_by="self-blocker"))

    def test_direct_circular_block(self):
        """A blocks B, then B tries to block A."""
        cmd_spawn(_SpawnArgs(id="a"))
        cmd_spawn(_SpawnArgs(id="b"))
        cmd_status(_StatusArgs(id="a", new_status="blocked", blocked_by="b"))
        with self.assertRaises(SystemExit):
            cmd_status(_StatusArgs(id="b", new_status="blocked", blocked_by="a"))

    def test_transitive_circular_block(self):
        """A blocked by B, B blocked by C, C tries to block A."""
        cmd_spawn(_SpawnArgs(id="a"))
        cmd_spawn(_SpawnArgs(id="b"))
        cmd_spawn(_SpawnArgs(id="c"))
        cmd_status(_StatusArgs(id="a", new_status="blocked", blocked_by="b"))
        cmd_status(_StatusArgs(id="b", new_status="blocked", blocked_by="c"))
        with self.assertRaises(SystemExit):
            cmd_status(_StatusArgs(id="c", new_status="blocked", blocked_by="a"))

    def test_long_block_chain_no_cycle(self):
        """A -> B -> C -> D (no cycle) should work."""
        for agent_id in ["a", "b", "c", "d"]:
            cmd_spawn(_SpawnArgs(id=agent_id))
        cmd_status(_StatusArgs(id="a", new_status="blocked", blocked_by="b"))
        cmd_status(_StatusArgs(id="b", new_status="blocked", blocked_by="c"))
        cmd_status(_StatusArgs(id="c", new_status="blocked", blocked_by="d"))
        # All should be blocked
        data = self._load_tree()
        self.assertEqual(data["agents"]["a"]["status"], "blocked")
        self.assertEqual(data["agents"]["b"]["status"], "blocked")
        self.assertEqual(data["agents"]["c"]["status"], "blocked")

    def test_unblock_then_reblock(self):
        """Block, unblock, then reblock with a different agent."""
        cmd_spawn(_SpawnArgs(id="x"))
        cmd_spawn(_SpawnArgs(id="y"))
        cmd_spawn(_SpawnArgs(id="z"))
        cmd_status(_StatusArgs(id="x", new_status="blocked", blocked_by="y"))
        cmd_status(_StatusArgs(id="x", new_status="working"))
        cmd_status(_StatusArgs(id="x", new_status="blocked", blocked_by="z"))
        data = self._load_tree()
        self.assertEqual(data["agents"]["x"]["blocked_by"], "z")

    def test_block_by_nonexistent_agent(self):
        cmd_spawn(_SpawnArgs(id="lonely"))
        with self.assertRaises(SystemExit):
            cmd_status(_StatusArgs(id="lonely", new_status="blocked", blocked_by="ghost"))

    def test_blocked_status_without_blocked_by(self):
        cmd_spawn(_SpawnArgs(id="missing-blocker"))
        with self.assertRaises(SystemExit):
            cmd_status(_StatusArgs(id="missing-blocker", new_status="blocked"))


# ===========================================================================
# 5. DELETE EDGE CASES
# ===========================================================================

class TestDeleteEdgeCases(StressTestBase):
    """Cascade delete, deep trees, and orphan handling."""

    def test_cascade_delete_deep_tree(self):
        """Delete root of a 4-level deep tree with --cascade."""
        cmd_spawn(_SpawnArgs(id="r"))
        cmd_spawn(_SpawnArgs(id="c1", parent="r"))
        cmd_spawn(_SpawnArgs(id="c2", parent="r"))
        cmd_spawn(_SpawnArgs(id="gc1", parent="c1"))
        cmd_spawn(_SpawnArgs(id="gc2", parent="c1"))
        cmd_spawn(_SpawnArgs(id="ggc1", parent="gc1"))

        cmd_delete(_DeleteArgs(id="r", cascade=True))
        data = self._load_tree()
        self.assertEqual(len(data["agents"]), 0)
        self.assertNotIn("r", data.get("root_children", []))

    def test_delete_without_cascade_fails_with_children(self):
        cmd_spawn(_SpawnArgs(id="parent"))
        cmd_spawn(_SpawnArgs(id="child", parent="parent"))
        with self.assertRaises(SystemExit):
            cmd_delete(_DeleteArgs(id="parent"))

    def test_delete_leaf_no_cascade_needed(self):
        cmd_spawn(_SpawnArgs(id="leaf"))
        cmd_delete(_DeleteArgs(id="leaf"))
        data = self._load_tree()
        self.assertNotIn("leaf", data["agents"])

    def test_delete_nonexistent(self):
        with self.assertRaises(SystemExit):
            cmd_delete(_DeleteArgs(id="ghost"))

    def test_delete_middle_of_tree_cascade(self):
        """Delete a middle node, keeping siblings intact."""
        cmd_spawn(_SpawnArgs(id="p"))
        cmd_spawn(_SpawnArgs(id="left", parent="p"))
        cmd_spawn(_SpawnArgs(id="right", parent="p"))
        cmd_spawn(_SpawnArgs(id="left-child", parent="left"))

        cmd_delete(_DeleteArgs(id="left", cascade=True))
        data = self._load_tree()
        self.assertNotIn("left", data["agents"])
        self.assertNotIn("left-child", data["agents"])
        self.assertIn("right", data["agents"])
        self.assertIn("p", data["agents"])
        # parent's children list should be updated
        self.assertEqual(data["agents"]["p"]["children"], ["right"])

    def test_cascade_delete_cleans_up_files(self):
        """Verify MD files are actually removed from disk."""
        cmd_spawn(_SpawnArgs(id="parent"))
        cmd_spawn(_SpawnArgs(id="child", parent="parent"))
        child_file = os.path.join(self._agents_dir, "parent", "child.md")
        self.assertTrue(os.path.exists(child_file))

        cmd_delete(_DeleteArgs(id="parent", cascade=True))
        self.assertFalse(os.path.exists(child_file))


# ===========================================================================
# 6. SYNC EDGE CASES
# ===========================================================================

class TestSyncEdgeCases(StressTestBase):
    """Sync behavior when MD files are manually modified or deleted."""

    def test_sync_removes_agents_with_deleted_files(self):
        """Manually delete an MD file, sync should remove from tree.json."""
        cmd_spawn(_SpawnArgs(id="doomed"))
        md_path = os.path.join(self._agents_dir, "doomed.md")
        os.unlink(md_path)

        cmd_sync(_SyncArgs())
        data = self._load_tree()
        self.assertNotIn("doomed", data["agents"])
        self.assertNotIn("doomed", data.get("root_children", []))

    def test_sync_picks_up_status_change_in_md(self):
        """Manually change status in MD file, sync should update tree.json."""
        cmd_spawn(_SpawnArgs(id="manual-edit"))
        md_path = os.path.join(self._agents_dir, "manual-edit.md")
        with open(md_path) as f:
            content = f.read()
        content = content.replace("status: pending", "status: working")
        with open(md_path, "w") as f:
            f.write(content)

        cmd_sync(_SyncArgs())
        data = self._load_tree()
        self.assertEqual(data["agents"]["manual-edit"]["status"], "working")

    def test_sync_picks_up_title_change_in_md(self):
        cmd_spawn(_SpawnArgs(id="title-edit", title="Original"))
        md_path = os.path.join(self._agents_dir, "title-edit.md")
        with open(md_path) as f:
            content = f.read()
        content = content.replace("title: Original", "title: Updated Title")
        with open(md_path, "w") as f:
            f.write(content)

        cmd_sync(_SyncArgs())
        data = self._load_tree()
        self.assertEqual(data["agents"]["title-edit"]["title"], "Updated Title")

    def test_sync_idempotent(self):
        """Running sync twice with no changes should be a no-op."""
        cmd_spawn(_SpawnArgs(id="stable"))
        cmd_sync(_SyncArgs())
        data_before = self._load_tree()
        cmd_sync(_SyncArgs())
        data_after = self._load_tree()
        self.assertEqual(data_before, data_after)

    def test_sync_with_child_file_deleted(self):
        """Delete a child's MD but keep parent — sync should clean up."""
        cmd_spawn(_SpawnArgs(id="parent"))
        cmd_spawn(_SpawnArgs(id="child", parent="parent"))
        child_file = os.path.join(self._agents_dir, "parent", "child.md")
        os.unlink(child_file)

        cmd_sync(_SyncArgs())
        data = self._load_tree()
        self.assertNotIn("child", data["agents"])
        self.assertNotIn("child", data["agents"]["parent"]["children"])


# ===========================================================================
# 7. VALIDATE EDGE CASES
# ===========================================================================

class TestValidateEdgeCases(StressTestBase):
    """Validate detects various forms of corruption."""

    def test_validate_clean_tree(self):
        """Valid tree should pass."""
        cmd_spawn(_SpawnArgs(id="valid"))
        # Should not raise
        cmd_validate(_ValidateArgs())

    def test_validate_detects_missing_md_file(self):
        """Delete MD file, validate should catch it."""
        cmd_spawn(_SpawnArgs(id="missing-file"))
        md_path = os.path.join(self._agents_dir, "missing-file.md")
        os.unlink(md_path)

        # Validate prints issues but doesn't raise — capture output
        import io
        from unittest.mock import patch
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            cmd_validate(_ValidateArgs())
        output = mock_out.getvalue()
        self.assertIn("MISSING FILE", output)

    def test_validate_detects_orphan(self):
        """Create agent referencing nonexistent parent in tree.json."""
        cmd_spawn(_SpawnArgs(id="orphan-test"))
        data = self._load_tree()
        data["agents"]["orphan-test"]["parent"] = "nonexistent-parent"
        with open(os.path.join(self._agents_dir, "tree.json"), "w") as f:
            json.dump(data, f)

        import io
        from unittest.mock import patch
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            cmd_validate(_ValidateArgs())
        output = mock_out.getvalue()
        self.assertIn("ORPHAN", output)

    def test_validate_detects_missing_child(self):
        """Add nonexistent child ID to agent's children list."""
        cmd_spawn(_SpawnArgs(id="parent-v"))
        data = self._load_tree()
        data["agents"]["parent-v"]["children"] = ["ghost-child"]
        with open(os.path.join(self._agents_dir, "tree.json"), "w") as f:
            json.dump(data, f)

        import io
        from unittest.mock import patch
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            cmd_validate(_ValidateArgs())
        output = mock_out.getvalue()
        self.assertIn("MISSING CHILD", output)

    def test_validate_detects_missing_blocker(self):
        """Set blocked_by to nonexistent agent in tree.json."""
        cmd_spawn(_SpawnArgs(id="blocked-v"))
        data = self._load_tree()
        data["agents"]["blocked-v"]["blocked_by"] = "phantom-blocker"
        with open(os.path.join(self._agents_dir, "tree.json"), "w") as f:
            json.dump(data, f)

        import io
        from unittest.mock import patch
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            cmd_validate(_ValidateArgs())
        output = mock_out.getvalue()
        self.assertIn("MISSING BLOCKER", output)


# ===========================================================================
# 8. INIT EDGE CASES
# ===========================================================================

class TestInitEdgeCases(StressTestBase):
    """Reinit, force overwrite, etc."""

    def test_reinit_without_force_fails(self):
        with self.assertRaises(SystemExit):
            cmd_init(_InitArgs())

    def test_reinit_with_force_overwrites(self):
        cmd_spawn(_SpawnArgs(id="old-agent"))
        cmd_init(_InitArgs(objective="Fresh start", force=True))
        data = self._load_tree()
        self.assertEqual(data["objective"], "Fresh start")
        self.assertEqual(len(data["agents"]), 0)

    def test_init_with_special_chars_objective(self):
        os.chdir(self._orig_cwd)
        tmpdir2 = tempfile.mkdtemp()
        os.chdir(tmpdir2)
        try:
            cmd_init(_InitArgs(objective="Build: [auth] system with #priority & 'quotes'"))
            # Should create valid files
            self.assertTrue(os.path.exists(os.path.join(tmpdir2, ".claude-agents", "tree.json")))
        finally:
            os.chdir(self._orig_cwd)
            shutil.rmtree(tmpdir2)


# ===========================================================================
# 9. STATUS TRANSITIONS
# ===========================================================================

class TestStatusTransitions(StressTestBase):
    """All valid status transitions and edge cases."""

    def test_all_valid_statuses(self):
        """Every status value should be settable."""
        for status in ["pending", "working", "done", "failed", "cancelled"]:
            agent_id = f"status-{status}"
            cmd_spawn(_SpawnArgs(id=agent_id))
            cmd_status(_StatusArgs(id=agent_id, new_status=status))
            data = self._load_tree()
            self.assertEqual(data["agents"][agent_id]["status"], status)

    def test_status_on_nonexistent_agent(self):
        with self.assertRaises(SystemExit):
            cmd_status(_StatusArgs(id="ghost", new_status="working"))

    def test_rapid_status_changes(self):
        """Change status many times rapidly."""
        cmd_spawn(_SpawnArgs(id="flip-flop"))
        for _ in range(20):
            cmd_status(_StatusArgs(id="flip-flop", new_status="working"))
            cmd_status(_StatusArgs(id="flip-flop", new_status="pending"))
        data = self._load_tree()
        self.assertEqual(data["agents"]["flip-flop"]["status"], "pending")

    def test_complete_then_status_change(self):
        """A completed agent can have status changed back."""
        cmd_spawn(_SpawnArgs(id="reopen"))
        cmd_complete(_CompleteArgs(id="reopen", summary="Done initially"))
        cmd_status(_StatusArgs(id="reopen", new_status="working"))
        data = self._load_tree()
        self.assertEqual(data["agents"]["reopen"]["status"], "working")


# ===========================================================================
# 10. COMPLETE / FAIL EDGE CASES
# ===========================================================================

class TestCompleteFailEdgeCases(StressTestBase):

    def test_complete_nonexistent(self):
        with self.assertRaises(SystemExit):
            cmd_complete(_CompleteArgs(id="ghost"))

    def test_fail_nonexistent(self):
        with self.assertRaises(SystemExit):
            cmd_fail(_FailArgs(id="ghost"))

    def test_complete_with_special_chars_summary(self):
        cmd_spawn(_SpawnArgs(id="special-done"))
        cmd_complete(_CompleteArgs(id="special-done", summary="Done! Auth: [v2] with #tags & 'quotes'"))
        data = self._load_tree()
        self.assertEqual(data["agents"]["special-done"]["status"], "done")

    def test_fail_with_long_reason(self):
        cmd_spawn(_SpawnArgs(id="fail-long"))
        reason = "Error: " + "x" * 1000
        cmd_fail(_FailArgs(id="fail-long", reason=reason))
        md_path = os.path.join(self._agents_dir, "fail-long.md")
        with open(md_path) as f:
            content = f.read()
        self.assertIn("FAILED", content)

    def test_complete_clears_blocked_by(self):
        """Completing a blocked agent should clear blocked_by."""
        cmd_spawn(_SpawnArgs(id="blocker"))
        cmd_spawn(_SpawnArgs(id="blocked"))
        cmd_status(_StatusArgs(id="blocked", new_status="blocked", blocked_by="blocker"))
        cmd_complete(_CompleteArgs(id="blocked", summary="Done despite blocker"))
        data = self._load_tree()
        self.assertIsNone(data["agents"]["blocked"]["blocked_by"])


# ===========================================================================
# 11. UPDATE EDGE CASES
# ===========================================================================

class TestUpdateEdgeCases(StressTestBase):

    def test_update_nothing_fails(self):
        cmd_spawn(_SpawnArgs(id="no-update"))
        with self.assertRaises(SystemExit):
            cmd_update(_UpdateArgs(id="no-update"))

    def test_update_nonexistent(self):
        with self.assertRaises(SystemExit):
            cmd_update(_UpdateArgs(id="ghost", title="New"))

    def test_update_title_objective_tags_together(self):
        cmd_spawn(_SpawnArgs(id="multi-update", title="Old", objective="Old obj", tags=["old"]))
        cmd_update(_UpdateArgs(id="multi-update", title="New", objective="New obj", tags=["new", "v2"]))
        data = self._load_tree()
        self.assertEqual(data["agents"]["multi-update"]["title"], "New")
        self.assertEqual(data["agents"]["multi-update"]["tags"], ["new", "v2"])

    def test_update_objective_with_regex_special_chars(self):
        """Objective update uses regex — test with regex-hostile content."""
        cmd_spawn(_SpawnArgs(id="regex-obj", objective="Original"))
        cmd_update(_UpdateArgs(id="regex-obj", objective="New: (pattern) with [brackets] and $dollars"))
        # Read back
        md_path = os.path.join(self._agents_dir, "regex-obj.md")
        with open(md_path) as f:
            content = f.read()
        self.assertIn("$dollars", content)

    def test_update_tags_to_empty(self):
        cmd_spawn(_SpawnArgs(id="clear-tags", tags=["a", "b"]))
        cmd_update(_UpdateArgs(id="clear-tags", tags=[]))
        data = self._load_tree()
        self.assertEqual(data["agents"]["clear-tags"]["tags"], [])


# ===========================================================================
# 12. CONTEXT EDGE CASES
# ===========================================================================

class TestContextEdgeCases(StressTestBase):

    def test_context_root_agent(self):
        """Root agent should show objective in chain."""
        cmd_spawn(_SpawnArgs(id="root-ctx"))
        cmd_context(_ContextArgs(id="root-ctx"))

    def test_context_deep_agent(self):
        """Deep agent should show full chain."""
        cmd_spawn(_SpawnArgs(id="a"))
        cmd_spawn(_SpawnArgs(id="b", parent="a"))
        cmd_spawn(_SpawnArgs(id="c", parent="b"))
        cmd_spawn(_SpawnArgs(id="d", parent="c"))
        cmd_context(_ContextArgs(id="d"))

    def test_context_nonexistent(self):
        with self.assertRaises(SystemExit):
            cmd_context(_ContextArgs(id="ghost"))

    def test_context_shows_blocked_by(self):
        cmd_spawn(_SpawnArgs(id="blocker"))
        cmd_spawn(_SpawnArgs(id="victim"))
        cmd_status(_StatusArgs(id="victim", new_status="blocked", blocked_by="blocker"))

        import io
        from unittest.mock import patch
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            cmd_context(_ContextArgs(id="victim"))
        output = mock_out.getvalue()
        self.assertIn("Blocked by", output)
        self.assertIn("blocker", output)


# ===========================================================================
# 13. LOG EDGE CASES
# ===========================================================================

class TestLogEdgeCases(StressTestBase):

    def test_many_log_entries(self):
        """Add 50 log entries and verify last one shows in verbose tree."""
        cmd_spawn(_SpawnArgs(id="chatty"))
        for i in range(50):
            cmd_log(_LogArgs(id="chatty", message=f"Log entry #{i}"))

        import io
        from unittest.mock import patch
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            cmd_tree(_TreeArgs(verbose=True))
        output = mock_out.getvalue()
        self.assertIn("Log entry #49", output)

    def test_log_nonexistent_agent(self):
        with self.assertRaises(SystemExit):
            cmd_log(_LogArgs(id="ghost", message="Hello"))


# ===========================================================================
# 14. TREE DISPLAY EDGE CASES
# ===========================================================================

class TestTreeDisplayEdgeCases(StressTestBase):

    def test_tree_empty(self):
        """Tree with no agents should just show objective."""
        import io
        from unittest.mock import patch
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            cmd_tree(_TreeArgs())
        output = mock_out.getvalue()
        self.assertIn("Stress test", output)

    def test_tree_tag_filter(self):
        """Tag filter should only show matching agents."""
        cmd_spawn(_SpawnArgs(id="tagged", tags=["api"]))
        cmd_spawn(_SpawnArgs(id="untagged", tags=["db"]))

        import io
        from unittest.mock import patch
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            cmd_tree(_TreeArgs(tag="api"))
        output = mock_out.getvalue()
        self.assertIn("tagged", output)
        self.assertNotIn("untagged", output)

    def test_tree_large_display(self):
        """Display tree with 30+ agents without crashing."""
        for i in range(30):
            cmd_spawn(_SpawnArgs(id=f"a-{i:02d}", title=f"Agent {i}"))
        cmd_tree(_TreeArgs())
        cmd_tree(_TreeArgs(verbose=True))


# ===========================================================================
# 15. FILE SYSTEM EDGE CASES
# ===========================================================================

class TestFileSystemEdgeCases(StressTestBase):

    def test_tree_json_corrupt_json(self):
        """Corrupt tree.json should exit gracefully."""
        tree_path = os.path.join(self._agents_dir, "tree.json")
        with open(tree_path, "w") as f:
            f.write("{invalid json!!!")
        with self.assertRaises(SystemExit):
            store = TreeStore(self._agents_dir)
            store.load()

    def test_tree_json_future_version(self):
        """Tree with future version should raise."""
        tree_path = os.path.join(self._agents_dir, "tree.json")
        with open(tree_path) as f:
            data = json.load(f)
        data["version"] = 999
        with open(tree_path, "w") as f:
            json.dump(data, f)
        store = TreeStore(self._agents_dir)
        with self.assertRaises(SystemExit):
            store.load()

    def test_stale_lock_file_cleaned_up(self):
        """Lock file from dead PID should be cleaned up."""
        lock_path = os.path.join(self._agents_dir, "tree.lock")
        with open(lock_path, "w") as f:
            f.write("99999999")  # unlikely to be a real PID

        # Should not raise — stale lock should be cleaned
        cmd_spawn(_SpawnArgs(id="after-stale-lock"))
        data = self._load_tree()
        self.assertIn("after-stale-lock", data["agents"])

    def test_corrupt_lock_file_cleaned_up(self):
        """Lock file with non-numeric content should be cleaned up."""
        lock_path = os.path.join(self._agents_dir, "tree.lock")
        with open(lock_path, "w") as f:
            f.write("not-a-pid")

        cmd_spawn(_SpawnArgs(id="after-corrupt-lock"))
        data = self._load_tree()
        self.assertIn("after-corrupt-lock", data["agents"])

    def test_find_agents_dir_walks_up(self):
        """find_agents_dir should walk up from subdirectories."""
        subdir = os.path.join(self._tmpdir.name, "src", "deep", "path")
        os.makedirs(subdir)
        result = TreeStore.find_agents_dir(subdir)
        self.assertIsNotNone(result)
        self.assertTrue(result.endswith(".claude-agents"))

    def test_find_agents_dir_returns_none_at_root(self):
        """find_agents_dir should return None if no .claude-agents exists."""
        isolated = tempfile.mkdtemp()
        try:
            result = TreeStore.find_agents_dir(isolated)
            self.assertIsNone(result)
        finally:
            shutil.rmtree(isolated)


# ===========================================================================
# 16. READ EDGE CASES
# ===========================================================================

class TestReadEdgeCases(StressTestBase):

    def test_read_nonexistent(self):
        with self.assertRaises(SystemExit):
            cmd_read(_ReadArgs(id="ghost"))

    def test_read_after_multiple_logs(self):
        """Read should show accumulated log entries."""
        cmd_spawn(_SpawnArgs(id="logged"))
        for i in range(5):
            cmd_log(_LogArgs(id="logged", message=f"Entry {i}"))

        import io
        from unittest.mock import patch
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            cmd_read(_ReadArgs(id="logged"))
        output = mock_out.getvalue()
        for i in range(5):
            self.assertIn(f"Entry {i}", output)


# ===========================================================================
# 17. COMBINED STRESS SCENARIOS
# ===========================================================================

class TestCombinedStress(StressTestBase):
    """Multi-operation scenarios that exercise multiple features together."""

    def test_full_lifecycle_with_blocks(self):
        """Create → block → unblock → work → complete → validate."""
        cmd_spawn(_SpawnArgs(id="api", title="API"))
        cmd_spawn(_SpawnArgs(id="db", title="Database"))
        cmd_spawn(_SpawnArgs(id="ui", title="UI"))

        # Block API on DB
        cmd_status(_StatusArgs(id="api", new_status="blocked", blocked_by="db"))

        # Work on DB
        cmd_status(_StatusArgs(id="db", new_status="working"))
        cmd_log(_LogArgs(id="db", message="Created tables"))
        cmd_complete(_CompleteArgs(id="db", summary="All tables created"))

        # Unblock and work on API
        cmd_status(_StatusArgs(id="api", new_status="working"))
        cmd_log(_LogArgs(id="api", message="Building endpoints"))
        cmd_complete(_CompleteArgs(id="api", summary="Endpoints live"))

        # Work on UI
        cmd_status(_StatusArgs(id="ui", new_status="working"))
        cmd_complete(_CompleteArgs(id="ui", summary="Frontend ready"))

        # Validate
        cmd_validate(_ValidateArgs())
        data = self._load_tree()
        for agent_id in ["api", "db", "ui"]:
            self.assertEqual(data["agents"][agent_id]["status"], "done")

    def test_spawn_delete_respawn(self):
        """Spawn an agent, delete it, spawn again with same ID."""
        cmd_spawn(_SpawnArgs(id="phoenix"))
        cmd_delete(_DeleteArgs(id="phoenix"))
        cmd_spawn(_SpawnArgs(id="phoenix", title="Reborn"))
        data = self._load_tree()
        self.assertEqual(data["agents"]["phoenix"]["title"], "Reborn")

    def test_sync_after_manual_file_deletion_and_corruption(self):
        """Multiple agents, delete some files, corrupt others, then sync."""
        for i in range(5):
            cmd_spawn(_SpawnArgs(id=f"s-{i}"))

        # Delete file for s-0
        os.unlink(os.path.join(self._agents_dir, "s-0.md"))

        # Manually change status in s-1's file
        md_path = os.path.join(self._agents_dir, "s-1.md")
        with open(md_path) as f:
            content = f.read()
        content = content.replace("status: pending", "status: done")
        with open(md_path, "w") as f:
            f.write(content)

        cmd_sync(_SyncArgs())
        data = self._load_tree()
        self.assertNotIn("s-0", data["agents"])
        self.assertEqual(data["agents"]["s-1"]["status"], "done")
        for i in range(2, 5):
            self.assertIn(f"s-{i}", data["agents"])

    def test_tree_json_backslash_normalization(self):
        """Verify tree.json uses forward slashes even when paths have backslashes."""
        cmd_spawn(_SpawnArgs(id="parent"))
        cmd_spawn(_SpawnArgs(id="child", parent="parent"))
        tree_path = os.path.join(self._agents_dir, "tree.json")
        with open(tree_path) as f:
            raw = f.read()
        self.assertNotIn("\\\\", raw)

    def test_concurrent_safe_lock_same_process(self):
        """Two lock acquisitions in same process — second should fail."""
        store = TreeStore(self._agents_dir)
        lock = store.lock()
        lock.acquire()
        try:
            # Same process, same PID — should detect it's alive
            lock2 = store.lock()
            with self.assertRaises(RuntimeError):
                lock2.acquire()
        finally:
            lock.release()


# ===========================================================================
# 18. ID VALIDATION & SECURITY
# ===========================================================================

class TestIdValidation(unittest.TestCase):
    """Verify ID validation blocks dangerous inputs."""

    def test_path_traversal_rejected(self):
        for bad in ["../evil", "../../etc/passwd", "../../../tmp/x"]:
            with self.assertRaises(SystemExit, msg=f"ID '{bad}' should be rejected"):
                _validate_agent_id(bad)

    def test_slash_in_id_rejected(self):
        for bad in ["auth/login", "a/b/c", "/root"]:
            with self.assertRaises(SystemExit, msg=f"ID '{bad}' should be rejected"):
                _validate_agent_id(bad)

    def test_empty_id_rejected(self):
        with self.assertRaises(SystemExit):
            _validate_agent_id("")

    def test_space_in_id_rejected(self):
        with self.assertRaises(SystemExit):
            _validate_agent_id("a b c")

    def test_hidden_file_id_rejected(self):
        with self.assertRaises(SystemExit):
            _validate_agent_id(".hidden")

    def test_reserved_names_rejected(self):
        for reserved in ["objective", "tree", "root"]:
            with self.assertRaises(SystemExit, msg=f"'{reserved}' should be reserved"):
                _validate_agent_id(reserved)

    def test_too_long_id_rejected(self):
        with self.assertRaises(SystemExit):
            _validate_agent_id("a" * 101)

    def test_valid_ids_pass(self):
        for valid in ["auth-api", "task-1", "v1.0.0", "my_agent", "123", "A"]:
            _validate_agent_id(valid)  # should not raise


class TestNewlineInValues(StressTestBase):
    """Verify newlines in titles/objectives are sanitized."""

    def test_newline_in_title_sanitized(self):
        cmd_spawn(_SpawnArgs(id="nl-title", title="Line1\nLine2"))
        md_path = os.path.join(self._agents_dir, "nl-title.md")
        with open(md_path) as f:
            meta, _ = parse_frontmatter(f.read())
        # Newline should be replaced with space
        self.assertEqual(meta["title"], "Line1 Line2")

    def test_newline_in_title_roundtrip(self):
        """Title with newline should survive write→parse roundtrip."""
        cmd_spawn(_SpawnArgs(id="nl-rt", title="A\nB"))
        data = self._load_tree()
        md_path = os.path.join(self._agents_dir, data["agents"]["nl-rt"]["file"])
        with open(md_path) as f:
            meta, _ = parse_frontmatter(f.read())
        self.assertNotIn("\n", meta.get("title", ""))


class TestCommaInTags(StressTestBase):
    """Verify tags with commas roundtrip correctly."""

    def test_tag_with_comma_roundtrips(self):
        cmd_spawn(_SpawnArgs(id="comma-tag", tags=["tag with, comma", "normal"]))
        md_path = os.path.join(self._agents_dir, "comma-tag.md")
        with open(md_path) as f:
            meta, _ = parse_frontmatter(f.read())
        self.assertEqual(meta["tags"], ["tag with, comma", "normal"])


class TestObjectiveUpdateMissing(StressTestBase):
    """Verify objective update warns when section is missing."""

    def test_update_warns_when_objective_section_missing(self):
        cmd_spawn(_SpawnArgs(id="no-obj", objective="original"))
        md_path = os.path.join(self._agents_dir, "no-obj.md")
        with open(md_path) as f:
            content = f.read()
        content = content.replace("## Objective", "## Goals")
        with open(md_path, "w") as f:
            f.write(content)

        import io
        from unittest.mock import patch
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            cmd_update(_UpdateArgs(id="no-obj", objective="new"))
        output = mock_out.getvalue()
        self.assertIn("Warning", output)


if __name__ == "__main__":
    unittest.main()
