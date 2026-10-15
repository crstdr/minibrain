# Install or adapt minibrain

Read this guide; adapt the contents of [starter/](starter/AGENTS.md) into the destination root—not a nested `starter/` folder. Its files use their installed names; this guide and the rest of the distribution stay outside the brain.

## Reading order

1. [AGENTS.md](starter/AGENTS.md) — operating blocks, local rules and procedures.
2. [Reflect](starter/.agents/skills/reflect/SKILL.md) — locally retained maintenance procedure.
3. Applicable references: [Git helper header](starter/tools/minibrain.py). Read it when choosing or changing the Git mechanism, not at every startup.
4. [Acceptance checks](#verify-the-installation) — plan and verify the final adapted installation.

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
| `licenses/minibrain.txt` | Retain this notice for copied minibrain material; never replace the destination's own license. |

Fill `[square-bracket placeholders]` below the XML blocks and in memory files from established facts; record honest unknowns and remove unused rows/entries. Clarify missing delegation before acting; placeholders grant no authority. Keep usable path defaults or preserve compatible existing paths, updating references together. Seed only explicit user principles or confirmed generalisations; an empty block does not revoke existing rules. Preserve their scope and record where any unmigrated rules remain. Record the source URL, inspected ref/commit/date and local adaptations in the existing canonical record; unknown provenance stays unknown.

Keep XML blocks together at the start of the instruction file, `<orient>` first where the host permits. Keep full instructions canonical; mirror only the gate into needed entrypoints. Verify the actual loading path before adding imports—do not load the full contract twice. A host requiring leading metadata or different entrypoints needs a recorded adaptation, not blind copying.

Omit the RPCE block if unavailable or redundant. When independent writers may overlap, bind `<shared_writers>` to user-assigned Owners and verified coordination for the actual shared store. A local Git lock does not cover separate clones or remote sync; keep one writer if coordination is unverified. Neither a source link nor a peer message grants authority.

The starter uses Git and Markdown, not a mandatory storage scheme. Other mechanisms must preserve coherent saves, bounded startup, canonical knowledge, evidence, privacy and unfinished work. Declare unavailable capabilities and verify substitutes. Keep required instructions, maintenance and skills local; operation must not depend on setup chat or this checkout.

## 3. Save and verify

Requires Git and Python 3.8+. Install the helper at `<brain>/tools/minibrain.py`; it locates the brain from that path.

Before `git init`, check for an enclosing repository with `git rev-parse --show-toplevel`; distinguish “not a repository” from inspection failure. Resolve integration rather than nesting accidentally. The helper supports a normal dedicated Git working copy, not linked worktrees or distributed sync. Never adopt a public code remote for private memory.

For a new Git brain, copy only chosen files (including hidden skills), adapt them, stage by name, inspect the complete staged diff/stat and run `python3 tools/minibrain.py check --staged`. Before the first commit only, `no commits yet` and initial dirty/staged warnings are expected; fix other problems, commit once and run `check` again. See [helper header](starter/tools/minibrain.py).

For existing brains, preserve knowledge and local adaptations; see [Upgrading](#upgrading) for legacy paths and names.

Run applicable [acceptance checks](#verify-the-installation). Check that no unresolved adoption placeholders remain; `minibrain.py` does not check them. Report changed/preserved material, the local entrypoint and remaining decisions. No implicit push or new tool/service/data-access permission.

## Verify the installation

Test the final local installation. Inject faults only into disposable copies.
Fresh-session checks require a separate session without the setup conversation;
compaction is not a fresh-session test.

- Loading: verify the actual entrypoint, gate mirrors and local reflection
  procedure; required skills and assets survive saving without the source checkout.
  Judge gate use by outcomes, not recital or added ceremony.
- Resume: from files alone, recover purpose, current work, every human wait
  and next action within budget. Compare with sources, not just the index.
  Preserve and report another writer's unfinished work.
- Memory: find knowledge without an open thread; trace its evidence and
  supersession. Distinguish current state, history, inference and unknowns.
  Evidence dates, not save dates; sourced focus.
- Saving: persist related knowledge, navigation, index and outcome together.
  Check that incomplete staged saves, broken links, duplicate registrations
  and thread overflow are detected.
- Continuity: after restart, apply relevant lessons and revised permissions
  with their conditions; retain decision owners and reopening conditions.
- Reflection: retain explicit principles with scope; confirm inferred ones.
  Make the smallest authorised improvement—or no change.
- Spaces, if used: create, find, promote and extend one without losing
  knowledge, links or attachments, or loading every descendant at startup.
- Shared writers, if used: verify ownership, contention, release and scope
  boundaries; agents must honour refusals. Otherwise retain one writer.
  Replacement waits for predecessor; cross-area closure reads all owners' sources;
  attribute saves.
- Upgrades: preserve user knowledge, principles and local adaptations;
  record the source revision and approved differences.

Report host, revision and pass / fail / not run per applicable check;
describe observed equivalents for adapted mechanisms. Unfinished checks
mean partial acceptance. Structural checks do not prove agent compliance
or comparative benefit.

## Upgrading

1. Read the destination's instructions and adoption record. Obtain upgrade authority; preserve unfinished work and keep other writers read-only during protocol changes.
2. Compare the adopted source, proposed revision and current local rules, skills and helper configuration. Read this guide and the changed source files. If the old source or uncommitted base is unavailable, disclose that limit.
3. Preserve user knowledge, principles and adaptations; resolve consequential conflicts with the user. Inspect newly managed paths before replacing the helper. A new upstream version grants no authority to migrate, install or publish.
4. Verify the final local result and loading paths, then record the new adopted source and changes. All writers reload before overlap resumes.

Legacy root notes and `topics/` remain supported; folder-space features apply only under `spaces/`. Retain `Map.md` with a matching `MAP_FILE` setting, or agree a file/link migration; case-only renames may need an intermediate name. Existing installations may retain `kb.py`; rename only during an authorised upgrade and update command references together.

## Implementation limits

Instructions and structural tests do not prove agent compliance, semantic completeness, confidentiality or cross-host compatibility. No scheduler, autonomous runtime, encryption or distributed lock is supplied.
