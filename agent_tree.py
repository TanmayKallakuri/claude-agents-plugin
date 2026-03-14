#!/usr/bin/env python3
"""Claude Agents Plugin - Core Infrastructure.

Single-file CLI with YAML frontmatter parser, PID-based file lock, and TreeStore.
Zero external dependencies - stdlib only (Python 3.13).
"""

import os
import sys
import json
import re
import shutil
from datetime import datetime, timezone
import argparse


# ---------------------------------------------------------------------------
# YAML Frontmatter Parser
# ---------------------------------------------------------------------------

_SPECIAL_CHARS = set(':#[]{},\'"')

_FIELD_ORDER = [
    "id", "title", "status", "parent", "created", "updated",
    "children", "tags", "blocked_by",
]


def _format_yaml_value(value):
    """Format a Python value as a YAML frontmatter value string."""
    if isinstance(value, list):
        if not value:
            return "[]"
        return "[" + ", ".join(str(item) for item in value) + "]"
    s = str(value)
    if any(c in s for c in _SPECIAL_CHARS):
        return '"' + s + '"'
    return s


def _parse_yaml_value(raw):
    """Parse a raw YAML value string into a Python value."""
    stripped = raw.strip()
    # List
    if stripped.startswith("[") and stripped.endswith("]"):
        inner = stripped[1:-1].strip()
        if not inner:
            return []
        return [item.strip() for item in inner.split(",")]
    # Quoted string
    if (
        (stripped.startswith('"') and stripped.endswith('"'))
        or (stripped.startswith("'") and stripped.endswith("'"))
    ):
        return stripped[1:-1]
    return stripped


def parse_frontmatter(text):
    """Parse YAML frontmatter from markdown text.

    Returns (meta_dict, body_str). If no frontmatter found, returns ({}, text).
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, text

    meta = {}
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
        match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*(.*)', lines[i])
        if match:
            key = match.group(1)
            raw_value = match.group(2)
            meta[key] = _parse_yaml_value(raw_value)

    if end_idx is None:
        return {}, text

    body = "\n".join(lines[end_idx + 1:])
    return meta, body


def write_frontmatter(meta, body):
    """Write YAML frontmatter and body to a string.

    Fields are ordered according to _FIELD_ORDER, with extra fields appended.
    """
    lines = ["---"]

    # Ordered fields first
    written = set()
    for key in _FIELD_ORDER:
        if key in meta:
            lines.append(f"{key}: {_format_yaml_value(meta[key])}")
            written.add(key)

    # Extra fields
    for key, value in meta.items():
        if key not in written:
            lines.append(f"{key}: {_format_yaml_value(value)}")

    lines.append("---")
    return "\n".join(lines) + "\n" + body


# ---------------------------------------------------------------------------
# PID-Based File Lock
# ---------------------------------------------------------------------------

class FileLock:
    """PID-based file lock with stale lock detection."""

    def __init__(self, path):
        self._path = path

    def acquire(self):
        """Acquire the lock. Raises RuntimeError if held by a live process."""
        if os.path.exists(self._path):
            try:
                with open(self._path) as f:
                    existing_pid = int(f.read().strip())
            except (ValueError, OSError):
                # Corrupt lock file, break it
                os.unlink(self._path)
            else:
                try:
                    os.kill(existing_pid, 0)
                except ProcessLookupError:
                    # Stale lock - process is dead
                    os.unlink(self._path)
                except PermissionError:
                    # Process exists but we can't signal it - treat as alive
                    raise RuntimeError(
                        f"Lock held by PID {existing_pid} (permission denied)"
                    )
                else:
                    # Process is alive
                    raise RuntimeError(f"Lock held by PID {existing_pid}")

        with open(self._path, "w") as f:
            f.write(str(os.getpid()))

    def release(self):
        """Release the lock by removing the lock file."""
        if os.path.exists(self._path):
            os.unlink(self._path)

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False


# ---------------------------------------------------------------------------
# TreeStore
# ---------------------------------------------------------------------------

class TreeStore:
    """Manages the tree.json file for agent task trees."""

    CURRENT_VERSION = 1

    def __init__(self, agents_dir):
        self._agents_dir = agents_dir
        self.tree_path = os.path.join(agents_dir, "tree.json")
        self._lock_path = os.path.join(agents_dir, "tree.lock")

    def create(self, objective):
        """Create a new tree.json with the given objective."""
        data = {
            "version": self.CURRENT_VERSION,
            "objective": objective,
            "created": datetime.now(timezone.utc).isoformat(),
            "agents": {},
        }
        self.save(data)

    def load(self):
        """Load and return tree.json data, with version checking."""
        with open(self.tree_path) as f:
            data = json.load(f)
        self._check_version(data)
        return data

    def save(self, data):
        """Save data to tree.json, converting paths to POSIX separators."""
        raw = json.dumps(data, indent=2)
        # Replace backslash paths with forward slashes
        raw = raw.replace("\\\\", "/")
        with open(self.tree_path, "w") as f:
            f.write(raw)

    def lock(self):
        """Return a FileLock instance for the tree."""
        return FileLock(self._lock_path)

    def _check_version(self, data):
        """Check data version, auto-migrate older or error on newer."""
        version = data.get("version", 0)
        if version > self.CURRENT_VERSION:
            raise RuntimeError(
                f"Tree version {version} is newer than supported "
                f"version {self.CURRENT_VERSION}. Please upgrade."
            )
        if version < self.CURRENT_VERSION:
            print(
                f"Notice: Migrating tree from version {version} "
                f"to {self.CURRENT_VERSION}"
            )
            data["version"] = self.CURRENT_VERSION

    @staticmethod
    def find_agents_dir(start_dir):
        """Walk up from start_dir looking for a .claude-agents/ directory."""
        current = os.path.abspath(start_dir)
        while True:
            candidate = os.path.join(current, ".claude-agents")
            if os.path.isdir(candidate):
                return candidate
            parent = os.path.dirname(current)
            if parent == current:
                # Reached filesystem root
                return None
            current = parent


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _get_depth(data, parent_id):
    """Walk parent chain to calculate depth. Root = 0."""
    depth = 0
    current = parent_id
    while current != "root":
        agent = data["agents"].get(current)
        if agent is None:
            break
        current = agent.get("parent", "root")
        depth += 1
    return depth


def _move_to_subfolder(agents_dir, agent_id, current_file, data):
    """Move a flat MD file into its own subfolder.

    Creates {agent_id}/ and moves {agent_id}.md -> {agent_id}/{agent_id}.md.
    Updates the file path in tree.json data (caller must save).
    Returns the new file path relative to agents_dir.
    """
    subfolder = os.path.join(agents_dir, agent_id)
    os.makedirs(subfolder, exist_ok=True)
    new_file = os.path.join(subfolder, f"{agent_id}.md")
    shutil.move(current_file, new_file)
    new_rel = f"{agent_id}/{agent_id}.md"
    data["agents"][agent_id]["file"] = new_rel
    return new_rel


def _update_md_children(agents_dir, agent_entry):
    """Update the children field in an agent's MD frontmatter."""
    file_path = os.path.join(agents_dir, agent_entry["file"])
    with open(file_path) as f:
        text = f.read()
    meta, body = parse_frontmatter(text)
    meta["children"] = list(agent_entry.get("children", []))
    with open(file_path, "w") as f:
        f.write(write_frontmatter(meta, body))


def _has_circular_block(data, agent_id, blocked_by_id):
    """Check for transitive circular dependency in blocked_by chains.

    Walks the blocked_by chain from blocked_by_id. If it reaches agent_id,
    there is a cycle.
    """
    visited = set()
    current = blocked_by_id
    while current is not None:
        if current == agent_id:
            return True
        if current in visited:
            return False
        visited.add(current)
        agent = data["agents"].get(current)
        if agent is None:
            return False
        current = agent.get("blocked_by")
    return False


def _get_last_log_entry(agents_dir, agent_entry):
    """Extract the last log entry (### heading + content) from an agent's MD file."""
    file_path = os.path.join(agents_dir, agent_entry["file"])
    try:
        with open(file_path) as f:
            text = f.read()
    except OSError:
        return None
    _, body = parse_frontmatter(text)
    # Find all ### headings in the Log section
    matches = list(re.finditer(r'^### (.+)$', body, re.MULTILINE))
    if not matches:
        return None
    last_match = matches[-1]
    # Get content after the last ### heading
    start = last_match.end()
    # Find the next heading of any level or end of text
    next_heading = re.search(r'^#{1,3} ', body[start:], re.MULTILINE)
    if next_heading:
        content = body[start:start + next_heading.start()].strip()
    else:
        content = body[start:].strip()
    heading = last_match.group(1).strip()
    if content:
        return f"{heading}: {content}"
    return heading


def _print_tree_level(data, agents, prefix, args, agents_dir):
    """Recursively print tree levels with box-drawing characters."""
    tag_filter = getattr(args, "tag", None)
    verbose = getattr(args, "verbose", False)

    # Filter agents by tag if needed
    if tag_filter:
        filtered = [a for a in agents if tag_filter in data["agents"].get(a, {}).get("tags", [])]
    else:
        filtered = list(agents)

    for i, agent_id in enumerate(filtered):
        agent = data["agents"].get(agent_id)
        if agent is None:
            continue
        is_last = (i == len(filtered) - 1)
        connector = "└── " if is_last else "├── "
        status = agent.get("status", "pending")
        title = agent.get("title", agent_id)
        print(f"{prefix}{connector}{agent_id} ({status}) — {title}")

        if verbose:
            log_entry = _get_last_log_entry(agents_dir, agent)
            if log_entry:
                extension = "    " if is_last else "│   "
                print(f"{prefix}{extension}  ↳ {log_entry}")

        children = agent.get("children", [])
        if children:
            child_prefix = prefix + ("    " if is_last else "│   ")
            _print_tree_level(data, children, child_prefix, args, agents_dir)


# ---------------------------------------------------------------------------
# Command Implementations
# ---------------------------------------------------------------------------

def cmd_init(args):
    """Initialize a new agent tree in the current directory."""
    agents_dir = os.path.join(os.getcwd(), ".claude-agents")

    if os.path.exists(agents_dir):
        if not args.force:
            print(f"Error: {agents_dir} already exists. Use --force to overwrite.")
            sys.exit(1)
        shutil.rmtree(agents_dir)

    os.makedirs(agents_dir)

    # Write objective.md
    objective_path = os.path.join(agents_dir, "objective.md")
    with open(objective_path, "w") as f:
        f.write(f"# Objective\n\n{args.objective}\n")

    # Write tree.json
    store = TreeStore(agents_dir)
    store.create(args.objective)

    print(f"Initialized agent tree in {agents_dir}")

    # Check .gitignore for tip
    gitignore_path = os.path.join(os.getcwd(), ".gitignore")
    if os.path.exists(gitignore_path):
        with open(gitignore_path) as f:
            content = f.read()
        if ".claude-agents/" not in content and ".claude-agents" not in content:
            print("Tip: Add .claude-agents/ to your .gitignore")


def cmd_spawn(args):
    """Spawn a new agent task."""
    agents_dir = TreeStore.find_agents_dir(os.getcwd())
    if agents_dir is None:
        print("Error: No .claude-agents/ directory found. Run 'init' first.")
        sys.exit(1)

    store = TreeStore(agents_dir)

    with store.lock():
        data = store.load()
        agents = data["agents"]

        # Validate parent
        if args.parent != "root" and args.parent not in agents:
            print(f"Error: Parent '{args.parent}' not found.")
            sys.exit(1)

        # Reject duplicate ID
        if args.id in agents:
            print(f"Error: Agent '{args.id}' already exists.")
            sys.exit(1)

        # Enforce max agents
        agent_count = len(agents)
        max_agents = args.max_agents
        if agent_count >= max_agents and not args.force:
            print(f"Error: Max agents ({max_agents}) reached. Use --force to override.")
            sys.exit(1)
        if agent_count >= 30 and agent_count < max_agents:
            print(f"Warning: {agent_count} agents spawned (max: {max_agents})")

        # Enforce max depth
        depth = _get_depth(data, args.parent) + 1
        if depth > 4 and not args.force:
            print(f"Error: Max depth (4) exceeded at depth {depth}. Use --force to override.")
            sys.exit(1)

        now = datetime.now(timezone.utc).isoformat()

        # Determine file path
        if args.parent == "root":
            file_rel = f"{args.id}.md"
        else:
            parent_entry = agents[args.parent]
            parent_children = parent_entry.get("children", [])

            # If parent has no children yet, move parent to subfolder
            if not parent_children:
                parent_file = os.path.join(agents_dir, parent_entry["file"])
                _move_to_subfolder(agents_dir, args.parent, parent_file, data)

            file_rel = f"{args.parent}/{args.id}.md"

        # Create MD file
        meta = {
            "id": args.id,
            "title": args.title,
            "status": "pending",
            "parent": args.parent,
            "created": now,
            "updated": now,
            "children": [],
            "tags": list(args.tags),
            "blocked_by": "null",
        }
        body = f"\n# {args.title}\n\n## Objective\n{args.objective}\n\n## Log\n"
        md_content = write_frontmatter(meta, body)

        file_path = os.path.join(agents_dir, file_rel)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as f:
            f.write(md_content)

        # Register in tree.json
        agents[args.id] = {
            "id": args.id,
            "title": args.title,
            "status": "pending",
            "parent": args.parent,
            "file": file_rel,
            "created": now,
            "updated": now,
            "children": [],
            "tags": list(args.tags),
            "blocked_by": None,
        }

        # Update parent's children list
        if args.parent == "root":
            root_children = data.get("root_children", [])
            root_children.append(args.id)
            data["root_children"] = root_children
        else:
            parent_entry = agents[args.parent]
            children = parent_entry.get("children", [])
            children.append(args.id)
            parent_entry["children"] = children
            _update_md_children(agents_dir, parent_entry)

        store.save(data)

    print(f"Spawned agent '{args.id}' under '{args.parent}'")


def cmd_status(args):
    """Update task status."""
    agents_dir = TreeStore.find_agents_dir(os.getcwd())
    if agents_dir is None:
        print("Error: No .claude-agents/ directory found. Run 'init' first.")
        sys.exit(1)

    store = TreeStore(agents_dir)

    with store.lock():
        data = store.load()
        agents = data["agents"]

        if args.id not in agents:
            print(f"Error: Agent '{args.id}' not found.")
            sys.exit(1)

        # Blocked status requires --blocked-by
        if args.new_status == "blocked":
            if not args.blocked_by:
                print("Error: --blocked-by is required when setting status to 'blocked'.")
                sys.exit(1)
            if args.blocked_by not in agents:
                print(f"Error: Blocking agent '{args.blocked_by}' not found.")
                sys.exit(1)
            # Circular dependency check
            if _has_circular_block(data, args.id, args.blocked_by):
                print(f"Error: Circular dependency detected: "
                      f"'{args.blocked_by}' is already blocked by '{args.id}' "
                      f"(directly or transitively).")
                sys.exit(1)

        now = datetime.now(timezone.utc).isoformat()
        agent_entry = agents[args.id]

        # Update tree.json
        agent_entry["status"] = args.new_status
        agent_entry["updated"] = now

        if args.new_status == "blocked":
            agent_entry["blocked_by"] = args.blocked_by
        else:
            # Clear blocked_by when leaving blocked status
            agent_entry["blocked_by"] = None

        # Update MD frontmatter
        file_path = os.path.join(agents_dir, agent_entry["file"])
        with open(file_path) as f:
            text = f.read()
        meta, body = parse_frontmatter(text)
        meta["status"] = args.new_status
        meta["updated"] = now

        if args.new_status == "blocked":
            meta["blocked_by"] = args.blocked_by
        else:
            meta["blocked_by"] = "null"

        with open(file_path, "w") as f:
            f.write(write_frontmatter(meta, body))

        store.save(data)

    print(f"Updated '{args.id}' status to '{args.new_status}'")

    # Check if all siblings are done
    parent_id = agent_entry.get("parent", "root")
    if parent_id != "root" and args.new_status == "done":
        parent = agents.get(parent_id)
        if parent:
            sibling_ids = parent.get("children", [])
            all_done = all(
                agents.get(sid, {}).get("status") == "done"
                for sid in sibling_ids
            )
            if all_done:
                print(f"Tip: All children of '{parent_id}' are done. "
                      f"Consider marking it as done too.")


def cmd_read(args):
    """Read and display a task's MD file."""
    agents_dir = TreeStore.find_agents_dir(os.getcwd())
    if agents_dir is None:
        print("Error: No .claude-agents/ directory found. Run 'init' first.")
        sys.exit(1)

    store = TreeStore(agents_dir)
    data = store.load()

    if args.id not in data["agents"]:
        print(f"Error: Agent '{args.id}' not found.")
        sys.exit(1)

    file_path = os.path.join(agents_dir, data["agents"][args.id]["file"])
    with open(file_path) as f:
        print(f.read())


def cmd_tree(args):
    """Display the task tree."""
    agents_dir = TreeStore.find_agents_dir(os.getcwd())
    if agents_dir is None:
        print("Error: No .claude-agents/ directory found. Run 'init' first.")
        sys.exit(1)

    store = TreeStore(agents_dir)
    data = store.load()

    print(f"{data['objective']} [objective]")

    # Get root-level agents
    root_children = data.get("root_children", [])
    # Also find agents with parent "root" not in root_children
    for agent_id, agent in data["agents"].items():
        if agent.get("parent") == "root" and agent_id not in root_children:
            root_children.append(agent_id)

    _print_tree_level(data, root_children, "", args, agents_dir)


def cmd_log(args):
    """Append a timestamped log entry to an agent's MD file."""
    agents_dir = TreeStore.find_agents_dir(os.getcwd())
    if agents_dir is None:
        print("Error: No .claude-agents/ directory found. Run 'init' first.")
        sys.exit(1)

    store = TreeStore(agents_dir)

    with store.lock():
        data = store.load()
        agents = data["agents"]

        if args.id not in agents:
            print(f"Error: Agent '{args.id}' not found.")
            sys.exit(1)

        now = datetime.now(timezone.utc).isoformat()
        agent_entry = agents[args.id]

        file_path = os.path.join(agents_dir, agent_entry["file"])
        with open(file_path) as f:
            text = f.read()

        meta, body = parse_frontmatter(text)
        meta["updated"] = now

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        log_line = f"\n### {timestamp}\n{args.message}\n"
        body = body.rstrip("\n") + "\n" + log_line

        with open(file_path, "w") as f:
            f.write(write_frontmatter(meta, body))

        agent_entry["updated"] = now
        store.save(data)

    print(f"Logged to '{args.id}'")


def _not_implemented(args):
    """Stub handler for unimplemented subcommands."""
    print("Not implemented")
    sys.exit(1)


def build_parser():
    """Build and return the argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="agent-tree",
        description="Claude Agents Plugin - Task tree management",
    )
    subparsers = parser.add_subparsers(dest="command")

    # init
    p_init = subparsers.add_parser("init", help="Initialize a new agent tree")
    p_init.add_argument("objective", help="Root objective for the tree")
    p_init.add_argument("--force", action="store_true", help="Overwrite existing tree")
    p_init.set_defaults(func=cmd_init)

    # spawn
    p_spawn = subparsers.add_parser("spawn", help="Spawn a new agent task")
    p_spawn.add_argument("id", help="Task ID")
    p_spawn.add_argument("--parent", required=True, help="Parent task ID")
    p_spawn.add_argument("--title", required=True, help="Task title")
    p_spawn.add_argument("--objective", required=True, help="Task objective")
    p_spawn.add_argument("--tags", nargs="*", default=[], help="Task tags")
    p_spawn.add_argument(
        "--max-agents", type=int, default=50, help="Max concurrent agents"
    )
    p_spawn.add_argument("--force", action="store_true", help="Force spawn")
    p_spawn.set_defaults(func=cmd_spawn)

    # status
    p_status = subparsers.add_parser("status", help="Update task status")
    p_status.add_argument("id", help="Task ID")
    p_status.add_argument(
        "new_status",
        choices=["pending", "working", "blocked", "done", "failed", "cancelled"],
        help="New status",
    )
    p_status.add_argument("--blocked-by", help="ID of blocking task")
    p_status.set_defaults(func=cmd_status)

    # update
    p_update = subparsers.add_parser("update", help="Update task metadata")
    p_update.add_argument("id", help="Task ID")
    p_update.add_argument("--title", help="New title")
    p_update.add_argument("--objective", help="New objective")
    p_update.add_argument("--tags", nargs="*", help="New tags")
    p_update.set_defaults(func=_not_implemented)

    # log
    p_log = subparsers.add_parser("log", help="Add a log entry")
    p_log.add_argument("id", help="Task ID")
    p_log.add_argument("message", help="Log message")
    p_log.set_defaults(func=cmd_log)

    # tree
    p_tree = subparsers.add_parser("tree", help="Display the task tree")
    p_tree.add_argument("--verbose", action="store_true", help="Verbose output")
    p_tree.add_argument("--tag", help="Filter by tag")
    p_tree.set_defaults(func=cmd_tree)

    # read
    p_read = subparsers.add_parser("read", help="Read a task")
    p_read.add_argument("id", help="Task ID")
    p_read.set_defaults(func=cmd_read)

    # complete
    p_complete = subparsers.add_parser("complete", help="Mark task as complete")
    p_complete.add_argument("id", help="Task ID")
    p_complete.add_argument("--summary", required=True, help="Completion summary")
    p_complete.set_defaults(func=_not_implemented)

    # fail
    p_fail = subparsers.add_parser("fail", help="Mark task as failed")
    p_fail.add_argument("id", help="Task ID")
    p_fail.add_argument("--reason", required=True, help="Failure reason")
    p_fail.set_defaults(func=_not_implemented)

    # delete
    p_delete = subparsers.add_parser("delete", help="Delete a task")
    p_delete.add_argument("id", help="Task ID")
    p_delete.add_argument(
        "--cascade", action="store_true", help="Delete children too"
    )
    p_delete.set_defaults(func=_not_implemented)

    # context
    p_context = subparsers.add_parser("context", help="Show task context")
    p_context.add_argument("id", help="Task ID")
    p_context.set_defaults(func=_not_implemented)

    # run
    p_run = subparsers.add_parser("run", help="Run a task")
    p_run.add_argument("id", help="Task ID")
    p_run.set_defaults(func=_not_implemented)

    # validate
    p_validate = subparsers.add_parser("validate", help="Validate a task")
    p_validate.add_argument("id", help="Task ID")
    p_validate.set_defaults(func=_not_implemented)

    # sync
    p_sync = subparsers.add_parser("sync", help="Sync tree state")
    p_sync.set_defaults(func=_not_implemented)

    return parser


def main():
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
