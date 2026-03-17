# Claude Agents Plugin

A lightweight agent orchestration system for [Claude Code](https://docs.anthropic.com/en/docs/claude-code). Break complex development tasks into tracked, parallel sub-agents with hierarchical markdown file trees.

When you describe a complex task like *"build an auth system"*, this plugin decomposes it into independent workstreams, spawns tracked agents for each, manages dependencies between them, and logs progress in living markdown files — all while understanding your existing codebase first.

## Why

Claude Code is powerful, but complex tasks need structure. Without orchestration:
- Work gets done sequentially when it could be parallel
- There's no visibility into what's happening across workstreams
- Context gets lost between sub-tasks
- Existing code gets overwritten instead of extended

This plugin solves all of that with a single-file CLI and a skill that teaches Claude when and how to use it.

## Features

- **Context-aware** — Scans your existing codebase before making any changes. Never overwrites, always extends.
- **Hierarchical task trees** — Parent-child relationships up to 4 levels deep, max 50 agents
- **Dependency management** — Agents can block/unblock each other with circular dependency detection
- **Living documentation** — Each agent gets a markdown file with YAML frontmatter and timestamped logs
- **Zero dependencies** — Pure Python stdlib. Works on Python 3.9+. Single file.
- **186 tests** — Unit, integration, stress, and adversarial tests all passing

## Installation

### 1. Clone the plugin

```bash
git clone https://github.com/TanmayKallakuri/claude-agents-plugin.git ~/.claude/skills/claude-agents-plugin
```

### 2. Add the CLI alias

Add this to your `~/.bashrc` or `~/.zshrc`:

```bash
alias agent-tree="agent-tree"
```

Then reload your shell:

```bash
source ~/.zshrc  # or source ~/.bashrc
```

### 3. Verify

```bash
agent-tree --help
```

You should see the CLI help with all 13 commands. Claude Code automatically picks up the skill from `~/.claude/skills/`.

## Usage

### With Claude Code (recommended)

Open any project in Claude Code and describe a complex task:

> *"Build a user authentication system with login, signup, password reset, and JWT tokens"*

Claude will automatically:
1. Scan your project structure and existing code
2. Present a decomposition plan and wait for your confirmation
3. Spawn tracked agents for each workstream
4. Set dependencies between them
5. Execute work in parallel where possible
6. Track progress in `.claude-agents/` markdown files

You can also invoke directly:

```
/orchestrate Add payment processing with Stripe
```

Or ask for status at any time:

> *"Show me the agent tree"*

### With the CLI directly

```bash
# Navigate to your project
cd ~/my-project

# Initialize an agent tree
agent-tree init "Build user auth system"

# Spawn agents
agent-tree spawn auth-api \
  --parent root \
  --title "Auth API" \
  --objective "Build login and signup REST endpoints" \
  --tags backend api

agent-tree spawn auth-ui \
  --parent root \
  --title "Auth UI" \
  --objective "Build login and signup React components" \
  --tags frontend ui

# Set dependencies
agent-tree status auth-ui blocked --blocked-by auth-api

# Log progress
agent-tree log auth-api "Set up Express routes and JWT middleware"
agent-tree status auth-api working

# View the tree
agent-tree tree --verbose
```

**Output:**
```
Build user auth system [objective]
├── auth-api (working) — Auth API
│     ↳ 2026-03-17 10:30 UTC: Set up Express routes and JWT middleware
└── auth-ui (blocked) — Auth UI
```

```bash
# Complete work
agent-tree complete auth-api --summary "All endpoints working with JWT refresh tokens"

# Validate tree integrity
agent-tree validate

# Sync tree.json with markdown files
agent-tree sync
```

## CLI Reference

| Command | Description | Example |
|---------|-------------|---------|
| `init` | Initialize `.claude-agents/` in current directory | `init "Build auth system"` |
| `spawn` | Create a new agent task | `spawn auth-api --parent root --title "Auth API" --objective "Build endpoints" --tags backend` |
| `status` | Update agent status | `status auth-api working` |
| `log` | Append timestamped log entry | `log auth-api "Implemented /login endpoint"` |
| `update` | Modify title, objective, or tags | `update auth-api --title "Auth API v2"` |
| `complete` | Mark done with summary | `complete auth-api --summary "All endpoints working"` |
| `fail` | Mark failed with reason | `fail auth-api --reason "External API unavailable"` |
| `delete` | Remove agent (use `--cascade` for children) | `delete auth-api --cascade` |
| `read` | Display agent's markdown file | `read auth-api` |
| `tree` | Show hierarchical tree view | `tree --verbose --tag backend` |
| `context` | Show parent chain, blockers, siblings | `context auth-api` |
| `validate` | Check tree integrity | `validate` |
| `sync` | Reconcile tree.json with markdown files | `sync` |

### Status lifecycle

```
pending → working → done
                  → failed
       → blocked (requires --blocked-by)
       → cancelled
```

## How It Works

### Per-project directory

When you run `init`, a `.claude-agents/` directory is created in your project:

```
.claude-agents/
├── tree.json          # Master index — all agents and relationships
├── objective.md       # Root objective
├── auth-api.md        # Agent file (flat when no children)
├── auth-api/          # Subfolder (created when agent gets children)
│   ├── auth-api.md    # Parent moves here
│   ├── login.md       # Child agent
│   └── signup.md      # Child agent
```

### Agent markdown format

Each agent is a markdown file with YAML frontmatter:

```markdown
---
id: auth-api
title: Auth API
status: working
parent: root
created: 2026-03-17T10:00:00+00:00
updated: 2026-03-17T10:30:00+00:00
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

### Context-aware orchestration

When triggered in an existing project, the orchestrator:

1. **Reads the conversation** — picks up decisions, constraints, preferences you've discussed
2. **Scans the codebase** — understands project structure, tech stack, existing patterns
3. **Presents its plan** — shows what it found and how it will decompose the task
4. **Waits for confirmation** — you approve before any agents are spawned
5. **Passes full context** to each sub-agent — they know what files exist, what patterns to follow, and what NOT to overwrite

## Project Structure

```
claude-agents-plugin/
├── .claude-plugin/
│   ├── plugin.json          # Plugin manifest
│   └── marketplace.json     # Marketplace metadata
├── agents/
│   └── orchestrator.md      # Orchestrator agent definition
├── skills/
│   └── orchestrate/
│       └── SKILL.md         # Orchestration skill (context-aware decomposition)
├── commands/
│   └── orchestrate.md       # /orchestrate slash command
├── agent_tree.py            # Single-file CLI (zero deps, Python 3.9+)
├── tests/                   # 186 tests
├── AGENTS.md                # Agent documentation
├── CLAUDE.md                # Instructions for Claude Code
├── LICENSE                  # MIT
└── README.md                # This file
```

## Running Tests

```bash
cd ~/.claude/skills/claude-agents-plugin
python3 -m pytest tests/ -v
```

All 186 tests cover:
- YAML frontmatter parsing and roundtrip fidelity
- PID-based file locking and stale lock detection
- Agent spawning, status transitions, and dependency management
- Cascade deletion and tree integrity validation
- Stress tests (50 agents, max depth chains, adversarial inputs)
- End-to-end integration workflows

## Requirements

- Python 3.9+
- No external packages (stdlib only)
- Claude Code (for the skill/agent integration — CLI works standalone)

## License

MIT
