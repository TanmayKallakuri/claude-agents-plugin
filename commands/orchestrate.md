---
name: orchestrate
description: Break down a complex task into tracked sub-agents. Analyzes the existing project first, then decomposes into parallel workstreams with dependency management.
user_invocable: true
---

# /orchestrate

Break down the current task into tracked sub-agents.

## Usage

```
/orchestrate [objective]
```

If no objective is provided, use the most recent user request from the conversation.

## What This Does

1. **Analyzes the existing project** — scans codebase, understands tech stack, finds relevant code
2. **Reviews conversation context** — picks up decisions, constraints, preferences discussed
3. **Presents a decomposition plan** — shows what will be modified vs created, waits for confirmation
4. **Spawns tracked agents** — each with full project context, safety rules, and progress tracking
5. **Manages dependencies** — sets blocking relationships between agents

## Examples

```
/orchestrate Build user authentication with JWT
/orchestrate Add payment processing with Stripe
/orchestrate Refactor the database layer to use repositories
```

## Under the Hood

Uses `agent_tree.py` CLI to manage a `.claude-agents/` directory in the project root containing:
- `tree.json` — master index of all agents and relationships
- `objective.md` — root objective
- `{agent-id}.md` — individual agent files with YAML frontmatter and logs
