# Changes

Upgrading: [procedure](SETUP.md#upgrading). Each row lists changed `starter/` files relative to its linked predecessor; unlisted files are unchanged for that comparison. For upgrades across releases, compare the adopted ref directly with the target.

| Release | Changed in `starter/` |
|---|---|
| [0.10-alpha.1](https://github.com/crstdr/minibrain/compare/v0.9.1...v0.10-alpha.1) | nothing. RepoPrompt CE block (`hosts/repoprompt.md`): new MAP line. |
| [0.9.1](https://github.com/crstdr/minibrain/compare/v0.9...v0.9.1) | nothing. The Agents Map demo and its fixes are outside `starter/`. |
| [0.9.1-alpha.1](https://github.com/crstdr/minibrain/compare/v0.9...v0.9.1-alpha.1) | nothing. The Agents Map demo is outside `starter/`. |
| [0.9](https://github.com/crstdr/minibrain/compare/v0.8...v0.9) | Since 0.8: the 0.9-alpha.2 changes (0.9-alpha.1 changed nothing in `starter/`). Follow [Upgrading](SETUP.md#upgrading). |
| [0.9-alpha.2](https://github.com/crstdr/minibrain/compare/v0.9-alpha.1...v0.9-alpha.2) | `AGENTS.md` throughout; `CLAUDE.md` is `@AGENTS.md` only; new `.agents/skills/writers/SKILL.md`; `.agents/skills/reflect/SKILL.md` Standing rules and Destinations; `tools/minibrain.py`: take the helper whole; `tools/collection.py` wording; `licenses/minibrain.txt` holder name; `CHANGELOG.md` removed. RepoPrompt CE guidance moves to `hosts/repoprompt.md`. Follow [Upgrading](SETUP.md#upgrading). |
| [0.9-alpha.1](https://github.com/crstdr/minibrain/compare/v0.8...v0.9-alpha.1) | nothing. Optional beta plugins are outside `starter/`. |
| [0.8](https://github.com/crstdr/minibrain/compare/v0.7.0...v0.8) | Since 0.7.0: `AGENTS.md` opening block (IMPROVE) and Checkpoint step 2; `CLAUDE.md` mirrors the opening block; `.agents/skills/reflect/SKILL.md` description and Principles; new `tools/upgrade_diff.py` (run from a clone, not installed). |
| [0.8-alpha.2](https://github.com/crstdr/minibrain/compare/v0.8-alpha.1...v0.8-alpha.2) | nothing; new `tools/upgrade_diff.py` (run from a clone, not installed) and SETUP → Upgrading step 2. |
| [0.8-alpha.1](https://github.com/crstdr/minibrain/compare/v0.7.0...v0.8-alpha.1) | `AGENTS.md` opening block (IMPROVE) and Checkpoint step 2; `CLAUDE.md` mirrors the opening block; `.agents/skills/reflect/SKILL.md` description and Principles. |
| [0.7.0](https://github.com/crstdr/minibrain/compare/v0.7.0-alpha.9...v0.7.0) | `tools/minibrain.py`: take the helper whole. From 0.6.1: the changed sections of `AGENTS.md`, `CLAUDE.md`'s opening block, `tools/minibrain.py` whole and the reflect skill's Destinations; `tools/collection.py` is optional. |
| [0.7.0-alpha.9](https://github.com/crstdr/minibrain/compare/v0.7.0-alpha.8...v0.7.0-alpha.9) | `tools/minibrain.py`: take the helper whole. |
| [0.7.0-alpha.8](https://github.com/crstdr/minibrain/compare/v0.7.0-alpha.7...v0.7.0-alpha.8) | `tools/collection.py` and `tools/minibrain.py`: take both helpers whole; `.agents/skills/reflect/SKILL.md` Destinations: one archive line. `AGENTS.md` `<rpce_tooling_guidance>`: NAME line. Brains without collection.py take tools/minibrain.py and the reflect line. |
| [0.7.0-alpha.7](https://github.com/crstdr/minibrain/compare/v0.7.0-alpha.6...v0.7.0-alpha.7) | `AGENTS.md` opening block, Authority and privacy, Resume step 3 and Checkpoint steps 4–5; `CLAUDE.md` mirrors the opening block; `tools/collection.py`: take the helper whole. |
| [0.7.0-alpha.6](https://github.com/crstdr/minibrain/compare/v0.7.0-alpha.5...v0.7.0-alpha.6) | `AGENTS.md` Checkpoint: express the reflection cue as explicit When/Do conditions and action. |
| [0.7.0-alpha.5](https://github.com/crstdr/minibrain/compare/v0.7.0-alpha.4...v0.7.0-alpha.5) | `AGENTS.md` Checkpoint: reflection invitation after a completed corrective save, unless timing is already agreed. |
| [0.7.0-alpha.4](https://github.com/crstdr/minibrain/compare/v0.7.0-alpha.3...v0.7.0-alpha.4) | `AGENTS.md` opening orientation and Resume step 3; `CLAUDE.md` mirrors the updated opening block. Helpers, memory layout and skills unchanged. |
| [0.7.0-alpha.3](https://github.com/crstdr/minibrain/compare/v0.7.0-alpha.2...v0.7.0-alpha.3) | `AGENTS.md` Authority and privacy, Memory rules, Resume and Checkpoint; `MEMORY.md`; `tools/minibrain.py`; `.agents/skills/reflect/SKILL.md` Destinations. Removes Watch and automatic attention output; retains instruction-only attention to commitments and clarifies delegation versus uncertainty. Collections unchanged. |
| [0.7.0-alpha.2](https://github.com/crstdr/minibrain/compare/v0.7.0-alpha.1...v0.7.0-alpha.2) | Core upgrade: `AGENTS.md` Authority and privacy, Memory rules (new Watch rule), Resume steps 2–3 and Checkpoint; `MEMORY.md` (new `## Watch`); `tools/minibrain.py` and `.agents/skills/reflect/SKILL.md` Destinations. Take the contract and core helper together. Then add `## Watch` to your `MEMORY.md` with a line for each open obligation: dated promise, decision owed, "when X, do Y" rule. Wording-only fixes in `tools/collection.py`. |
| [0.7.0-alpha.1](https://github.com/crstdr/minibrain/compare/v0.6.1...v0.7.0-alpha.1) | Core upgrade: `AGENTS.md` Checkpoint steps 3–5, `tools/minibrain.py` and `.agents/skills/reflect/SKILL.md` Destinations. Take the contract and core helper changes together, including in brains without collections. Optional: new `tools/collection.py`; use the matching core helper, setting `CORE_HELPER` to its local filename. |
| [0.6.1](https://github.com/crstdr/minibrain/compare/v0.6.0...v0.6.1) | nothing |
| [0.6.0](https://github.com/crstdr/minibrain/compare/v0.5.2...v0.6.0) | `AGENTS.md`: Checkpoint, Memory rules, Resume, `<rpce_tooling_guidance>`. `.agents/skills/reflect/SKILL.md`: Destinations |
| [0.5.2](https://github.com/crstdr/minibrain/compare/v0.5.1...v0.5.2) | `AGENTS.md`: Authority and privacy, `<rpce_tooling_guidance>` |
| [0.5.1](https://github.com/crstdr/minibrain/compare/v0.5.0...v0.5.1) | `AGENTS.md`: `<rpce_tooling_guidance>` |
| [0.5.0](https://github.com/crstdr/minibrain/compare/v0.4.2...v0.5.0) | `AGENTS.md`: Memory rules, Resume, `<communication_hygiene>` |
| [0.4.2](https://github.com/crstdr/minibrain/compare/v0.3.1...v0.4.2) | nothing |
| [0.3.1](https://github.com/crstdr/minibrain/compare/v0.3.0...v0.3.1) | `AGENTS.md`: Checkpoint |
| [0.3.0](https://github.com/crstdr/minibrain/compare/v0.2.0...v0.3.0) | new structure (contract, skills, helper, starter files): adapt per [SETUP.md](SETUP.md) |

## 0.10-alpha.1

- minibrain app (alpha) in `plugins/app/` (Agents Map, Roadmap and Tasks): local observability and visualisation for multi-agent work, replacing `plugins/map/` and `plugins/roadmap/`.
- Upgrades also cover the RepoPrompt CE block and plugins.

## 0.9.1

- Agents Map beta: Tidy moves boxes as little as possible and fixes overlaps inside groups; boxes show each RepoPrompt CE workspace's colour, shrink when agents leave and show the names of saved layouts. Nothing in `starter/` changed.

## 0.9.1-alpha.1

- Added the Agents Map beta: a local map of RepoPrompt CE agents and who oversees whom, with a demo on sample data.

## 0.9

- The lighter core from 0.9-alpha.2, with the beta Roadmap and the Agents Map setup guide from 0.9-alpha.1. No changes since the last pre-release.

## 0.9-alpha.2

- **Shorter instructions.** Agents read less than a third as much before they start work.
- **One-step saves.** An agent working alone saves in a single step. Coordination rules apply only when several agents share a brain.
- **Less bookkeeping.** Git keeps the history, so there's no separate changelog to maintain. Open work has no fixed limit.
- **Still tracks what needs you.** Priorities, decisions waiting on you and outcomes you haven't acknowledged stay in view.
- **Clearer reports.** Agents mark each claim as checked, reported by someone else, or inferred.

## 0.9-alpha.1

- Added an optional beta roadmap with a standalone HTML demo and setup guide.
- Added draft setup for the Agents Map beta. The demo snapshot will follow.

## 0.8

- Upgrade diff and the reflect cue for new rules, unchanged from 0.8-alpha.2. No changes since the last pre-release.

## 0.8-alpha.2

- New upgrade diff: shows which changes from each release a brain already has and which it lacks, even with an unknown starting version. SETUP → Upgrading uses it. Nothing in `starter/` changed.

## 0.8-alpha.1

- New rules reach `reflect`. The opening block's IMPROVE line, Checkpoint step 2 and the reflect skill now name what users and agents call them: standing rule, instruction or direction, ground or working rule, preference, lesson, and "remember…". The agent stores each where it will apply; plain facts need only a save.
- Explicit rules are stored without asking first; inferred rules and changes to authority are still confirmed or proposed.
- Untested with agents.

## 0.7.0

- Your agent can now keep lists as well as notes. If it tracks tasks, tickets or contacts, it can store each one as a small Markdown file in a collection folder, then answer questions such as "what is blocked, and by what?" with a query instead of rereading everything. Closed records move to an archive file, so the working list stays short. Collections are optional, and a brain that doesn't use them works as before.
- Saving memory takes one command. The agent runs `minibrain.py commit`, which checks the changes, saves only the files the agent chose, and checks the result. Before 0.7 the agent ran those steps itself.
- An interrupted save no longer leaves memory frozen. In our tests an agent would sometimes lose its place halfway through a save, for example after its context was compacted, and then stop saving for the rest of the session while it waited for you to step in. Now it picks up its own unfinished save and carries on.
- The agent looks for what is due before it starts. At the beginning of each piece of work it checks for commitments that have come due and standing rules that apply, and raises them alongside your request. After fixing a mistake that could happen again, it asks whether you want it to record the lesson.
- Since alpha.9: a `commit` without `--label` while a lock is held is refused with the exact command to rerun.
- We tested the 0.7 pre-releases with more than 20 model configurations on our Project Manager Bench, covering models from Anthropic, OpenAI and xAI, and open models including DeepSeek, GLM, Kimi, MiMo, MiniMax and Mistral.

## 0.7.0-alpha.9

- The helper recovers a writer's own stuck save: `lock <name>` re-issues a lost label when that name already holds the lock, and no longer refuses files left staged by an interrupted save.
- Recovery only: `AGENTS.md` and the output of a normal `lock`, `commit`, `unlock` and `check` are unchanged from alpha.8.

## 0.7.0-alpha.8

- Collections: a `collection.NAME` folder may sit at any depth outside hidden folders, usually inside the space that owns its records. Names stay unique across the brain; a clash is a PROBLEM naming both paths.
- New `archive` and `restore` commands move committed records whole into `collection.NAME.archive.md` beside the folder and back. Archived records keep their IDs and stay in `needs`, `reach`, `_unmet`, `graph` and wikilink checks, but not in SQL tables. Archived content is frozen. Nothing archives automatically.
- Core helper: collection folders and archives at any depth are neither topics nor spaces and do not trigger the changelog gate.
- RepoPrompt lanes are titled with the recorded agent name alone; unnamed lanes keep a title given by the user or their creating overseer, or use a short task name.
- Untested with agents.

## 0.7.0-alpha.7

- Collections: remove the `edit` command; change records by editing their files. Remove the `tags` and `sections` relations, `day()`, `_age` and `_rev`. `graph`, `needs`, `reach` and `_unmet` stay.
- In SQL, characters other than letters, digits and underscores in collection and field names become underscores, and a collection name starting with a digit gains a leading underscore; queries use these mapped names.
- Governed fields keep their save-time check; its refusals now state the entry format.
- Instructions: the opening block's reflection line, the delegation sentence and Resume step 3 return to their 0.6.1 wording. The post-checkpoint reflection cue stays. Failed-commit recovery is shorter; the note for helpers without `commit` moves to SETUP → Upgrading.
- SETUP: the suggested instruction line for a collection now shows how to preview its field lines with one `grep`. Untested hint.
- The removals follow observed non-use in recorded agent runs. No behavioural gain is claimed.

## 0.7.0-alpha.6

- Express the post-checkpoint reflection cue as `When:` conditions and a `Do:` action. Completion, recurring-mistake scope and already-agreed timing remain the conditions.
- Helpers, skills, memory layout and the opening gate are unchanged. We have not tested whether this formatting improves agent behaviour.

## 0.7.0-alpha.5

- Add one post-checkpoint cue: after saving a correction to a mistake that could recur, ask whether to use `reflect` now unless timing is already agreed. Checkpoint verification and lock release precede the invitation.
- Keep the broader reflection trigger outside checkpoints. No helper, skill, memory-layout or test changes. We have not tested whether agents follow the new cue.

## 0.7.0-alpha.4

- Move commitment and trigger attention into the opening orientation used before substantive replies and actions. Retrieve the governing source when needed, then act within authority or raise the matter alongside the request. Remove the duplicate first-reply-only triage sentence from Resume.
- After correcting a mistake that could recur, ask the user whether now is a good time to use `reflect` and incorporate the learning. Other recurring friction or changed guidance still invokes reflection. Factual corrections remain durable state. Existing lesson evidence, scope and authority safeguards remain.
- Keep the Claude opening block identical to the canonical contract. No helper, collection, memory-layout or skill changes. Behavioural improvements have not been validated.

## 0.7.0-alpha.3

- Remove the Watch index template, its maintenance instructions and automatic attention output, including `check --today`. Restore the pre-alpha-2 core helper. Validation, writer locking, gated commits and collections integration are unchanged.
- Keep startup attention to due or overdue commitments and triggered standing rules alongside the current request, within recorded authority. Use recorded delegation when it clearly covers the action. Clarify consequential uncertainty about intent, scope or authority. Corrections and lessons remain durable state.
- Remove the README's "Nothing slips" claim. Performance improvements from this revision have not been established. Collections are unchanged.

## 0.7.0-alpha.2

- Attention at startup, independent of collections. `MEMORY.md` gains a `## Watch` index: one line per obligation the agent must later raise, inspect or perform, with its date or condition, next action, where to look and a link to the canonical rule. Plain `python3 tools/minibrain.py check` prints an attention block: dated lines (`due YYYY-MM-DD: …`) that are overdue or within `WATCH_LEAD_WORKING_DAYS` (2) working days, with a count of the rest and of condition lines. It never changes the exit status; `check --staged` and the checks run by `commit` stay quiet. `check --today YYYY-MM-DD` sets the date when the clock is wrong. Warnings for unreadable dates, long lines and more than 25 lines; none hides work.
- Resume triages that block and Watch in the first reply, alongside the request, retrieves what a Watch line points to and acts only within recorded authority after rechecking the source. A one-off line closes when done or expired; a standing rule stays while it applies. Authority: check recorded delegation before asking permission or deferring. The Work rule no longer reads as "ignore deadlines". Checkpoint counts corrections and lessons as durable state and grooms Watch. Reflect's Destinations routes later obligations to Watch.
- Collections are unchanged. Clarify setup, section editing and recovery messages; commands and validation are unchanged.

## 0.7.0-alpha.1

- Optional `tools/collection.py` supplies `query`, `graph` and one-operation `edit` for Markdown records. Read-only SQL uses an in-memory snapshot with configured numeric fields and prerequisite states, dependency relations and assessment-section presence. Query and graph emit LF-ended, headered TSV with CSV quoting for embedded CR, LF, tabs and quotes. Integral REAL results omit `.0`.
- Collection checks preserve canonical decision History even after governance retirement, report malformed governed entries, reject committed-record deletion and check outgoing wikilinks without Map registration or routine collection-only changelog entries. Section edits preserve peer sections across indented Setext continuations and HTML comments. All section edits refuse records with unclosed code fences or recognized HTML comment blocks starting at the beginning of a line. Close them or edit manually. Unusual inline or reopened comment forms are not comprehensively tracked. Section replacements refuse old bodies containing possible raw ATX H1/H2 or Setext peer headings, including code/comment examples, even if repeated in the payload. Edit manually. Field edits are unchanged. Added-edge checks report cycles even when unrelated cycles already exist. Private SQL indexes no longer collide with collection names. CTE counts work without opening schema reads or writes.
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
