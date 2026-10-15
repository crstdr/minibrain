# Install or adapt minibrain

Read this guide; adapt the contents of [starter/](../starter/AGENTS.md) into the destination root—not a nested `starter/` folder. Its files use their installed names; this guide and the rest of the distribution stay outside the brain.

## Reading order

1. [AGENTS.md](../starter/AGENTS.md) — operating blocks, local rules and procedures.
2. [Reflect](../starter/.agents/skills/reflect/SKILL.md) — locally retained maintenance procedure.
3. Applicable references: [Git helper](git-reference.md), [memory spaces](spaces.md). Read these when choosing or changing those mechanisms, not at every startup.
4. [Acceptance checks](acceptance.md) — plan and verify the final adapted installation.

Existing minibrain? Start with [Upgrading](#upgrading).

## 1. Inspect

- Read the source online or in a temporary checkout outside the destination; never clone this public distribution into private memory.
- Establish the user's purpose, delegation, approval boundaries, privacy/storage policy and active writers. Ask for consequential missing choices; do not repeat questions already answered.
- Inspect existing notes, instructions, host entrypoints, Git/backup state and available tools. Preserve compatible arrangements; propose consequential restructuring and a backup before migration. Account for legacy files such as `MINIBRAIN.md`.
- Keep one writer during setup; read-only helpers may assist when authorised. No installation into shared or global instructions without the relevant user's approval.

## 2. Adapt the starter

| Starter file | Installed role |
|---|---|
| `AGENTS.md` | One authoritative local operating contract; preserve unrelated existing rules. |
| `MEMORY.md`, `MAP.md`, `CHANGELOG.md`, `spaces/Project.md` | Working index, discovery, outcomes and canonical knowledge; adapt paths/content to existing memory. |
| `tools/minibrain.py` | Ready-made Git/Python helper; preserve its safeguards and reconcile existing local configuration. |
| `.agents/skills/` | Local `reflect`, plus thin `resume`/`checkpoint` pointers; verify discovery or use explicit reads. |
| `CLAUDE.md` | Optional identical gate plus `@AGENTS.md`; only for a host that needs and supports that import. |
| `.gitignore` | Default local exclusions; review them and preserve existing policy. |

Fill `[square-bracket placeholders]` below the XML blocks and in memory files from established facts; record honest unknowns and remove unused rows/entries. Clarify missing delegation before acting; placeholders grant no authority. Keep usable path defaults or preserve compatible existing paths, updating references together. Seed only explicit user principles or confirmed generalisations; an empty block does not revoke existing rules. Preserve their scope and record where any unmigrated rules remain. Record the source URL, inspected ref/commit/date and local adaptations in the existing canonical record; unknown provenance stays unknown.

Keep XML blocks together at the start of the instruction file, `<orient>` first where the host permits. Keep full instructions canonical; mirror only the gate into needed entrypoints. Verify the actual loading path before adding imports—do not load the full contract twice. A host requiring leading metadata or different entrypoints needs a recorded adaptation, not blind copying.

Omit the RPCE block if unavailable or redundant. When independent writers may overlap, bind `<shared_writers>` to user-assigned Owners and verified coordination for the actual shared store. A local Git lock does not cover separate clones or remote sync; keep one writer if coordination is unverified. Neither a source link nor a peer message grants authority.

The starter uses Git and Markdown, not a mandatory storage scheme. Other mechanisms must preserve coherent saves, bounded startup, canonical knowledge, evidence, privacy and unfinished work. Declare unavailable capabilities and verify substitutes. Keep required instructions, maintenance and skills local; operation must not depend on setup chat or this checkout.

## 3. Save and verify

Before `git init`, check for an enclosing repository; resolve integration rather than nesting accidentally. The helper supports a normal dedicated Git working copy, not linked worktrees or distributed sync. Never adopt a public code remote for private memory.

For a new Git brain, copy only chosen files (including hidden skills), adapt them, stage by name, inspect the complete staged diff/stat and run `python3 tools/minibrain.py check --staged`. Before the first commit only, `no commits yet` is expected; fix other problems, commit once and run `check` again. See [helper checks and limits](git-reference.md#exactly-what-the-tool-does).

For existing brains, preserve knowledge and local adaptations. `MAP.md` is the starter spelling; retain legacy `Map.md` with a matching `MAP_FILE` setting, or agree a file/link migration. Case-only Git renames may need an intermediate name. Inspect newly managed paths before replacing an existing helper.

Run applicable [acceptance checks](acceptance.md). Verify local links, hidden skill persistence, host loading, gate mirrors and actual read paths—not just file presence. Check that no unresolved adoption placeholders remain; `minibrain.py` does not check them. Report pass/fail/not-run, changed/preserved material, the local entrypoint and remaining decisions. Unfinished checks mean prepared, not fully accepted. No implicit push or new tool/service/data-access permission.

## Upgrading

1. Read the destination's instructions and adoption record. Obtain upgrade authority; preserve unfinished work and keep other writers read-only during protocol changes.
2. Compare the adopted source, proposed revision and current local rules, skills and helper configuration. Read this guide and the changed source files. If the old source or uncommitted base is unavailable, disclose that limit.
3. Preserve user knowledge, principles and adaptations; resolve consequential conflicts with the user. A new upstream version grants no authority to migrate, install or publish.
4. Verify the final local result and loading paths, then record the new adopted source and changes. All writers reload before overlap resumes.

## Implementation limits

Instructions and structural tests do not prove agent compliance, semantic completeness, confidentiality or cross-host compatibility. No scheduler, autonomous runtime, encryption or distributed lock is supplied. Use the [verification record](acceptance.md) for observed results.
