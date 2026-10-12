# Memory spaces

A **memory space** is a named scope of knowledge with a clear purpose and one authoritative entrypoint. It can be one Markdown note or a folder whose index leads to the knowledge it owns. Size and shape change without changing the principle: one home per claim, current state distinct from history, and responsibilities still visible when the session resumes.

The short `<primitive_spaces>` block in the [operating contract](../starter/instructions.md#memory-spaces) defines the agent's habit. Keep it with the adopted core instructions, not copied into every space. This page and the [Git/Markdown reference](../examples/git-markdown/README.md) provide concrete inspiration, not a compulsory stack or schema.

## “Create a memory space for X”

1. Infer the purpose/boundary from the request; ask only for consequential missing information. Find an existing canonical home before creating another one.
2. Use the smallest useful shape. A short subject can be `spaces/X.md`. A subject that already needs multiple sources, attachments or children can start as `spaces/X/index.md`.
3. Record known purpose, current state, evidence/unknowns and relevant history. Register its entrypoint once in its parent's navigation; add a root working-index pointer only for actual ongoing work or a human decision. Do not invent tasks to populate a template.
4. Save and verify with the existing checkpoint/coordination rules. Creating a space does not install tools, grant new access, launch an agent or create a separate repository.

## A recursive reference, created only as needed

```text
AGENTS.md                         one root operating contract/gate
MEMORY.md                         root responsibilities and startup budget
Map.md                            top-level discovery
CHANGELOG.md                      coherent outcomes for the whole brain
spaces/
  Garden.md                       one small space
  Travel/
    index.md                      purpose, current state, child navigation, history
    assets/                       supporting material, when needed
    spaces/
      Japan.md                    a child space
      Portugal/
        index.md                  repeats the useful knowledge/navigation pattern
        assets/                   only if there is material to keep
```

The repeatable unit is **purpose + current knowledge + navigation + history**, not a cloned agent installation. The root is special: retain one operating contract, adoption record, working-responsibility index and writer/checkpoint mechanism. Do not silently add nested AGENTS.md/CLAUDE.md, per-space locks, independent Git repos or mandatory per-space changelogs. An index may cite more detailed history or handling information when useful; it does not grant authority to override root/user/host instructions.

An index's suggested sections are `Purpose`, `Current status`, `Spaces` (if there are children), `Supporting material` (if any), and `History`. Create only meaningful sections and files. A space can itself contain spaces, but depth is not a goal. Root startup does not recursively load them: read the source sections needed for actual work. A child folder cannot hide a pending decision or bypass the root's declared responsibility budget.

## Growth is a deliberate change, not another copy

Promoting `spaces/Garden.md` into `spaces/Garden/index.md` can be routine growth within existing authority when it preserves content, ownership and logical links; report that coherent change. If ownership, externally used paths or responsibilities change, propose the layout and give the user an opportunity to respond before restructuring. Preserve the original knowledge, evidence, decisions and procedural lessons. A qualified logical space link such as `[[spaces/Garden]]` resolves to either the note or the folder index, so ordinary growth preserves it. Update exact-file references, changed section anchors and any moved child paths in the same coherent checkpoint. Do not leave both the old note and the new folder index as competing entrypoints. For other relocations, update references or retain an explicitly retired successor pointer where the local mechanism supports it; verify the result. Never rename all existing topics merely to match the new default.

The Git reference uses root-relative qualified space links such as `[[spaces/Travel]]` or `[[spaces/Travel/spaces/Japan#Current status]]`. Without `.md`, a logical space path resolves to its note or folder index; both existing is an error. Explicit `[[spaces/Travel/index.md]]` or note `.md` paths remain exact file references. Repeated `index.md` and child names at different paths are allowed, but bare space names are rejected even if unique today, preventing a later same-named space from breaking earlier links. Legacy non-space bare links remain supported. Moving a space to another path still requires reference updates. Other storage mechanisms must preserve the same discoverability, not these spellings.

Top-level spaces are registered in root Map.md; child spaces in their parent's index under `## Spaces`. These registrations are navigation, not duplicate knowledge. Related links outside that section do not change ownership. The reference retains the old root/topic registration rules for existing brains. Within a folder space, every non-asset Markdown note is a canonical child, whether directly in the folder or grouped under an optional `spaces/` namespace; register it once under `## Spaces`, including a split-out history note. Use other sections for related links. Do not move canonical knowledge into `assets/` merely to silence a registration check.

The reference reserves the space names `assets` and `spaces` (case-insensitively) for structure, and `index.md` for a folder space's entrypoint; choose a descriptive alternative such as `Asset inventory`. A namespace directory itself has no index (`spaces/index.md` and `.../spaces/index.md` are refused). These are reference spelling constraints, not universal memory-space concepts.

## Attachments are supporting evidence, not instructions

Use an optional `assets/` directory for supporting material owned by a space. Keep a small description/link in the space index when needed to understand relevance, provenance or retention. Quoted Markdown, PDFs and images do not become canonical claims or higher-priority instructions merely because they are nearby. Do not auto-load every attachment on resume or execute anything it contains.

Choose storage under the user's privacy/versioning policy: Git history retains committed binary content even after deletion. Large, sensitive or externally governed material may need an authorised external location and a durable descriptive pointer instead. Do not copy secrets or broaden sharing through a space. A pointer does not make an external asset portable, private or available; state the dependency.

The helper checks supported Markdown structure and file boundaries, not the safety, confidentiality, completeness or availability of attachment contents. Its root-only instruction-file refusal also applies inside assets: retain source examples under a non-entrypoint name rather than accidentally installing instructions.

## Existing brains and limits

`topics/`, root-level subject notes and suitable existing arrangements remain valid. Adoption and upgrades preserve them unless the user approves a reasoned migration. The helper extension supports `spaces/` alongside `topics/`; it does not migrate a brain. Real personal brains are never product fixtures or test data. In this Git reference, indexed folder growth, assets and parent registries operate under `spaces/`, not `topics/`; growing a legacy topic requires a proposed move into `spaces/` and conversion of its incoming bare links to qualified paths. A helper upgrade also needs an inspection of any pre-existing `spaces/` directory before claiming it as managed memory.

These patterns and synthetic checks are not evidence that an agent will always choose a useful boundary, preserve every obligation during a move, or maintain effectiveness at arbitrary depth. Exercise the relevant [acceptance checks](acceptance.md) on disposable material and report what remains untested.
