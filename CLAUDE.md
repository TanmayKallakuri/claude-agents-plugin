# Claude Agents Plugin

Agent orchestrator for Claude Code. Breaks complex tasks into tracked sub-agents with MD file trees.

## Quick Start

```bash
# Initialize in a project
python3 ~/.claude/skills/claude-agents-plugin/agent_tree.py init "Build user auth system"

# Spawn agents
python3 ~/.claude/skills/claude-agents-plugin/agent_tree.py spawn auth-api --parent root --title "Auth API" --objective "Build login/signup endpoints" --tags backend

# Track progress
python3 ~/.claude/skills/claude-agents-plugin/agent_tree.py log auth-api "Implemented /login endpoint"
python3 ~/.claude/skills/claude-agents-plugin/agent_tree.py status auth-api working

# View tree
python3 ~/.claude/skills/claude-agents-plugin/agent_tree.py tree --verbose

# Complete
python3 ~/.claude/skills/claude-agents-plugin/agent_tree.py complete auth-api --summary "All endpoints working with JWT"
```

## Running Tests

```bash
cd ~/.claude/skills/claude-agents-plugin
python3 -m pytest tests/ -v
```

## Architecture

- `agent_tree.py` — Single-file CLI, zero external deps (stdlib only, Python 3.9+)
- `skills/orchestrate.md` — Claude Code skill that teaches Claude to use the CLI
- `.claude-agents/` — Created per-project, contains tree.json + agent MD files

## Commands

| Command | Description |
|---------|-------------|
| init | Initialize .claude-agents/ directory |
| spawn | Create a new agent task |
| status | Update agent status |
| log | Append timestamped log entry |
| update | Modify title, objective, tags |
| complete | Mark done with summary |
| fail | Mark failed with reason |
| delete | Remove agent (--cascade for children) |
| read | Display agent's MD file |
| tree | Show hierarchical tree view |
| context | Show parent chain, blockers, siblings |
| validate | Check tree integrity |
| sync | Reconcile tree.json with MD files |
