# Set up or adapt a brain

Installer guidance, not an instruction to restructure the distribution repository. The [operating contract](../starter/instructions.md) owns behaviour. The [Git/Markdown example](../examples/git-markdown/README.md) is concrete implementation guidance, not a compulsory tree or later upgrade.

## 1. Inspect before choosing

Read the distribution from its URL or a temporary checkout outside the target memory folder; do not clone it into the brain being adopted. Establish purpose from the user's stated intent. Ask only consequential missing questions; do not repeat onboarding or ask a separate Focus question when already known. Inspect instructions, handling policies, knowledge, host entrypoints, versioning/backups, privacy and other writers. Do not invent permission or capabilities.

Distinguish a new personal memory folder, memory alongside work and an existing brain. Never initialise personal memory inside this public distribution. If persistence is unavailable, report it rather than promise continuity.

## 2. Choose means that satisfy the properties

Preserve the functions: operating instructions; bounded working index; authoritative current knowledge/history; discovery independent of tasks; durable outcomes; checks and coherent saves. Functions may share a file or use existing tools if they remain unambiguous and bounded. Do not start from a fixed file count.

For subject knowledge, use [memory spaces](spaces.md): a note can become a folder with an index, supporting assets and child spaces. `spaces/` is the new file-based default, not a mandatory rename of existing `topics/` or other arrangements. Repeat useful navigation, not root-only instruction/coordination machinery.

Record each function's concrete location/procedure and why an alternative provides the protection. Prefer permitted tools. Git, Python, filenames and caps are reference choices. Missing essentials are explicit limitations needing a suitable alternative, not silently optional guarantees.

For Git, establish private-memory versioning/remote policy. Before creating a dedicated repo, check whether the target is already inside another one; do not accidentally nest a repository or adopt a public code remote for personal memory. Worktrees and multi-clone sync need appropriate mechanisms; the supplied helper supports only a normal dedicated Git working copy.

## 3. Preserve existing memory

Retain compatible instructions, structure and knowledge. Propose integration rather than automatic replacement. Before migration/substantial restructuring, obtain the user's confirmation and a suitable backup. Inventory purpose, facts, evidence, decisions, permission conditions, procedures, ownership and discovery before/after. Resolve omissions/conflicts before declaring completion.

Include legacy files such as v0.1's MINIBRAIN.md in that inventory. Integrate or explicitly retire/register them; never silently discard their contents to fit a new layout.

The Git reference's regular-file boundary is stricter than the original helper: an existing CLAUDE.md symlink to AGENTS.md will be refused. Inspect it and propose a compatible regular entrypoint if needed, preserving the canonical rules and the user's migration choice. Its gate and any verified import follow the placement rules below. Do not silently follow external targets or replace a working entrypoint.

Prefer an independent checker where available and authorised. If none checked, disclose the limit; do not launch agents without permission. Keep other writers read-only during setup/protocol changes. A replacement does not inherit a predecessor's lock.

## 4. Install a self-contained local contract

Create/update one authoritative local instruction source with the core contract and concrete bindings. Install the shared-writer module there only when overlap is possible; otherwise retain the core's trigger without loading the whole module at every startup. Preserve unrelated host/project rules. Do not leave necessary rules only in an online link or the installation conversation.

### Put the operating gate first

Recommend the exact opening `<before_you_act>` block from [starter/instructions.md](../starter/instructions.md) at the **very beginning of both AGENTS.md and CLAUDE.md where those files are used**—before titles, comments, imports and the longer rules. Keep its four checks and proportionality sentence together, not scattered among other guidance. Create a missing entrypoint only when the actual setup needs it; other hosts use an equivalent verified entrypoint, not irrelevant filenames. Skill files whose required frontmatter must come first remain thin pointers, not gate copies.

If a host entrypoint requires leading metadata, preserve its format and record that literal first-position placement is unavailable there. If the user declines the gate or its placement, record that decision as an adaptation/limitation rather than repeatedly asking or claiming unchanged adoption.

For an existing brain, propose the insertion while preserving its rules. Shared instruction files affect other readers: obtain explicit approval from the user with authority over those files before changing them. Do not install into somebody else's project instructions or confuse the brain's entrypoint with unrelated shared repository guidance. Keep other writers read-only during an approved protocol change.

Target the chosen entrypoints that load this brain's contract, not every nested instruction file. Do not change user-wide global instructions without an explicit request; those can affect other projects. Inspect the combined loading path across parent, project and nested instructions rather than propagating copies blindly.

Declare one local authoritative gate copy (usually at the top of the full contract). Copies at other active entrypoints are small identical mirrors; update them in the same change and check equality whenever the gate changes. Do not maintain competing copies of the full contract or require an online checkout at runtime. Record the adopted source revision; a deliberate wording change is a local adaptation, not the unchanged reviewed gate.

Verify the host's actual loading path before choosing a pointer:
- If it already loads the full local contract, **do not add an import that loads the whole contract again**. An existing second entrypoint can keep its gate mirror and unrelated host rules without that redundant import.
- If it reads CLAUDE.md, supports the relevant import syntax and does **not** already load the full contract, put the gate first and the import of the authoritative local contract after it. The [worked example](../examples/git-markdown/CLAUDE.md.example) shows this case only. A CLAUDE-only installation may instead keep the full contract there, with the gate first and no import.
- If imports or automatic loading are unavailable, use a verified explicit read/startup instruction naming the real local source. Do not claim installation acceptance until that path works; record the limitation if it cannot be verified.

An import may expose the small gate a second time. Identical wording is not a second reporting task; do not promise host de-duplication or harmlessness without testing. Observe loading, avoid redundant full-contract exposure, and report what remains unverified. “First” means first in the file, not first in the entire model context or higher priority than host instructions.

### Add only useful environment bindings

Where the agent uses RPCE, consider the small [RPCE binding](../starter/environments/rpce.md). Install only useful, non-duplicated guidance in the authoritative local instruction source, with other environment bindings—not ahead of or beside the prominent operating gate. Other environments may use equivalent small bindings; no RPCE dependency is introduced. Inspect actual tools and injected instructions rather than infer availability from a product name.

### Record adoption and preserve adaptations

Keep one short adoption record in the installed instructions or an existing canonical source they point to. No new manifest or separate file is required. Record:

- the minibrain source URL and adopted release/ref **plus the exact distribution commit when available**, with adoption date;
- intentional differences and why/where they live: local structures, budgets, entrypoints, procedures, helper changes and optional environment bindings as applicable.

Use the source revision you actually inspected, not a guessed release from VERSION: main can contain unreleased changes after that release. If the immutable source cannot be established, record the uncertainty rather than fabricate a pin. An adoption record is provenance, not proof that all requirements passed.

On an authorised upgrade, read this record first. Compare the adopted source, the proposed upstream revision and the current local contract. Review changes against the reasons for local adaptations; merge compatible improvements rather than replacing local rules or personal knowledge wholesale. Resolve consequential conflicts with the user and preserve the existing restructuring/backup rules. Before replacing a helper, inspect any paths it will newly manage—for example, this reference treats an existing `spaces/` directory as memory, so unrelated content there needs an explicit layout decision. Verify the changed bindings and record the new adopted base, retained/changed adaptations and outcome together. If the old source is unavailable, disclose the comparison limit. Do not turn upstream guidance into new authority or automatically install tools, migrate structure or publish memory.

### Bind the local procedures

Record:
- purpose, scope and actual instruction entrypoints, including the authoritative gate copy and any mirrors;
- the canonical adoption record described above;
- working index and explicit reading/capacity budget;
- subject sources, discovery and outcome/history locations;
- exact resume/checkpoint check and persistence procedures;
- privacy/versioning policy and dependencies;
- delegated maintenance authority and its limits; assignments and coordination when overlap is possible.

Bindings describe implementation, not a second copy of the principles. Host pointers cite authoritative local instructions; the gate mirror is the small, explicit exception to copying. A pointer without its target is not portable. Keep both the gate and the procedures it orients: the short check does not replace resume, checkpoint, authority or writer safeguards.

Adapt distribution-relative links to actual local targets. When a conditional module is not installed, retain its self-contained trigger without a dangling file link; obtain and adopt the module before enabling overlap. Verify links after installation, not just in this distribution.

Seed only known context and real work. The [memory sketch](../starter/memory.md) is illustrative, not proof of completeness.

## 5. Verify and report

Run applicable [acceptance checks](acceptance.md), using disposable data for injected faults and genuinely fresh sessions for independent checks. Report pass/fail/not-run or observed substitutions. A structural pass does not establish semantic completeness or safe action.

Outstanding acceptance means **prepared, not fully accepted**. Describe useful capability and unresolved limits. Do not force infrastructure or migration merely to satisfy example filenames.

Finish with the local entrypoint, how to resume, preserved/changed content, real decisions needed and checks actually performed. Setup does not imply a public push, service installation or new data access.
