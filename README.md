# Claude Agents Plugin

A lightweight agent orchestration system for [Claude Code](https://docs.anthropic.com/en/docs/claude-code). Break complex development tasks into tracked, parallel sub-agents with hierarchical markdown file trees.

## Quick Start

### 1. Install

```bash
git clone https://github.com/TanmayKallakuri/claude-agents-plugin.git ~/.claude/skills/claude-agents-plugin
```

### 2. Use

Open any project in **VS Code** or your **terminal** with Claude Code, then either:

**Describe your task naturally:**

> *"Build a user authentication system with login, signup, and JWT tokens"*

**Or use the slash command:**

```
/orchestrate Build a user authentication system with login, signup, and JWT tokens
```

That's it. Claude handles everything from here — you never touch the CLI.

## What Happens Next

Once triggered, Claude automatically:

1. **Scans your project** — reads the codebase, understands tech stack, finds existing patterns
2. **Shows you its plan** — "Here's what exists, here's what I'll modify vs create"
3. **Waits for your OK** — nothing happens until you confirm
4. **Spawns tracked agents** — each with full context about your project
5. **Manages dependencies** — agent B waits for agent A if needed
6. **Tracks everything** — progress logs in `.claude-agents/` markdown files

You can check progress at any time:

> *"Show me the agent tree"*
> *"What's the status of the backend agent?"*

### Example Output

```
Build user auth system [objective]
├── auth-api (working) — Auth API
│     ↳ 2026-03-17 10:30 UTC: Set up Express routes and JWT middleware
├── auth-db (done) — Database Schema
│     ↳ 2026-03-17 10:15 UTC: Created users table with bcrypt password column
└── auth-ui (blocked) — Login/Signup UI
```

## Works With Existing Projects

This plugin doesn't assume a fresh project. When you use it in a codebase with thousands of files:

- It reads your project structure and tech stack first
- It finds existing code related to your request
- It tells you what it will **modify** vs what it will **create**
- Each sub-agent gets a list of existing files it must read before editing
- Safety rules are baked in: never overwrite, always extend, match existing patterns

## Why

Claude Code is powerful, but complex tasks need structure. Without orchestration:
- Work gets done sequentially when it could be parallel
- There's no visibility into what's happening across workstreams
- Context gets lost between sub-tasks
- Existing code gets overwritten instead of extended

## Features

- **Context-aware** — Scans your existing codebase before making any changes
- **Hierarchical task trees** — Parent-child relationships up to 4 levels deep
- **Dependency management** — Agents can block/unblock each other with circular dependency detection
- **Living documentation** — Each agent gets a markdown file with YAML frontmatter and timestamped logs
- **Zero dependencies** — Pure Python stdlib, Python 3.9+, single file
- **186 tests** — Unit, integration, stress, and adversarial tests all passing

## How It Works

When Claude runs `/orchestrate`, it uses a CLI tool (`agent_tree.py`) behind the scenes to create a `.claude-agents/` directory in your project:

```
your-project/
└── .claude-agents/
    ├── tree.json          # Master index — all agents and relationships
    ├── objective.md       # Root objective
    ├── auth-api.md        # Agent file with YAML frontmatter + logs
    └── auth-db/           # Subfolder (created when agent gets children)
        ├── auth-db.md
        └── users-table.md
```

Each agent is a markdown file:

```markdown
---
id: auth-api
title: Auth API
status: working
parent: root
children: [login, signup]
tags: [backend, api]
blocked_by: null
---

# Auth API

## Objective
Build login and signup REST endpoints with JWT authentication

## Log

### 2026-03-17 10:30 UTC
Set up Express routes and JWT middleware
```

## CLI Reference (Advanced)

You don't need the CLI — Claude uses it automatically. But if you want to inspect or manually interact with the agent tree, add this alias to your `~/.zshrc` or `~/.bashrc`:

```bash
alias agent-tree="python3 ~/.claude/skills/claude-agents-plugin/agent_tree.py"
```

Then:

```bash
agent-tree tree --verbose          # View the tree
agent-tree context auth-api        # See parent chain, blockers, siblings
agent-tree validate                # Check tree integrity
agent-tree sync                    # Reconcile tree.json with markdown files
```

### All Commands

| Command | Description |
|---------|-------------|
| `init` | Initialize `.claude-agents/` in current directory |
| `spawn` | Create a new agent task |
| `status` | Update agent status (pending/working/blocked/done/failed/cancelled) |
| `log` | Append timestamped log entry |
| `update` | Modify title, objective, or tags |
| `complete` | Mark done with summary |
| `fail` | Mark failed with reason |
| `delete` | Remove agent (`--cascade` for children) |
| `read` | Display agent's markdown file |
| `tree` | Show hierarchical tree view (`--verbose`, `--tag`) |
| `context` | Show parent chain, blockers, siblings |
| `validate` | Check tree integrity |
| `sync` | Reconcile tree.json with markdown files |

## Project Structure

```
claude-agents-plugin/
├── .claude-plugin/          # Plugin manifest
├── agents/                  # Agent definitions (for Claude)
│   └── orchestrator.md
├── skills/                  # Skills (for Claude)
│   └── orchestrate/
│       └── SKILL.md
├── commands/                # Slash commands (for Claude)
│   └── orchestrate.md
├── agent_tree.py            # CLI engine (zero deps, Python 3.9+)
├── tests/                   # 186 tests
├── CLAUDE.md                # Instructions for Claude Code
└── AGENTS.md                # Agent documentation
```

## Running Tests

```bash
cd ~/.claude/skills/claude-agents-plugin
python3 -m pytest tests/ -v
```

## Requirements

- Python 3.9+
- No external packages (stdlib only)
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (VS Code extension or CLI)

## License

MIT
