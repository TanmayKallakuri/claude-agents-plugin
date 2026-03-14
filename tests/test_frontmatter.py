"""Tests for YAML frontmatter parser."""
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent_tree import parse_frontmatter, write_frontmatter, _format_yaml_value


class TestParseFrontmatter(unittest.TestCase):
    def test_simple_fields(self):
        text = "---\nid: task-1\ntitle: My Task\nstatus: pending\n---\nBody here"
        meta, body = parse_frontmatter(text)
        self.assertEqual(meta["id"], "task-1")
        self.assertEqual(meta["title"], "My Task")
        self.assertEqual(meta["status"], "pending")
        self.assertEqual(body, "Body here")

    def test_empty_list(self):
        text = "---\ntags: []\n---\nBody"
        meta, body = parse_frontmatter(text)
        self.assertEqual(meta["tags"], [])
        self.assertEqual(body, "Body")

    def test_list_with_items(self):
        text = "---\ntags: [auth, backend, api]\n---\nBody"
        meta, body = parse_frontmatter(text)
        self.assertEqual(meta["tags"], ["auth", "backend", "api"])

    def test_no_frontmatter(self):
        text = "Just a plain body\nWith multiple lines"
        meta, body = parse_frontmatter(text)
        self.assertEqual(meta, {})
        self.assertEqual(body, text)

    def test_blocked_by_field(self):
        text = "---\nid: task-2\nblocked_by: [task-1]\n---\nBlocked task"
        meta, body = parse_frontmatter(text)
        self.assertEqual(meta["blocked_by"], ["task-1"])

    def test_special_chars_colon_in_title(self):
        text = '---\nid: task-1\ntitle: "Auth: OAuth Flow"\n---\nBody'
        meta, body = parse_frontmatter(text)
        self.assertEqual(meta["title"], "Auth: OAuth Flow")

    def test_special_chars_brackets_in_string(self):
        text = '---\nid: task-1\ntitle: "Use [brackets] here"\n---\nBody'
        meta, body = parse_frontmatter(text)
        self.assertEqual(meta["title"], "Use [brackets] here")

    def test_quoted_values_roundtrip(self):
        meta = {"id": "task-1", "title": "Auth: OAuth Flow", "status": "pending"}
        body = "Some body"
        output = write_frontmatter(meta, body)
        parsed_meta, parsed_body = parse_frontmatter(output)
        self.assertEqual(parsed_meta["title"], "Auth: OAuth Flow")
        self.assertEqual(parsed_body, body)

    def test_roundtrip_with_lists(self):
        meta = {
            "id": "task-1",
            "title": "Test",
            "status": "pending",
            "tags": ["auth", "api"],
            "children": [],
        }
        body = "Task body"
        output = write_frontmatter(meta, body)
        parsed_meta, parsed_body = parse_frontmatter(output)
        self.assertEqual(parsed_meta["tags"], ["auth", "api"])
        self.assertEqual(parsed_meta["children"], [])
        self.assertEqual(parsed_body, body)


class TestWriteFrontmatter(unittest.TestCase):
    def test_field_ordering(self):
        meta = {
            "tags": ["a"],
            "status": "pending",
            "id": "task-1",
            "title": "Test",
            "parent": "root",
            "created": "2026-01-01",
            "updated": "2026-01-02",
            "children": [],
            "blocked_by": [],
        }
        body = "Body"
        output = write_frontmatter(meta, body)
        lines = output.split("\n")
        self.assertEqual(lines[0], "---")
        self.assertTrue(lines[1].startswith("id:"))
        self.assertTrue(lines[2].startswith("title:"))
        self.assertTrue(lines[3].startswith("status:"))
        self.assertTrue(lines[4].startswith("parent:"))
        self.assertTrue(lines[5].startswith("created:"))
        self.assertTrue(lines[6].startswith("updated:"))
        self.assertTrue(lines[7].startswith("children:"))
        self.assertTrue(lines[8].startswith("tags:"))
        self.assertTrue(lines[9].startswith("blocked_by:"))

    def test_extra_fields_after_ordered(self):
        meta = {"id": "task-1", "custom_field": "value"}
        body = "Body"
        output = write_frontmatter(meta, body)
        lines = output.split("\n")
        self.assertEqual(lines[0], "---")
        self.assertTrue(lines[1].startswith("id:"))
        self.assertTrue(lines[2].startswith("custom_field:"))


class TestFormatYamlValue(unittest.TestCase):
    def test_empty_list(self):
        self.assertEqual(_format_yaml_value([]), "[]")

    def test_list_with_items(self):
        self.assertEqual(_format_yaml_value(["a", "b"]), "[a, b]")

    def test_plain_string(self):
        self.assertEqual(_format_yaml_value("hello"), "hello")

    def test_string_with_colon(self):
        self.assertEqual(_format_yaml_value("Auth: OAuth"), '"Auth: OAuth"')

    def test_string_with_brackets(self):
        self.assertEqual(_format_yaml_value("[test]"), '"[test]"')

    def test_string_with_hash(self):
        self.assertEqual(_format_yaml_value("color #red"), '"color #red"')

    def test_string_with_comma(self):
        self.assertEqual(_format_yaml_value("a, b"), '"a, b"')

    def test_string_with_quotes(self):
        self.assertEqual(_format_yaml_value("it's here"), '"it\'s here"')


if __name__ == "__main__":
    unittest.main()
