# Agents

## orchestrator

**Purpose:** Decomposes complex development tasks into tracked, parallel sub-agents with dependency management.

**When to use:**
- Multi-step feature implementation (3+ workstreams)
- Parallelizable work across different concerns (API, DB, UI, tests)
- Any task that benefits from decomposition and progress tracking

**How it works:**
1. Analyzes the existing project (codebase, tech stack, patterns)
2. Reviews conversation context (decisions, constraints, preferences)
3. Presents understanding and decomposition plan to user
4. Spawns tracked agents with full project context
5. Manages dependencies between agents
6. Monitors progress via hierarchical tree

**Tools:** Read, Grep, Glob, Bash, Agent, Write, Edit

**Invoke:** `/orchestrate` or describe a complex task naturally
