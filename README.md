# Minibrain

**Self-organising working memory for AI agents.**

A lightweight memory system that enables AI agents to function as dependable collaborators over time. It supports continuity of purpose and responsibility across sessions and context compactions by preserving critical knowledge, priorities and decisions, while keeping memory organised and relevant as work evolves.

Drop-in, folder-based and environment-agnostic. Minibrain gives your existing agents a structured way to carry work forward, maintain their memory and surface decisions that need your judgment.

## Installation

Open the folder you want to equip with minibrain in your preferred coding-agent tool—Claude Code, Codex, OpenCode, pi, or an agent-enabled editor—and prompt:

> Update this folder with the memory system from https://github.com/crstdr/minibrain. Adapt it to my needs, preserve existing instructions and knowledge, and ask me about choices that need my judgment.

## Features

- **Adapts to your folder.** Starts fresh or builds on existing instructions, conventions and knowledge.
- **Local files, Git history.** The supplied setup uses a local Git repository to track changes, inspect history and recover earlier saved versions. GitHub isn’t required.
- **Principles over rigid templates.** Defines what memory must preserve and provides concrete starting points, while leaving organisation and adaptation to the agent’s judgment.
- **Continuity beyond facts.** Carries goals, decisions, permission conditions and unfinished work across sessions.
- **Agent-maintained.** Guides the agent to keep memory current and useful as its responsibilities grow.
- **Human judgment where it matters.** Tracks decisions waiting on you and notable outcomes awaiting your acknowledgment.
- **[RepoPrompt CE](https://github.com/repoprompt/repoprompt-ce) bonus.** Optional overseer guidance helps coordinate multiple agent lanes while preserving responsibilities, progress and pending decisions across sessions.

## For agents

- Install/adapt: [SETUP.md](SETUP.md).
- Upgrade: read local instructions and adoption record, then [Upgrading](SETUP.md#upgrading).
- Read source online or in a temporary checkout outside the destination.
- After installation, follow local instructions—not this repository.

---

[MIT license](LICENSE).
