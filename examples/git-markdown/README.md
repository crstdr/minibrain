# Git/Markdown reference implementation

A concrete implementation of the [operating contract](../../starter/instructions.md), derived from the original lean memory system. **Use or adapt it when it fits; do not migrate merely to match this tree.** These are implementation choices, not an additional product tier.

Requires available Git and Python 3, in a normal dedicated Git working copy. It does not support a linked worktree (.git file), a bare repo, multiple clones or remote locking. The helper's root is the parent of its tools directory. Do not run it here as if this distribution were your personal brain.

## Example local layout

```text
AGENTS.md                 adopted contract plus local bindings
MEMORY.md                 bounded working index, not history
Map.md                    one entry per canonical subject
CHANGELOG.md              one outcome per coherent checkpoint
topics/Project.md         current knowledge and dated history
tools/kb.py                copy of the supplied helper
.agents/skills/resume/SKILL.md       optional host pointer
.agents/skills/checkpoint/SKILL.md   optional host pointer
CLAUDE.md                 optional, only for a verified host entrypoint
```

Root-level topics also work for older installations. Supporting material can use work/, sources/ or archive/ when needed; never create empty structure just to match this example. Keep non-memory work Markdown there rather than at the root, whose Markdown is all managed. Inventory legacy files such as MINIBRAIN.md and integrate or retire/register them rather than silently dropping their knowledge. Every non-reserved Markdown basename must be unique across canonical and tracked supporting Markdown outside dot-folders. Managed Markdown is root *.md plus topics/**/*.md; it must not be ignored. Topic links resolve by basename. The checker verifies targets, not section anchors; verify anchors separately.

This reference requires ordinary UTF-8 Markdown files contained in the repository, not symlinks, special files or symlinked topic directories. A deliberately external store needs an explicit alternative binding; it must not masquerade as knowledge contained in this Git history.

## Install the rules and concrete bindings

For a new installation, put the [core contract](../../starter/instructions.md) in the chosen local instruction source (AGENTS.md here), adding the [shared-writer module](../../starter/shared-writers.md) only if overlap is possible, then record the following local bindings there. A single writer retains the core's overlap trigger without paying for the whole module at startup. For an existing brain, integrate without duplicating or overriding its compatible authoritative instructions. All applicable runtime rules and procedures must be local.

Example bindings to adapt:

- **Instruction source:** AGENTS.md. Host pointers refer here, not to an online distribution.
- **Working index:** MEMORY.md; at most 150 lines and 12 one-line open threads. Thread length above 400 characters warns. These are tunable reference values; change the helper constants and local rule together if appropriate.
- **Knowledge and lookup:** topics/*.md, or existing root topics; Map.md lists each canonical topic once as a leading bare wikilink. Current status at top, newest-first dated history below. Related links only when they add navigation.
- **Outcomes:** CHANGELOG.md, newest first, one dated outcome per checkpoint. Completed entries are additive. Never put an expanding recent-decisions log in MEMORY.md.
- **Startup check:** `python3 tools/kb.py check`. Read AGENTS.md and directly linked handling guidance, MEMORY.md, the latest three changelog entries, and precise source sections for all open threads (plus canonical sources needed for the current request). Follow the contract's readback and consistency rules.
- **Persistence:** re-read edited sources, update knowledge/navigation/index and prepend one outcome; stage intended files by name, inspect `git diff --cached` and `git diff --cached --stat`, run `python3 tools/kb.py check --staged` on the prospective commit, commit once, then run `python3 tools/kb.py check`. Restage/reinspect/recheck after any later edit. Shared writers prefix the commit subject with their seat (for example `Alpha: Record current decision`) for durable attribution. Your own unfinished omission can be corrected/amended before the checkpoint completes; never rewrite completed history or include unknown dirt.
- **Privacy:** fill in the actual user-approved policy. A local repo does not imply permission for any remote. Never commit credentials; minimise sensitive information; exclude caches, generated outputs and private artifacts as appropriate.
- **Writers:** one designated writer unless overlap is needed. When it is, install the shared-writer module, record user-assigned Owners/scopes in MEMORY.md, and bind acquisition/release to `python3 tools/kb.py lock <Seat>` / `python3 tools/kb.py unlock <issued-label>`. Edit only assigned whole-file work; coordinate with the owner within existing authority or obtain user reassignment before crossing scope. Cross-area work belongs to all relevant seats. Acquisition must succeed before shared-memory editing/staging; reread after acquiring and release after post-commit verification. No lock while waiting.
- **Read consistency:** compare HEAD plus lock/unfinished-write signals before/after relevant reads and before action. A version alone cannot detect an uncommitted writer; if uncertainty remains take a brief protected snapshot.

The same commands can be invoked through an existing tool rather than a shell. Check return codes; an unsuccessful lock or validator must stop its dependent commands.

## Content templates, not mandatory filenames

### MEMORY.md

The helper expects these exact headings once, Focus before Open threads. Only `- ` items beneath Open threads until the next level-two heading count; do not hide overflow in tables, later headings or another file.

```markdown
# Working memory

## Focus

<Current goal, evidence date, source; label inference. Empty only if no confident basis.>

## Open threads

- **<Subject> — <state / waiting on whom>** (evidence YYYY-MM-DD). Next: <one action>. Hold: <only a genuine dependency>. Source: [[Project#Current status]].
```

If shared writers are enabled, add a canonical Owners table before Open threads:

```markdown
## Owners

| Area | Seat | Since | Note |
|---|---|---|---|
| <user-assigned scope> | <stable seat> | YYYY-MM-DD | <limits or unverified handoff> |
```

### Map.md

```markdown
# Map

## Topics

- [[Project]] — purpose, current commitments and durable decisions.
```

Each topic is registered exactly once, at the start of its own line. Control files and supporting material are not topic registrations.

### topics/Project.md

```markdown
# Project

## Current status

<What is true now, basis/evidence dates, unknowns and actionable pending work.>

## History

### YYYY-MM-DD

<Durable decision/outcome; explicitly identify a superseded account when material.>
```

### CHANGELOG.md

```markdown
# Changelog

Outcomes, newest first. Completed lines are additive.

YYYY-MM-DD - Established the memory system for the stated purpose.
```

Do not leave placeholder facts, dates or fictional work in a real installation.

### Optional host pointers

For a host that discovers skills at .agents/skills/, the resume pointer can contain:

```markdown
---
name: resume
description: Load this folder's memory before new work.
---
Execute resume exactly as defined in the local AGENTS.md.
```

Use the equivalent one-sentence checkpoint pointer. A verified Claude Code setup may use `@AGENTS.md` in CLAUDE.md. These are examples; do not assume universal discovery or replace existing host instructions. A manual prompt naming the local instruction file is a valid explicit entrypoint.

Unlike the original helper, this reference refuses symlinked Markdown, including CLAUDE.md → AGENTS.md. Where the host supports imports, propose a regular one-line pointer instead; preserve the target instructions and confirm any existing-installation change. Resolve distribution-relative links in adopted instructions to real local targets, and omit a missing module's link while keeping its trigger.

## Install and verify the helper

Copy [tools/kb.py](tools/kb.py) to the selected brain's tools/kb.py, not a nested tools directory whose parent is the wrong root. The helper uses only the standard library and never installs packages.

Before `git init`, inspect `git rev-parse --show-toplevel` from the target and distinguish “not a repository” from another Git failure. Refuse accidental nesting; resolve intended integration with the user. Keep other sessions read-only during setup.

Stage the new files by name, inspect the full staged diff and run `python3 tools/kb.py check --staged`. Before the very first commit, `no commits yet` is the one expected PROBLEM; initial dirty/staged warnings are also expected. Fix every other problem. Commit the installation once and run `python3 tools/kb.py check` again. Initial installation is sole-writer; do not overlap during this bootstrap exception.

For later checkpoints no PROBLEM is expected. Dirty/staged warnings for your own in-flight update and your own held lock are expected; known assigned foreign work remains untouched. Warnings do not change the exit code: the agent must interpret them. Unexpected dirt blocks dependent writes under the contract.

## Exactly what the tool does

- **check** is a read-only working-tree diagnostic for resume and post-save checks. Checks normal root, required controls, ordinary file boundaries, line/thread caps, heading uniqueness/order, managed link targets, unique basenames, map registrations, ignored managed Markdown, Git state and the staged-changelog requirement.
- **check --staged** validates Markdown content and modes from the Git index—the prospective commit. It cannot resolve links through untracked topics or use unstaged repairs to hide a broken commit. Use this before every commit, not `check` alone. Both modes report working-tree dirt without changing it; intentionally uncommitted foreign work remains outside the proposed commit. Neither mode decides whether omissions are semantically important, so inspect the full scoped diff and verify that all your intended changes were saved.
- Both modes reject symlink/special-file Markdown and unsupported ignore-rule checks rather than silently passing. `check` also rejects symlinked managed directories; it does not follow them. Snapshot validation is cooperative, not an adversarial filesystem sandbox.
- It does **not** prove topic status/history ordering, section-anchor validity, evidence truth, capture completeness, agent compliance or confidentiality. History links in CHANGELOG.md are intentionally not checked.
- **lock** atomically creates a persistent cooperative directory, refuses a nonempty index and issues a seat label with a 128-bit random acquisition component. It does not enforce all Git operations or verify that a caller is a live seat. Failed metadata creation or failed safe rollback is explicitly reported as a retained/incomplete lock, never success.
- **unlock** checks the exact label; **--force** is mechanical and requires the user's recovery decision. Unexpected lock contents are preserved even under force. A label is not a security credential; unrestricted writers could bypass this protocol.
- These original-derived checks now distinguish working state from the prospective commit, refuse unsupported roots/worktrees and unsafe file/lock shapes, preserve unexpected lock contents, and fail visibly if required inspection is unavailable. The staged changelog gate requires presence, not proof of a new/meaningful outcome. Topic status/history ordering and semantic completeness still require an agent's check.

Use [A1–A7](../../docs/acceptance.md) and the shared-writer checks on disposable data. Passing helper tests alone is not full installation acceptance.
