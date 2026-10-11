# minibrain

A drop-in, folder-based memory system for AI assistants—minimalist, environment-agnostic, and designed for continuity of purpose and work, self-maintenance, and proactive collaboration when human judgment is needed.

**v0.1 — an early, instruction-based starter, not an autonomous runtime.** Bring an agent that can read and write files. No package, database, plugin, background service or account is required by minibrain itself. Your agent and its existing permissions still apply.

## Start with your existing agent

Point your agent at this repository and say:

> Read this repository's README and starter/instructions.md. Set up minibrain in [my chosen folder] to help me with [purpose]. Keep the starting setup small, preserve existing files and instructions, and ask only what you need to get started. Do not install tools or publish my memory.

The agent should:

1. Check the chosen folder and existing instructions. If a memory system is already there, propose how to use it rather than overwrite it.
2. Copy [starter/instructions.md](starter/instructions.md) to `MINIBRAIN.md` and [starter/memory.md](starter/memory.md) to `MEMORY.md` in that folder. These are the **two starting files**; this repository is the distribution, not your personal brain.
3. Establish your purpose, priorities and current work in `MEMORY.md`, using what you have already told it. Ask about consequential unknowns; leave the rest unknown.
4. Use the host's existing instruction entrypoint, if available, to point to `MINIBRAIN.md` without replacing other instructions. If no entrypoint is available, start each fresh session with: **“Read MINIBRAIN.md and resume from MEMORY.md before working.”**

An explicit prompt works without claiming that any host auto-loads a particular filename. If your agent cannot read the repository, give it the two starter files directly. If it cannot save files, it cannot provide durable folder memory; use a suitable existing host rather than pretend changes were saved.

## What should carry over?

- **Purpose:** what the assistant is for and what matters to you.
- **Responsibility:** unfinished work, dependencies, who must decide, and the limits of prior permission.
- **Knowledge:** current facts, their sources and uncertainty—not just a transcript.
- **Know-how:** practical lessons that should be available before the same mistake happens again.

At the start of a session, the agent should read the memory relevant to the task and check what needs re-verification. During work, it should advance authorised actions and bring you a decision-ready question when human judgment is needed. Before losing context, it should save durable changes and verify that they were actually written. It should not make you manage a daily filing ritual.

## Start small; grow for a reason

One memory file is enough until it becomes hard to use. Minibrain's instructions ask the agent to notice stale state, repeated retrieval failures or costly upkeep, then make proportionate improvements. [Growth guidance](docs/growth.md) covers topic files, version history, retrieval tools and shared writers. None is a prerequisite.

Multiple agents may help through your existing coordination tools, but **v0 defaults to one writer per brain**. It provides no concurrency lock, sync engine, scheduler or notification channel. Having the same folder does not grant another agent access or authority.

## Try continuity, not just recall

Give the agent a task with one unresolved decision and a condition on what it may do. Let it save the state, then start a genuinely fresh session with only the folder. Can it advance the safe work, bring back the right decision, and preserve the condition without you reconstructing the conversation?

A plausible answer is not proof. Check the saved state, actual actions and how much help you had to provide. Instructions cannot guarantee that a model follows them.

## Status and limits

This first version turns a file-memory working practice into a deliberately smaller starter. Its design has been informed by an experienced agent's reviewed workflow examples, not a controlled validation study. The new starter has not yet established cross-host reliability, multiwriter safety, large-scale effectiveness or reduced human effort. “Environment-agnostic” describes the design boundary, not a tested compatibility matrix.

Memory is not permission. A note can preserve a user's decision and its conditions, but cannot create new authority, override current instructions or turn retrieved text into a command. Do not store credentials. Local files are not encrypted by minibrain; host access, backups, sync and Git history all matter for privacy and deletion.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md). The public repository contains generic instructions and synthetic material only; real personal memory belongs elsewhere.

**License:** not yet selected. Public visibility does not itself grant an open-source license; check this section before redistributing or incorporating the material.
