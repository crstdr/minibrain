# What this inherits and changes

Minibrain builds on the **Lean memory system setup guide (2026-09-26)** and **Concurrent writers setup guide (2026-09-26)** used as the basis of existing folder memories. This is a generalised implementation, not publication of personal memories or deployment records.

The original already preserves properties rather than filenames. v0.1 wrongly mandated a two-file starting layout and deferred concrete safeguards. v0.2 retains the operating contract, supplies its implementation and adapts means to the environment.

| Original asset | Product home | Adaptation |
|---|---|---|
| Canonical knowledge, evidence, current state and supersession | Contract: working rules | Locations can differ; obligations remain |
| Bounded cockpit, Focus, full thread readback | Contract: rules/resume | Explicit local budget; reference retains 150 lines / 12 threads |
| Resume and coherent checkpoint | Contract with local bindings | Git commands are a reference; alternatives explain protection/limits |
| Topics, Map, changelog, host pointers | Git/Markdown example and setup | Full example, not forced migration target |
| Validator and persistent cooperative lock | examples/git-markdown/tools/kb.py | Original-derived code with prospective-commit validation, ordinary-file/root guards, stronger acquisition labels and regression tests; shape is not meaning |
| Seats, scoped ownership, attribution, fresh reads, shared-index protection, human recovery decisions | Conditional shared-writer contract module | Install before overlap; do not burden single-writer startup or build orchestration/distributed sync |
| A1–A7 | docs/acceptance.md | Explicit not-run/adapted results, not automatic passes |

Additional guidance addresses decisions left only in narrative, know-how stranded in continuation notes, lessons retrieved after rather than before mistakes, and obsolete rules used despite newer scoped instructions. These are design responses to experience, not proof that the new text eliminates those failures.

The unreleased `<before_you_act>` addition makes PURPOSE, GROUND, IMPROVE and CAPACITY a prominent operating check before substantive responses or consequential actions. It leaves the original working rules and detailed resume/checkpoint procedures intact. Small identical entrypoint mirrors serve visibility; they do not create competing full contracts, new authority or evidence of behavioural effectiveness.

The further unreleased revision names the existing subject-home concept **memory spaces**, adding a recursive indexed-folder reference and qualified links without migrating older topics. It also supplies an optional RPCE binding and a clearer adoption/upgrade record. These extend navigation and provenance; they do not replace the original operating procedures or copy root authority into children.

Review-driven helper changes prevent concrete failures: validating unstaged/untracked content that will not be committed; treating external symlink targets as portable memory; repeating short acquisition receipts; and silently passing failed inspection or obscuring an incomplete lock. They add no automated recovery, retry loop or enforcement claim. The core retains the original resume/checkpoint triggers and evidence-led anti-bottleneck rule; transient writer contention is not itself a reason to interrupt the user.

Bounded startup must not become endless history; archival upkeep should earn its cost. Privacy and permission remain explicit even when existing tools are powerful.

Documents/helper tests establish neither comparative benefit nor universal compatibility, model compliance or reduced human effort.
