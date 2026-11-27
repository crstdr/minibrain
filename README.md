<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/minibrain-logo-dark.svg">
    <img alt="Minibrain" src="assets/minibrain-logo.svg" width="128">
  </picture>
</p>

# Minibrain

**Drop-in, modular working memory for dependable AI agents.**

Each brain is a plain folder with its own Git history. The agent keeps that memory organised, carries its goals, decisions and unfinished work across sessions and context compactions, and tracks the decisions that need your judgment.

Minibrain is minimal by design. A short instruction set says what memory must preserve and leaves the organising to the model.

One prompt adds a brain to any folder, and there is no server to run. Several agents can share one brain, saving one at a time, and with RepoPrompt CE you can link brains into teams.

## Installation

Open the folder you want to equip with minibrain in your preferred coding-agent tool—Claude Code, Codex, OpenCode, pi, or an agent-enabled editor—and prompt:

> Update this folder with the memory system from https://github.com/crstdr/minibrain.

## Features

- **Adapts to your folder.** Starts fresh or builds on existing instructions, conventions and knowledge.
- **Local files, Git history.** The supplied setup uses a local Git repository to track changes, inspect history and recover earlier saved versions. GitHub isn’t required.
- **Principles over rigid templates.** Defines what memory must preserve and provides concrete starting points, while leaving organisation and adaptation to the agent’s judgment.
- **Continuity beyond facts.** Carries goals, decisions, permission conditions and unfinished work across sessions.
- **Agent-maintained.** Guides the agent to keep memory current and useful as its responsibilities grow.
- **Human judgment where it matters.** Tracks decisions waiting on you and notable outcomes awaiting your acknowledgment.
- **Collections primitive.** Scales a brain to support large sets of related items: dependencies, shared assessments, governed priorities. Optional; still plain local files.
- **[RepoPrompt CE](https://github.com/repoprompt/repoprompt-ce) bonus.** Optional overseer guidance helps coordinate multiple agent lanes while preserving responsibilities, progress and pending decisions across sessions.

## Plugins (beta)

The optional [minibrain app](plugins/app/SETUP.md) (alpha) shows a brain's priorities, dependencies and decisions (Roadmap) and your RepoPrompt CE agents and who oversees whom (Agents Map). See [plugins](plugins/README.md).

## For agents

- Install/adapt: [SETUP.md](SETUP.md).
- Upgrade: read local instructions and adoption record, then [Upgrading](SETUP.md#upgrading).
- Add a plugin: [plugins/README.md](plugins/README.md).
- Read source online or in a temporary checkout outside the destination.
- After installation, follow local instructions—not this repository.

---

[MIT license](LICENSE).
