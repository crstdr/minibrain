# Git helper reference

Use [the starter](../starter/AGENTS.md) and [setup guide](setup.md). This is reference material, not installed instructions.

Requires available Git and Python 3.8 or later, in a normal dedicated Git working copy. It does not support a linked worktree (.git file), a bare repo, multiple clones or remote locking. The helper's root is the parent of its tools directory. Do not run it here as if this distribution were your personal brain.

## Layout and navigation

```text
AGENTS.md                 opening operating blocks, then local instructions
MEMORY.md                 bounded working index, not history
MAP.md                    top-level spaces and legacy subjects
CHANGELOG.md              one outcome per coherent checkpoint
spaces/Project.md         a small memory space; current knowledge and history
tools/minibrain.py                copy of the supplied helper
.agents/skills/reflect/SKILL.md      local procedure (or verified explicit-file equivalent)
.agents/skills/resume/SKILL.md       optional host pointer
.agents/skills/checkpoint/SKILL.md   optional host pointer
CLAUDE.md                 optional verified entrypoint; identical gate first
```

Existing `topics/` and root-level subjects stay supported; no migration is automatic. A new space can grow from `spaces/Project.md` to `spaces/Project/index.md`, with optional child spaces and `assets/` as described in [memory spaces](spaces.md). Do not create unused structure just to match the starter, copy root controls into spaces, or hide pending work in a child cockpit. Inventory legacy files such as MINIBRAIN.md rather than silently dropping their knowledge.

Managed Markdown is root *.md, topics/**/*.md and spaces/**/*.md; it must not be ignored. Root-relative qualified wikilinks accept sections/display text: `[[spaces/Project#Current status|Project]]`. A logical space path without `.md` resolves to its note or folder index; both existing is an error. A path ending in `.md` names that exact file. Bare names remain supported for unambiguous legacy non-space targets, not spaces (even when unique today). Spaces and their assets do not enter that legacy basename namespace. Bare reserved control names prefer the root file; use an exact path when a supporting copy is intended. Repeated names inside spaces are supported through their qualified paths. Legacy non-reserved basenames outside spaces retain the uniqueness guard. Links containing absolute paths, `.` or `..` segments are not accepted. The checker verifies Markdown targets, not section anchors or ordinary Markdown/asset links; verify those separately. General wikilink validation still scans fenced examples as in the legacy checker; fence exclusion applies to new space registrations, not every link.

Top-level spaces register once in root MAP.md. Every leading space-link bullet (`- [[spaces/...]]`) in root MAP.md is a registration, even under Related or with a section/display suffix; use ordinary Markdown links for non-owning root navigation and verify them separately. Children register once in their containing space's index under exact `## Spaces`, using leading `- [[path]]` entries. In a child index, Related links outside that section do not register ownership. Every non-asset Markdown file is a child space, placed directly in the folder or under an optional `spaces/` namespace. A folder containing canonical children needs its own index; a `spaces/` namespace must not have one. The space names `assets` and `spaces` are reserved case-insensitively; `index.md` is a folder-space entrypoint, not a namespace note. Registrations must be outside fenced examples; duplicate active `## Spaces` sections and entries that are not direct child spaces are refused. Legacy root/topics Markdown still registers in root MAP.md with its original leading `- [[basename]]` spelling; section/display links are not additional legacy registrations. Logical space links survive note-to-folder growth; exact-file links and other relocations still need updates.

Supporting material can use work/, sources/ or archive/ outside spaces, or a space's optional assets/ directory. Markdown outside root/topics/spaces must be tracked in Git before the working-tree checker can resolve it as a supporting target. Use the literal lowercase `spaces/` and `assets/` spellings for these reference bindings. Space assets are data, not canonical child spaces: Markdown assets are not registered and their contents are not checked for wikilinks. Markdown inside assets is still checked for regular UTF-8 file/ignore boundaries. Never place root control filenames (AGENTS.md, CLAUDE.md, MEMORY.md, MAP.md, CHANGELOG.md) inside spaces, including assets; the guard is case-insensitive and source copies need a non-entrypoint name such as AGENTS.md.example. Binary contents/privacy, ignored or missing non-Markdown assets and external availability are not validated. Record and manually verify required attachment retention/portability under the user's policy. Any staged change under spaces/, including binary assets, requires the root outcome changelog. Legacy topics/ retains its Markdown-only changelog gate; it has no new asset/folder-space semantics.

The new reference uses `MAP.md`. For an existing brain with `Map.md`, either retain its spelling and set `MAP_FILE` accordingly, or agree a migration of the file and all links together. On case-insensitive filesystems use an intermediate filename for a case-only rename. Never silently reset a local helper configuration.

This reference requires ordinary UTF-8 Markdown files contained in the repository, not symlinks, special files or symlinked managed directories. A deliberately external store needs an explicit alternative binding; it must not masquerade as knowledge contained in this Git history.

## Install and verify the helper

Keep [tools/minibrain.py](../starter/tools/minibrain.py) at the selected brain's tools/minibrain.py, not a nested tools directory whose parent is the wrong root. The helper uses only the standard library and never installs packages.

Existing brains may retain `kb.py`; rename only during an authorised upgrade and update command references together. The lock path stays `.git/kb-writer.lock`, preserving coordination with older helpers.

Before `git init`, inspect `git rev-parse --show-toplevel` from the target and distinguish “not a repository” from another Git failure. Refuse accidental nesting; resolve intended integration with the user. Keep other sessions read-only during setup.

Stage the new files by name, inspect the full staged diff and run `python3 tools/minibrain.py check --staged`. Before the very first commit, `no commits yet` is the one expected PROBLEM; initial dirty/staged warnings are also expected. Fix every other problem. Commit the installation once and run `python3 tools/minibrain.py check` again. Initial installation is sole-writer; do not overlap during this bootstrap exception.

For later checkpoints no PROBLEM is expected. Dirty/staged warnings for your own in-flight update and your own held lock are expected; known assigned foreign work remains untouched. Warnings do not change the exit code: the agent must interpret them. Unexpected dirt blocks dependent writes under the contract.

## Exactly what the tool does

- **check** is a read-only working-tree diagnostic for resume and post-save checks. Checks normal root, required controls, ordinary file boundaries, memory-size advisory and thread cap, heading uniqueness/order, canonical Markdown link targets, unambiguous names, parent-space/legacy-map registrations, ignored managed Markdown, Git state and the staged-changelog requirement.
- At ≥150 `MEMORY.md` lines (`MEMORY_REVIEW_LINES`), both modes warn without failing: consider `reflect` at the next useful boundary. Review relevance, navigation and startup cost; no forced trimming or repeated review of unchanged content. The 12-thread cap still fails; >400 characters per thread still warns.
- **check --staged** validates Markdown content and modes from the Git index—the prospective commit. It cannot resolve links through untracked topics or use unstaged repairs to hide a broken commit. Use this before every commit, not `check` alone. Both modes report working-tree dirt without changing it; intentionally uncommitted foreign work remains outside the proposed commit. Neither mode decides whether omissions are semantically important, so inspect the full scoped diff and verify that all your intended changes were saved.
- Before `check --staged` evaluates ignore rules, each repository `.gitignore` at the root or on the path to indexed managed Markdown must be an ordinary file matching its indexed version, allowing only CRLF/LF line-ending differences, or absent in both views. Other additions, removals or differences refuse validation before later Git inspection; reconcile the intended ignore policy rather than checking mixed states. Comparison uses raw bytes without running clean/smudge filters. Local/global Git exclusions still apply as local configuration, not committed policy.
- Both modes reject symlink/special-file Markdown and unsupported ignore-rule checks rather than silently passing. `check` also rejects symlinked managed directories; it does not follow them. Snapshot validation is cooperative, not an adversarial filesystem sandbox.
- Hidden skill paths such as `.agents/skills/reflect/SKILL.md` are outside the managed Markdown inventory and outcome gate. Verify separately that the bound procedure is persisted, not ignored and available after a fresh start; a green helper result does not check it.
- It does **not** prove space/topic status/history ordering, section-anchor or ordinary asset-link validity, attachment completeness/privacy, evidence truth, capture completeness, agent compliance or confidentiality. History links in CHANGELOG.md are intentionally not checked.
- **lock** atomically creates a persistent cooperative directory, refuses a nonempty index and issues a seat label with a 128-bit random acquisition component. It does not enforce all Git operations or verify that a caller is a live seat. Failed metadata creation or failed safe rollback is explicitly reported as a retained/incomplete lock, never success.
- **unlock** checks the exact label; **--force** is mechanical and requires the user's recovery decision. Unexpected lock contents are preserved even under force. A label is not a security credential; unrestricted writers could bypass this protocol.
- These original-derived checks now distinguish working state from the prospective commit, refuse unsupported roots/worktrees and unsafe file/lock shapes, preserve unexpected lock contents, and fail visibly if required inspection is unavailable. The staged changelog gate requires presence, not proof of a new/meaningful outcome. Topic status/history ordering and semantic completeness still require an agent's check.

Use [A1–A7](acceptance.md) and the [shared-writer checks](acceptance.md#shared-writers) on disposable data. Passing helper tests alone is not full installation acceptance.
