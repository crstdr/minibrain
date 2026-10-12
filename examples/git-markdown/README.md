# Git/Markdown reference implementation

A concrete implementation of the [operating contract](../../starter/instructions.md), derived from the original lean memory system. **Use or adapt it when it fits; do not migrate merely to match this tree.** These are implementation choices, not an additional product tier.

Requires available Git and Python 3, in a normal dedicated Git working copy. It does not support a linked worktree (.git file), a bare repo, multiple clones or remote locking. The helper's root is the parent of its tools directory. Do not run it here as if this distribution were your personal brain.

## Example local layout

```text
AGENTS.md                 gate first, then adopted contract and local bindings
MEMORY.md                 bounded working index, not history
Map.md                    top-level spaces and legacy subjects
CHANGELOG.md              one outcome per coherent checkpoint
spaces/Project.md         a small memory space; current knowledge and history
tools/kb.py                copy of the supplied helper
.agents/skills/resume/SKILL.md       optional host pointer
.agents/skills/checkpoint/SKILL.md   optional host pointer
CLAUDE.md                 optional verified entrypoint; identical gate first
```

Existing `topics/` and root-level subjects stay supported; no migration is automatic. A new space can grow from `spaces/Project.md` to `spaces/Project/index.md`, with optional child spaces and `assets/` as described in [memory spaces](../../docs/spaces.md). Do not create empty structure just to match an example, copy root controls into spaces, or hide pending work in a child cockpit. Inventory legacy files such as MINIBRAIN.md rather than silently dropping their knowledge.

Managed Markdown is root *.md, topics/**/*.md and spaces/**/*.md; it must not be ignored. Root-relative qualified wikilinks accept sections/display text: `[[spaces/Project#Current status|Project]]`. A logical space path without `.md` resolves to its note or folder index; both existing is an error. A path ending in `.md` names that exact file. Bare names remain supported for unambiguous legacy non-space targets, not spaces (even when unique today). Spaces and their assets do not enter that legacy basename namespace. Bare reserved control names prefer the root file; use an exact path when a supporting copy is intended. Repeated names inside spaces are supported through their qualified paths. Legacy non-reserved basenames outside spaces retain the uniqueness guard. Links containing absolute paths, `.` or `..` segments are not accepted. The checker verifies Markdown targets, not section anchors or ordinary Markdown/asset links; verify those separately. General wikilink validation still scans fenced examples as in the legacy checker; fence exclusion applies to new space registrations, not every link.

Top-level spaces register once in root Map.md. Children register once in their containing space's index under exact `## Spaces`, using leading `- [[path]]` entries. Related links outside that section do not register ownership. Every non-asset Markdown file is a child space, placed directly in the folder or under an optional `spaces/` namespace. A folder containing canonical children needs its own index; a `spaces/` namespace must not have one. The space names `assets` and `spaces` are reserved case-insensitively; `index.md` is a folder-space entrypoint, not a namespace note. Registrations must be outside fenced examples; duplicate active `## Spaces` sections and entries that are not direct child spaces are refused. Legacy root/topics Markdown still registers in root Map.md with its original leading `- [[basename]]` spelling; section/display links are not additional legacy registrations. Logical space links survive note-to-folder growth; exact-file links and other relocations still need updates.

Supporting material can use work/, sources/ or archive/ outside spaces, or a space's optional assets/ directory. Use the literal lowercase `spaces/` and `assets/` spellings for these reference bindings. Space assets are data, not canonical child spaces: Markdown assets are not registered and their contents are not checked for wikilinks. Markdown inside assets is still checked for regular UTF-8 file/ignore boundaries. Never place root control filenames (AGENTS.md, CLAUDE.md, MEMORY.md, Map.md, CHANGELOG.md) inside spaces, including assets; the guard is case-insensitive and source copies need a non-entrypoint name such as AGENTS.md.example. Binary contents/privacy, ignored or missing non-Markdown assets and external availability are not validated. Record and manually verify required attachment retention/portability under the user's policy. Any staged change under spaces/, including binary assets, requires the root outcome changelog. Legacy topics/ retains its Markdown-only changelog gate; it has no new asset/folder-space semantics.

This reference requires ordinary UTF-8 Markdown files contained in the repository, not symlinks, special files or symlinked managed directories. A deliberately external store needs an explicit alternative binding; it must not masquerade as knowledge contained in this Git history.

## Install the rules and concrete bindings

For a new installation, put the [core contract](../../starter/instructions.md) in the chosen local instruction source (AGENTS.md here), adding the [shared-writer module](../../starter/shared-writers.md) only if overlap is possible, then record the following local bindings there. A single writer retains the core's overlap trigger without paying for the whole module at startup. For an existing brain, integrate without duplicating or overriding its compatible authoritative instructions. All applicable runtime rules and procedures must be local.

The core starts with `<before_you_act>`: when adopting it as AGENTS.md, keep that entire block first, before the title and local bindings. Recommend the same first-position block in CLAUDE.md if that entrypoint is used. Preserve existing rules and obtain approval before changing shared instructions. [Setup](../../docs/setup.md#4-install-a-self-contained-local-contract) owns the loading and mirror rules; neither these filenames nor an unverified import is compulsory for another host.

Example bindings to adapt:

- **Instruction source:** AGENTS.md, including the authoritative gate at its start. Record CLAUDE.md as a gate mirror if used; compare both when either changes. Host pointers refer here, not to an online distribution.
- **Working index:** MEMORY.md; at most 150 lines and 12 one-line open threads. Thread length above 400 characters warns. These are tunable reference values; change the helper constants and local rule together if appropriate.
- **Knowledge and lookup:** spaces/ for new installations; preserve existing topics/ or root subjects. Map.md lists top-level spaces once, child indexes list their direct spaces under `## Spaces`, and legacy topics remain in Map.md. Link spaces only by root-relative qualified path, even when unique today. Current status at top, newest-first dated history below. Related links only when useful.
- **Adoption:** keep the source URL, adopted release/ref and exact source commit when known, date, and local adaptations/reasons in these bindings or one linked canonical record. Read it before an upgrade; preserve local changes rather than replacing this file. [Setup](../../docs/setup.md#record-adoption-and-preserve-adaptations) owns the comparison procedure.
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

- **<Subject> — <state / waiting on whom>** (evidence YYYY-MM-DD). Next: <one action>. Hold: <only a genuine dependency>. Source: [[spaces/Project#Current status]].
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

## Spaces

- [[spaces/Project]] — purpose, current commitments and durable decisions.
```

Each top-level space is registered exactly once, at the start of its own line. The index of a folder space owns its children's registrations, not root Map.md. Control files and supporting material are not space registrations. Existing root/topics subjects keep their root Map registrations.

### spaces/Project.md

```markdown
# Project

## Current status

<What is true now, basis/evidence dates, unknowns and actionable pending work.>

## History

### YYYY-MM-DD

<Durable decision/outcome; explicitly identify a superseded account when material.>
```

### A folder-space index, when needed

After a deliberate promotion, root Map.md can keep `[[spaces/Project]]`: it now resolves to the folder index. The folder entrypoint `spaces/Project/index.md` may contain:

```markdown
# Project

## Purpose

<Scope of knowledge this space owns.>

## Current status

<Current account, evidence, unknowns; actionable work remains visible at root.>

## Spaces

- [[spaces/Project/spaces/Goals]] — a child space, created only when needed.

## Supporting material

<Relevant asset links, provenance and retention policy; omit if empty.>

## History

<Dated material changes, or links to their canonical detailed history.>
```

Every non-asset Markdown file, including a split-out history note, registers once under `## Spaces`; links under History or other sections do not register it. Never move canonical notes into `assets/` to satisfy the checker. The same shape can recur for a child folder. Do not create placeholder children or use the literal template links in an installation without real targets. Repeated `index.md` filenames require qualified references. Root instructions, working index, changelog and lock remain shared; local space context is data, not a second command hierarchy.

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

Use the equivalent one-sentence checkpoint pointer. Do not prepend the gate to these skill pointers or displace required frontmatter.

For a host that reads CLAUDE.md, supports `@AGENTS.md` imports and does **not** already load AGENTS.md, [CLAUDE.md.example](CLAUDE.md.example) is a complete small entrypoint: the identical gate block first, then `@AGENTS.md`. Its `.example` suffix distinguishes this distribution example from an installed brain. Rename/copy only into the user's chosen installation when appropriate, and preserve any existing host rules after the gate. If the host already loads AGENTS.md, omit the redundant import; create CLAUDE.md only if needed. If it cannot import, verify an explicit startup read instead.

A manual prompt naming the local instruction file is a valid explicit entrypoint; verify the agent actually reads that file.

The authoritative gate is in the adopted AGENTS.md in this example; the CLAUDE.md block is its maintained mirror. Compare those blocks when changing them. The full operating contract remains in AGENTS.md. Distribution tests check the starter/example blocks, not arbitrary installed brains or host execution. An installation that has not adopted the gate is not rejected by kb.py.

Unlike the original helper, this reference refuses symlinked Markdown, including CLAUDE.md → AGENTS.md. Propose a regular entrypoint with the gate and verified pointer rather than silently replacing a working symlink; preserve target instructions and confirm any existing-installation change. Resolve distribution-relative links in adopted instructions to real local targets, and omit a missing module's link while keeping its trigger.

## Install and verify the helper

Copy [tools/kb.py](tools/kb.py) to the selected brain's tools/kb.py, not a nested tools directory whose parent is the wrong root. The helper uses only the standard library and never installs packages.

Before `git init`, inspect `git rev-parse --show-toplevel` from the target and distinguish “not a repository” from another Git failure. Refuse accidental nesting; resolve intended integration with the user. Keep other sessions read-only during setup.

Stage the new files by name, inspect the full staged diff and run `python3 tools/kb.py check --staged`. Before the very first commit, `no commits yet` is the one expected PROBLEM; initial dirty/staged warnings are also expected. Fix every other problem. Commit the installation once and run `python3 tools/kb.py check` again. Initial installation is sole-writer; do not overlap during this bootstrap exception.

For later checkpoints no PROBLEM is expected. Dirty/staged warnings for your own in-flight update and your own held lock are expected; known assigned foreign work remains untouched. Warnings do not change the exit code: the agent must interpret them. Unexpected dirt blocks dependent writes under the contract.

## Exactly what the tool does

- **check** is a read-only working-tree diagnostic for resume and post-save checks. Checks normal root, required controls, ordinary file boundaries, line/thread caps, heading uniqueness/order, canonical Markdown link targets, unambiguous names, parent-space/legacy-map registrations, ignored managed Markdown, Git state and the staged-changelog requirement.
- **check --staged** validates Markdown content and modes from the Git index—the prospective commit. It cannot resolve links through untracked topics or use unstaged repairs to hide a broken commit. Use this before every commit, not `check` alone. Both modes report working-tree dirt without changing it; intentionally uncommitted foreign work remains outside the proposed commit. Neither mode decides whether omissions are semantically important, so inspect the full scoped diff and verify that all your intended changes were saved.
- Both modes reject symlink/special-file Markdown and unsupported ignore-rule checks rather than silently passing. `check` also rejects symlinked managed directories; it does not follow them. Snapshot validation is cooperative, not an adversarial filesystem sandbox.
- It does **not** prove space/topic status/history ordering, section-anchor or ordinary asset-link validity, attachment completeness/privacy, evidence truth, capture completeness, agent compliance or confidentiality. History links in CHANGELOG.md are intentionally not checked.
- **lock** atomically creates a persistent cooperative directory, refuses a nonempty index and issues a seat label with a 128-bit random acquisition component. It does not enforce all Git operations or verify that a caller is a live seat. Failed metadata creation or failed safe rollback is explicitly reported as a retained/incomplete lock, never success.
- **unlock** checks the exact label; **--force** is mechanical and requires the user's recovery decision. Unexpected lock contents are preserved even under force. A label is not a security credential; unrestricted writers could bypass this protocol.
- These original-derived checks now distinguish working state from the prospective commit, refuse unsupported roots/worktrees and unsafe file/lock shapes, preserve unexpected lock contents, and fail visibly if required inspection is unavailable. The staged changelog gate requires presence, not proof of a new/meaningful outcome. Topic status/history ordering and semantic completeness still require an agent's check.

Use [A1–A7](../../docs/acceptance.md) and the shared-writer checks on disposable data. Passing helper tests alone is not full installation acceptance.
