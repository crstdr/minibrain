# Changes

Upgrading: [procedure](SETUP.md#upgrading). Each row lists changed `starter/` files relative to its linked predecessor; unlisted files are unchanged for that comparison. For upgrades across releases, compare the adopted ref directly with the target.

| Release | Changed in `starter/` |
|---|---|
| [Unreleased](https://github.com/crstdr/minibrain/compare/v0.6.1...records) | `AGENTS.md`: Checkpoint steps 3–5. `tools/minibrain.py`: staged checks, gated commit, collection integration and shared writer guard. New `tools/collection.py`: query, graph, edit and collection checks. Take the contract and core together; the collection extension needs the matching core changes and local `CORE_HELPER` filename. `.agents/skills/reflect/SKILL.md`: Destinations |
| [0.6.1](https://github.com/crstdr/minibrain/compare/v0.6.0...v0.6.1) | nothing |
| [0.6.0](https://github.com/crstdr/minibrain/compare/v0.5.2...v0.6.0) | `AGENTS.md`: Checkpoint, Memory rules, Resume, `<rpce_tooling_guidance>`. `.agents/skills/reflect/SKILL.md`: Destinations |
| [0.5.2](https://github.com/crstdr/minibrain/compare/v0.5.1...v0.5.2) | `AGENTS.md`: Authority and privacy, `<rpce_tooling_guidance>` |
| [0.5.1](https://github.com/crstdr/minibrain/compare/v0.5.0...v0.5.1) | `AGENTS.md`: `<rpce_tooling_guidance>` |
| [0.5.0](https://github.com/crstdr/minibrain/compare/v0.4.2...v0.5.0) | `AGENTS.md`: Memory rules, Resume, `<communication_hygiene>` |
| [0.4.2](https://github.com/crstdr/minibrain/compare/v0.3.1...v0.4.2) | nothing |
| [0.3.1](https://github.com/crstdr/minibrain/compare/v0.3.0...v0.3.1) | `AGENTS.md`: Checkpoint |
| [0.3.0](https://github.com/crstdr/minibrain/compare/v0.2.0...v0.3.0) | new structure (contract, skills, helper, starter files): adapt per [SETUP.md](SETUP.md) |

## Unreleased

- Optional `tools/collection.py` supplies `query`, `graph` and one-operation `edit` for Markdown records. Read-only SQL uses an in-memory snapshot with configured numeric fields and prerequisite states, dependency relations and assessment-section presence. Query and graph emit LF-ended, headered TSV with CSV quoting for embedded CR, LF, tabs and quotes. Integral REAL results omit `.0`.
- Collection checks preserve canonical decision History even after governance retirement, report malformed governed entries, reject committed-record deletion and check outgoing wikilinks without Map registration or routine collection-only changelog entries. Section edits preserve peer sections across indented Setext continuations and HTML comments. All section edits refuse records with an unclosed code fence or HTML comment; close it or edit manually. Section replacements also refuse removal of raw heading-like lines, including examples inside code; manual editing remains available. Field edits are unchanged. Added-edge checks report cycles even when unrelated cycles already exist. Private SQL indexes no longer collide with collection names. CTE counts work without opening schema reads or writes.
- Core checks run the optional extension, report unexpected extension exits as PROBLEMs and keep record ids out of the bare-name link namespace. Staged checks execute indexed extension bytes, allowing only CRLF/LF and executable-bit differences from the regular working file. They reject stale staged paths, including working rename sources and recreated deletions, and collection-root symlinks or gitlinks before commit.
- `minibrain.py commit [--label <label>] -m <message>... [--amend]` gates the index through `check --staged`, commits without `-a`, compares the saved tree with the validated tree, then runs `check`. If a hook changes the committed tree or tree verification fails, the helper reports that a commit already happened and grants no success or amend receipt. Hooks remain enabled. Amend requires this acquisition's recorded commit at HEAD. Checkpoint retains legacy pre/post checks and additive correction when amend is unavailable. Take the contract and core changes together. Core commits and collection edits share the writer-label guard.
- Collection help shows usable ranking operands and a local candidate-state filter, section editing through stdin, bracketed hyphenated identifiers, explicit assessment dates, exact state matching and promotion routes. Numeric fields retain the leading-number rule: all suffix text is commentary, with no unit conversion. `SETUP.md` covers approved manual governance conversion, optional adoption and matching core/extension configuration and repository-local commit identity. Reflect points to upstream setup rather than an installed setup file. README describes optional collections and keeps installation guidance in SETUP.
- Reflect's Destinations question 2 keeps subject preferences out of `<principles>`; its collection cue requires approval before installation or migration.

## 0.6.1

- SETUP.md#Upgrading is now a five-step procedure: inspect the delta between the adopted ref and the target, apply it without losing local adaptations, verify them, and record the adopted ref, local adaptations and any unapplied upstream changes.
- This changelog has an upgrade table listing the `starter/` files and sections each release changed, with compare links.
- A test requires the current version to appear in the changelog and the upgrade table.
- No starter, helper or installed-brain changes.

## 0.6.0

- `reflect` Destinations is now an ordered question flow for categorising and storing information: authority, standing rules, procedures, lessons and subject knowledge, then working-index follow-ups.
- Checkpoint step 2 reads `reflect`'s Principles and Destinations before changing principles, constraints or operating instructions.
- Resume step 2 retrieves only enough canonical context for the task, after orienting from `MEMORY.md`.
- Evidence tells agents to keep status short and move embedded history to a separate section or linked source when updating it.
- Canonical says to record or link a set's members, not just counts or classes, when membership matters.
- Checkpoint step 3 tells agents to add notable new outcomes to Awaiting acknowledgment.
- RepoPrompt lanes keep a name given by the user or their creating overseer instead of retitling themselves after the task.
- No helper changes or automatic updates to existing installations.

## 0.5.2

- Encourage available, authorised delegation, including subagents, to protect working context for reasoning, coordination and memory upkeep while following the harness's own mechanisms.
- Refresh the README opening to explain self-organising working memory and continuity of purpose and responsibility; retain the installation, feature and agent guidance.
- Honour agreed user preferences and delegation for RPCE workflows and compaction, matching Oracle guidance; otherwise ask first.
- Isolate disposable Git test fixtures from inherited `GIT_*` settings; regressions cover external index and repository redirection without changing the shipped helper.

## 0.5.1

- Expand optional RPCE guidance with task-based workflow selection and standalone Context Builder use; consult the user before the named workflows and preserve delegated decision boundaries.
- Guide Oracle use toward carefully prepared, proportionate, normally one-shot advice, reviews and second opinions; follow agreed preferences and delegation or ask first. Update the consent-policy test without freezing the surrounding advice.
- No helper changes or automatic updates to existing installations.

## 0.5.0

- Gather onboarding context progressively, asking consequential questions when their answers affect the next action rather than requiring an upfront questionnaire.
- Replace mandatory evidence-label syntax with natural attribution; keep inference, uncertainty and second-hand reports explicit.
- Let Resume retrieve context according to the task and reuse reliable context; remove the prescribed readback while retaining Reporting, unfinished-work reporting and read-consistency safeguards.
- Recognise acknowledgment through words or actions that unambiguously show awareness; consolidate superseded outcomes while preserving history and the distinction from approval.
- Tests: drop assertions on removed wording; assert synthetic adoption leaves the operating instructions unchanged.
- No helper changes or automatic updates to existing installations.

## 0.4.2

- Clarify the README introduction, installation prompt and features, including optional RepoPrompt CE overseer guidance; retain the concise agent setup and upgrade routes.
- Remove incidental copy checks and frozen prose snapshots from tests; retain preservation, authority, loading, packaging and helper checks.
- No changes to the starter, helper or installed brains.

## 0.3.1

- Clarify that user-stated decisions, deferrals, permission conditions and procedures are durable state even when no action is due.
- Require standalone lock acquisition without pipelines and verified success before shared edits or staging.

## 0.3.0

- Clarify continuing agent names and scopes, canonical Owners and RPCE lane titles; retain one active writer session per name.
- Add compact, conditional RPCE overseer guidance and explicit Oracle/compaction approval cues; move generic delegation briefing into the common contract.
- Distinguish user-blocked work from notable outcomes awaiting acknowledgment; retain both through ordinary memory and report them without per-turn repetition.
- Reduce CONTRIBUTING to a short human-and-agent policy. Extend copied-starter and helper tests for the updated naming and acknowledgment section.

- Move setup to root `SETUP.md`, shorten the README agent route and remove its experimental footer. License the distribution under MIT; include the notice in the copied starter.

- Fix prospective-commit checks for intent-to-add placeholders and hidden-change Git flags; count all Markdown thread markers and exclude fenced examples from structural counts. Add focused helper regressions.
- Reduce `docs/` to setup: move installation checks there and helper conventions into the script; remove duplicate growth/space guidance and historical test-run prose. Keep runtime safeguards and update links together.

- Consolidate copyable files into `starter/` with installed filenames, adoption fields, local skills and `tools/minibrain.py`; add the approved terse operating blocks and writer bindings, make ≥150 memory lines a reflection advisory, and simplify onboarding by removing duplicate documentation. Existing installations remain unchanged.

- Clarify onboarding with separate human/agent README routes, ordered setup reading and an explicit adaptation-preserving upgrade path; keep installation guidance separate from the concise local operating contract.
- Add maintained user principles and the locally bound `reflect` procedure; preserve existing user knowledge, permissions and shared-writer safeguards.
- Keep reference bindings and documentation aligned, verify copied-template adoption, and guard staged ignore-policy checks against mixed states, unsafe files and line-ending differences without invoking content filters.

- Reduce adoption to one short source-link request; retain setup/privacy/migration safeguards in the repository rather than requiring a long pasted prompt.
- Add the approved optional RPCE environment binding and make durable source/adaptation records and adaptation-preserving upgrades explicit.
- Define memory spaces: notes can grow into indexed folders with child spaces and supporting assets. Default new file-based installs to spaces/ without migrating existing topics/ brains or cloning root authority/coordination.
- Extend the reference checker with qualified space links, note/folder resolution, direct-parent registration and root-only control boundaries; retain legacy topics and prospective-index checks.
- Add synthetic/static checks and separate mechanical verification from untested agent adoption, growth and upgrade behaviour.

- Put the PURPOSE / GROUND / IMPROVE / CAPACITY / CEREMONY operating gate first in the core starter and recommend the same placement in applicable AGENTS.md and CLAUDE.md entrypoints.
- Preserve one authoritative full contract, identical small gate mirrors, existing rules and approval for shared-file changes; verify loading before adding host imports.
- Add a worked CLAUDE entrypoint, static wording/placement checks and explicit host/behavioural verification limits. Preserve the original operating detail and leave existing installations, helper acceptance and the v0.2.0 release unchanged.

## 0.2.0

- Restore the original operating contract; remove mandatory two-file installation.
- Separate required properties, conditional writer safeguards and adaptable implementation choices.
- Supply the Git/Markdown reference, structural validator/cooperative lock and product tests.
- Validate prospective commits separately from working files; reject unsafe file boundaries, strengthen acquisition receipts and expose inspection/lock failures without automated recovery.
- Preserve A1–A7 acceptance and verification limits; strengthen actionable decisions, portable know-how and current scoped instructions.
- Preserve existing installations unless their user approves integration/migration. No evaluation campaign or universal behavioural validation is implied.

## 0.1.0

- Initial simplified starter. Its fixed two-file approach is superseded by 0.2.0; historical tags remain unchanged.
