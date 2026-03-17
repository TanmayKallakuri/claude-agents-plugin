# Claude Agents Plugin

Agent orchestration for Claude Code. Breaks complex tasks into tracked, parallel sub-agents with markdown file trees. Works in both fresh and existing projects — always understands the codebase before making changes.

## How It Works

When you describe a complex task, this plugin:

1. **Understands first** — Scans the project structure, tech stack, and existing code
2. **Reviews context** — Picks up conversation decisions, constraints, preferences
3. **Confirms with you** — Shows what it found and how it plans to decompose the task
4. **Spawns tracked agents** — Each with full project context and safety rules
5. **Manages dependencies** — Agents can block/unblock each other
6. **Tracks progress** — Living markdown files with timestamped logs

## Quick Start

```bash
# Initialize in a project
python3 agent_tree.py init "Build user auth system"

# Spawn agents
python3 agent_tree.py spawn auth-api \
  --parent root --title "Auth API" \
  --objective "Build login/signup endpoints" --tags backend

# Track progress
python3 agent_tree.py status auth-api working
python3 agent_tree.py log auth-api "Implemented /login endpoint"

# View tree
python3 agent_tree.py tree --verbose

# Complete
python3 agent_tree.py complete auth-api --summary "All endpoints working"
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `init` | Initialize `.claude-agents/` directory |
| `spawn` | Create a new agent task |
| `status` | Update agent status (pending/working/blocked/done/failed/cancelled) |
| `log` | Append timestamped log entry |
| `update` | Modify title, objective, tags |
| `complete` | Mark done with summary |
| `fail` | Mark failed with reason |
| `delete` | Remove agent (`--cascade` for children) |
| `read` | Display agent's markdown file |
| `tree` | Show hierarchical tree view (`--verbose` for logs, `--tag` to filter) |
| `context` | Show parent chain, blockers, siblings |
| `validate` | Check tree integrity |
| `sync` | Reconcile tree.json with markdown files |

## Architecture

```
claude-agents-plugin/
├── .claude-plugin/          # Plugin manifest
│   ├── plugin.json
│   └── marketplace.json
├── agents/                  # Agent definitions
│   └── orchestrator.md      # The orchestrator agent
├── skills/                  # Skills
│   └── orchestrate/
│       └── SKILL.md         # Orchestration skill
├── commands/                # Slash commands
│   └── orchestrate.md       # /orchestrate command
├── agent_tree.py            # Single-file CLI (zero deps, Python 3.9+)
├── tests/                   # 186 tests
├── AGENTS.md                # Agent documentation
└── CLAUDE.md                # This file
```

## Per-Project Directory (`.claude-agents/`)

Created in any project when you run `init`:

```
.claude-agents/
├── tree.json                # Master index of all agents
├── objective.md             # Root objective
├── auth-api.md              # Root-level agent
├── auth-api/                # Subfolder created when agent gets children
│   ├── auth-api.md          # Parent moves here
│   ├── login.md             # Child agent
│   └── signup.md            # Child agent
```

## Safety

- Always reads existing code before making changes
- Extends existing files instead of creating duplicates
- Matches project conventions (naming, structure, patterns)
- Every sub-agent receives full project + conversation context
- Max 4 levels deep, max 50 agents, max 7 spawned at once

## Running Tests

```bash
cd ~/.claude/skills/claude-agents-plugin
python3 -m pytest tests/ -v
```
