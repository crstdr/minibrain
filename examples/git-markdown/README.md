# Git/Markdown reference implementation

A concrete implementation of the [operating contract](../../starter/instructions.md), derived from the original lean memory system. **Use or adapt it when it fits; do not migrate merely to match this tree.** These are implementation choices, not an additional product tier.

Requires available Git and Python 3.8 or later, in a normal dedicated Git working copy. It does not support a linked worktree (.git file), a bare repo, multiple clones or remote locking. The helper's root is the parent of its tools directory. Do not run it here as if this distribution were your personal brain.

## Example local layout

```text
AGENTS.md                 gate first, then adopted contract and local bindings
MEMORY.md                 bounded working index, not history
Map.md                    top-level spaces and legacy subjects
CHANGELOG.md              one outcome per coherent checkpoint
spaces/Project.md         a small memory space; current knowledge and history
tools/kb.py                copy of the supplied helper
.agents/skills/reflect/SKILL.md      local procedure (or verified explicit-file equivalent)
.agents/skills/resume/SKILL.md       optional host pointer
.agents/skills/checkpoint/SKILL.md   optional host pointer
CLAUDE.md                 optional verified entrypoint; identical gate first
```

Existing `topics/` and root-level subjects stay supported; no migration is automatic. A new space can grow from `spaces/Project.md` to `spaces/Project/index.md`, with optional child spaces and `assets/` as described in [memory spaces](../../docs/spaces.md). Do not create empty structure just to match an example, copy root controls into spaces, or hide pending work in a child cockpit. Inventory legacy files such as MINIBRAIN.md rather than silently dropping their knowledge.

Managed Markdown is root *.md, topics/**/*.md and spaces/**/*.md; it must not be ignored. Root-relative qualified wikilinks accept sections/display text: `[[spaces/Project#Current status|Project]]`. A logical space path without `.md` resolves to its note or folder index; both existing is an error. A path ending in `.md` names that exact file. Bare names remain supported for unambiguous legacy non-space targets, not spaces (even when unique today). Spaces and their assets do not enter that legacy basename namespace. Bare reserved control names prefer the root file; use an exact path when a supporting copy is intended. Repeated names inside spaces are supported through their qualified paths. Legacy non-reserved basenames outside spaces retain the uniqueness guard. Links containing absolute paths, `.` or `..` segments are not accepted. The checker verifies Markdown targets, not section anchors or ordinary Markdown/asset links; verify those separately. General wikilink validation still scans fenced examples as in the legacy checker; fence exclusion applies to new space registrations, not every link.

Top-level spaces register once in root Map.md. Every leading space-link bullet (`- [[spaces/...]]`) in root Map.md is a registration, even under Related or with a section/display suffix; use ordinary Markdown links for non-owning root navigation and verify them separately. Children register once in their containing space's index under exact `## Spaces`, using leading `- [[path]]` entries. In a child index, Related links outside that section do not register ownership. Every non-asset Markdown file is a child space, placed directly in the folder or under an optional `spaces/` namespace. A folder containing canonical children needs its own index; a `spaces/` namespace must not have one. The space names `assets` and `spaces` are reserved case-insensitively; `index.md` is a folder-space entrypoint, not a namespace note. Registrations must be outside fenced examples; duplicate active `## Spaces` sections and entries that are not direct child spaces are refused. Legacy root/topics Markdown still registers in root Map.md with its original leading `- [[basename]]` spelling; section/display links are not additional legacy registrations. Logical space links survive note-to-folder growth; exact-file links and other relocations still need updates.

Supporting material can use work/, sources/ or archive/ outside spaces, or a space's optional assets/ directory. Markdown outside root/topics/spaces must be tracked in Git before the working-tree checker can resolve it as a supporting target. Use the literal lowercase `spaces/` and `assets/` spellings for these reference bindings. Space assets are data, not canonical child spaces: Markdown assets are not registered and their contents are not checked for wikilinks. Markdown inside assets is still checked for regular UTF-8 file/ignore boundaries. Never place root control filenames (AGENTS.md, CLAUDE.md, MEMORY.md, Map.md, CHANGELOG.md) inside spaces, including assets; the guard is case-insensitive and source copies need a non-entrypoint name such as AGENTS.md.example. Binary contents/privacy, ignored or missing non-Markdown assets and external availability are not validated. Record and manually verify required attachment retention/portability under the user's policy. Any staged change under spaces/, including binary assets, requires the root outcome changelog. Legacy topics/ retains its Markdown-only changelog gate; it has no new asset/folder-space semantics.

This reference requires ordinary UTF-8 Markdown files contained in the repository, not symlinks, special files or symlinked managed directories. A deliberately external store needs an explicit alternative binding; it must not masquerade as knowledge contained in this Git history.

## Install the rules and concrete bindings

For a new installation, put the [core contract](../../starter/instructions.md) in the chosen local instruction source (AGENTS.md here), adding the [shared-writer module](../../starter/shared-writers.md) only if overlap is possible, then record the following local bindings there. A single writer retains the core's overlap trigger without paying for the whole module at startup. For an existing brain, integrate without duplicating or overriding its compatible authoritative instructions. All applicable runtime rules and procedures must be local.

The core starts with `<before_you_act>`: when adopting it as AGENTS.md, keep that entire block first, before the title and local bindings. Recommend the same first-position block in CLAUDE.md if that entrypoint is used. Preserve existing rules and obtain approval before changing shared instructions. [Setup](../../docs/setup.md#4-install-a-self-contained-local-contract) owns the loading and mirror rules; neither these filenames nor an unverified import is compulsory for another host.

### Example local bindings

Use the [contract's Local bindings template](../../starter/instructions.md#local-bindings), not a second schema. This example assumes the paths below fit the target; fill the user-specific values from evidence and preserve compatible existing arrangements. Do not copy unresolved placeholders or invent a purpose, policy or adopted revision.

```text
Purpose: <purpose, responsibilities and authority, or their existing canonical record; maintenance limits>
Instructions: AGENTS.md; CLAUDE.md is an identical gate mirror plus verified pointer only if needed; <other applicable handling/standing-rule sources>
Memory: MEMORY.md (working index); Map.md (top-level inventory); spaces/ (knowledge/lessons, or retain existing topics/). Use root-relative qualified space links. Register each space once: leading space-link bullets anywhere in root Map.md register top-level spaces; children register under their parent index's exact ## Spaces. Use ordinary Markdown links for non-owning root Map navigation.
History: CHANGELOG.md (outcomes); each subject's current status first, then newest-first dated material history
Startup budget: 150 index lines, 12 one-line open threads; latest 3 outcomes; precise cited/current sections for all open threads and canonical sources for new work. For an authorised budget change, update the local rule and helper constants together and verify startup.
Persistence: Git + Python 3.8+; python3 tools/kb.py check at resume/post-save; named staging, full staged diff/stat, python3 tools/kb.py check --staged, one coherent commit
Privacy: <actual user-approved storage, versioning, backup, remote and search-index policy>
Reflection: .agents/skills/reflect/SKILL.md; <verified discovery or explicit local read>
Writers: one designated writer; <if overlap is enabled, local protocol and MEMORY.md Owners>
Environment: <useful local guidance, or none>
Adoption: <actual source URL/ref/commit/date; adaptations and reasons; any uncommitted-source/comparison limits>
```

These budgets are reference choices. A thread over 400 characters warns; change helper constants and local rules together when adapting limits. Current knowledge precedes newest-first history in its subject source. The index holds no expanding recent-decisions log.

For checkpoints, reread sources before editing; save knowledge/navigation/index and one outcome together. Inspect `git diff --cached` and `git diff --cached --stat`, and restage/reinspect/recheck after later edits. Correct only your own unfinished omission under its existing outcome; completed history stays additive. Leave unknown dirt untouched.

If independent writers may overlap, first install the shared-writer module, user-assigned Owners/scopes and verified protection. Bind acquisition/release to `python3 tools/kb.py lock <Seat>` / `python3 tools/kb.py unlock <issued-label>`. Acquire successfully before shared edits or staging, reread after acquisition, and release only after post-commit verification. Prefix shared-writer commits with the seat. Compare HEAD plus lock/unfinished-write signals around relevant reads; HEAD alone misses in-flight edits. Use a brief protected snapshot when uncertain, never hold a lock while waiting, and do not cross assigned areas without the required owner coordination or user reassignment.

The same commands may run through an existing tool rather than a shell. A failed acquisition or validator stops dependent operations. These commands are the Git reference, not requirements for every host.

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
- Before `check --staged` evaluates ignore rules, each repository `.gitignore` at the root or on the path to indexed managed Markdown must be an ordinary file matching its indexed version, allowing only CRLF/LF line-ending differences, or absent in both views. Other additions, removals or differences refuse validation before later Git inspection; reconcile the intended ignore policy rather than checking mixed states. Comparison uses raw bytes without running clean/smudge filters. Local/global Git exclusions still apply as local configuration, not committed policy.
- Both modes reject symlink/special-file Markdown and unsupported ignore-rule checks rather than silently passing. `check` also rejects symlinked managed directories; it does not follow them. Snapshot validation is cooperative, not an adversarial filesystem sandbox.
- Hidden skill paths such as `.agents/skills/reflect/SKILL.md` are outside the managed Markdown inventory and outcome gate. Verify separately that the bound procedure is persisted, not ignored and available after a fresh start; a green helper result does not check it.
- It does **not** prove space/topic status/history ordering, section-anchor or ordinary asset-link validity, attachment completeness/privacy, evidence truth, capture completeness, agent compliance or confidentiality. History links in CHANGELOG.md are intentionally not checked.
- **lock** atomically creates a persistent cooperative directory, refuses a nonempty index and issues a seat label with a 128-bit random acquisition component. It does not enforce all Git operations or verify that a caller is a live seat. Failed metadata creation or failed safe rollback is explicitly reported as a retained/incomplete lock, never success.
- **unlock** checks the exact label; **--force** is mechanical and requires the user's recovery decision. Unexpected lock contents are preserved even under force. A label is not a security credential; unrestricted writers could bypass this protocol.
- These original-derived checks now distinguish working state from the prospective commit, refuse unsupported roots/worktrees and unsafe file/lock shapes, preserve unexpected lock contents, and fail visibly if required inspection is unavailable. The staged changelog gate requires presence, not proof of a new/meaningful outcome. Topic status/history ordering and semantic completeness still require an agent's check.

Use [A1–A7](../../docs/acceptance.md) and the shared-writer checks on disposable data. Passing helper tests alone is not full installation acceptance.
