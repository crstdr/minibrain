# Set up or adapt a brain

**Read this to install or upgrade; do not copy this guide into the destination's operating instructions.** The [operating contract](../starter/instructions.md) contains the enduring local rules. The [Git/Markdown example](../examples/git-markdown/README.md) supplies optional concrete bindings and templates, not a compulsory tree.

## Reading order

For a first installation (including an existing memory folder), read this guide first, then the following in order before editing the destination. Inspect the target under sections 1–3 below to decide which optional material applies; perform installation and verification under sections 4–5.

1. Read the complete [operating contract](../starter/instructions.md).
2. Read [reflect](../starter/skills/reflect/SKILL.md).
3. Read only applicable modules and references linked below: [shared writers](../starter/shared-writers.md) before enabling overlap, [environment guidance](../starter/environments/rpce.md) where useful, and any chosen implementation's instructions before using its templates or helper.
4. Read the [acceptance checks](acceptance.md) to plan verification; run applicable checks after the local contract and bindings are final.

For an existing minibrain, start with [Upgrading](#upgrading), not a new installation. No file is assumed to have been read merely because it was linked.

## Source versus installed brain

The distribution owns the reusable source contract. After adoption, the destination's integrated contract owns that brain's operating instructions, within higher-priority instructions and the user's authority. Retain its local adaptations and user knowledge; consult the distribution for authorised upgrades, not every session.

Install the contract, locally bound reflection procedure and applicable modules—not this guide, its examples, acceptance checklist or product-development instructions. Ongoing brain maintenance stays in the contract. Maintenance of minibrain itself belongs in [CONTRIBUTING](../CONTRIBUTING.md). The file roles are:

| Material | Role | Destination |
|---|---|---|
| [Setup and upgrades](setup.md) | Adopter procedure | Read and follow; do not install as operating instructions. |
| [Operating contract](../starter/instructions.md) | Enduring rules and local bindings | Integrate into one authoritative local instruction source. All sections stay; fill the bindings. |
| [Reflect](../starter/skills/reflect/SKILL.md) | Reusable maintenance procedure | Reconcile/install one local procedure and bind its verified read path. |
| [Shared writers](../starter/shared-writers.md), [environment guidance](../starter/environments/rpce.md) | Conditional protections/bindings | Integrate only when applicable; required safeguards must then be local. |
| Examples, memory sketch and [acceptance checks](acceptance.md) | Reference and verification | Adapt useful examples and run applicable checks; do not copy wholesale. |
| [CONTRIBUTING](../CONTRIBUTING.md), tests and release files | Maintenance of minibrain itself | Distribution only—not instructions for the user's brain. |

## 1. Inspect before choosing

Read the distribution from its URL or a temporary checkout outside the target memory folder; do not clone it into the brain being adopted. Establish purpose from the user's stated intent. Ask only consequential missing questions; do not repeat onboarding or ask a separate Focus question when already known. Inspect instructions, handling policies, knowledge, host entrypoints, versioning/backups, privacy and other writers. Do not invent permission or capabilities.

Distinguish a new personal memory folder, memory alongside work and an existing brain. Never initialise personal memory inside this public distribution. If persistence is unavailable, report it rather than promise continuity.

## 2. Choose means that satisfy the properties

Preserve the required properties; choose suitable mechanisms rather than starting from a fixed file count. Functions may share a file or use existing tools if they remain unambiguous and bounded.

| Required property | Adaptable implementation |
|---|---|
| A proportionate before-action check of purpose, grounding, improvement and capacity | A prominent local instruction block in the host's verified entrypoints |
| One authoritative home per claim; current state distinct from history | Files, topic boundaries, existing notes or a suitable external store |
| Bounded, action-ready startup from durable state alone | A working index, selected records and an explicit local reading budget |
| Purpose, decisions, permission conditions and lessons survive sessions | Schema and navigation that make them findable before action |
| User standing principles retain their scope and are maintained | One root `<principles>` block, local maintenance duty and bound `reflect` procedure |
| Verified, coherent updates; unfinished work is not discarded | Scoped edits, versioned checkpoints or an existing transaction mechanism |
| When writing may overlap, writers have clear ownership and safe coordination | An adequate existing mechanism or the cooperative-lock reference |

Adaptation changes the means, not the protection. [Source inheritance](source-inheritance.md) explains the original safeguards; [context stewardship](growth.md) explains maintenance for observed failures.

For subject knowledge, use [memory spaces](spaces.md): a note can become a folder with an index, supporting assets and child spaces. `spaces/` is the new file-based default, not a mandatory rename of existing `topics/` or other arrangements. Repeat useful navigation, not root-only instruction/coordination machinery.

Record concrete locations and procedures, and why chosen alternatives preserve the required properties. Prefer permitted tools. Git, Python, filenames and caps are reference choices. Missing essentials are explicit limitations needing a suitable alternative, not silently optional guarantees.

For Git, establish private-memory versioning/remote policy. Before creating a dedicated repo, check whether the target is already inside another one; do not accidentally nest a repository or adopt a public code remote for personal memory. Worktrees and multi-clone sync need appropriate mechanisms; the supplied helper supports only a normal dedicated Git working copy.

## 3. Preserve existing memory

Retain compatible instructions, structure and knowledge. Propose integration rather than automatic replacement. Before migration/substantial restructuring, obtain the user's confirmation and a suitable backup. Inventory purpose, facts, evidence, decisions, permission conditions, procedures, ownership and discovery before/after. Resolve omissions/conflicts before declaring completion.

Include legacy files such as v0.1's MINIBRAIN.md in that inventory. Integrate or explicitly retire/register them; never silently discard their contents to fit a new layout.

The Git reference's regular-file boundary is stricter than the original helper: an existing CLAUDE.md symlink to AGENTS.md will be refused. Inspect it and propose a compatible regular entrypoint if needed, preserving the canonical rules and the user's migration choice. Its gate and any verified import follow the placement rules below. Do not silently follow external targets or replace a working entrypoint.

Prefer an independent checker where available and authorised. If none checked, disclose the limit; do not launch agents without permission. Keep other writers read-only during setup/protocol changes. A replacement does not inherit a predecessor's lock.

## 4. Install a self-contained local contract

Integrate the [core contract](../starter/instructions.md) into one authoritative local instruction source, often AGENTS.md, filling its Local bindings. All sections of the core are intended to remain; it contains no installer-only section to remove. Reconcile equivalent existing instructions rather than appending duplicates, and preserve unrelated host/project rules.

When overlap is possible, integrate the shared-writer module into the local writer section and bind the actual coordination mechanism; otherwise retain the self-contained trigger and adoption source. The [shared-writer guidance](shared-writers.md) explains its rationale and limits. Put useful environment guidance with the local bindings. Do not leave necessary operating rules only in an online link or the installation conversation.

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

### Preserve principles and bind reflection

Install the principles section and its maintenance instruction together in the authoritative local contract. Seed only explicit standing directions and user-confirmed generalisations. Preserve existing rules and their scope; an empty template does not replace them. If existing standing rules remain elsewhere, name their canonical location in the Instructions binding; propose consolidation rather than silently moving or duplicating them. On upgrade, preserve user-owned principles while deliberately merging changes to maintenance guidance.

The distribution supplies [reflect](../starter/skills/reflect/SKILL.md) as a reusable procedure. Integrate it into one local source appropriate to the host—for example, `.agents/skills/reflect/SKILL.md` where that location is supported. Reuse or deliberately reconcile an existing equivalent skill; do not overwrite it or install globally without the user's request.

Bind the contract's reflection reference to the actual local procedure. Verify skill discovery or an explicit read path; a folder name alone proves neither. If the host has no skill mechanism, keep the procedure in a locally readable file and reference it explicitly. Neither the maintenance duty nor the procedure may depend on the installation chat or distribution checkout. Include the bound procedure in the actual persistence/backup policy and verify it remains available after a fresh start; hidden skill directories are not automatically covered by a Markdown checker.

### Add only useful environment bindings

Where the agent uses RPCE, consider the small [RPCE binding](../starter/environments/rpce.md). Install only useful, non-duplicated guidance in the authoritative local instruction source, with other environment bindings—not ahead of or beside the prominent operating gate. Other environments may use equivalent small bindings; no RPCE dependency is introduced. Inspect actual tools and injected instructions rather than infer availability from a product name.

### Record adoption and preserve adaptations

Keep one short adoption record in the installed instructions or an existing canonical source they point to. No new manifest or separate file is required. Record:

- the minibrain source URL and adopted release/ref **plus the exact distribution commit when available**, with adoption date;
- intentional differences and why/where they live: local structures, budgets, entrypoints, procedures, helper changes and optional environment bindings as applicable.

Use the source revision you actually inspected, not a guessed release from VERSION: main can contain unreleased changes after that release. A base commit does not identify uncommitted changes adopted on top of it: record that limit and the retained source needed for a later comparison. If the immutable source cannot be established, record the uncertainty rather than fabricate a pin. An adoption record is provenance, not proof that all requirements passed.

For later authorised changes, follow [Upgrading](#upgrading).

### Bind the local procedures

Fill the **[single canonical bindings template](../starter/instructions.md#local-bindings)**. Use actual local paths/procedures or references to existing canonical records; no additional bindings list or file is required. The [Git example](../examples/git-markdown/README.md#example-local-bindings) shows a filled version, not another schema.

For an existing folder, a Memory binding might be:

```text
Memory: NOTES.md (working index); projects/README.md (subject inventory);
        projects/website.md (current project knowledge, decisions and lessons).
```

This is an example to adapt, not a second binding to retain. Reuse an existing canonical purpose record, or establish the actual purpose once when there is none; bind its location rather than duplicate it in instructions and a memory sketch. Record missing capabilities and safe alternatives honestly. Confirm unresolved human decisions; establish other facts from evidence.

### Finalise before verification

- Replace every binding placeholder with the actual local record. Do not install setup examples, fictional facts or redundant contracts.
- Resolve runtime references locally. Where an optional module is absent, retain its self-contained trigger and recorded adoption source, not a dangling relative link.
- Confirm principles, their maintenance duty, `reflect`, authorised-upgrade safeguards and any required writer/environment rules remain locally available. Check gate mirrors together.
- Seed only known context and real work. The [memory sketch](../starter/memory.md) illustrates content; it is not proof of completeness.

## 5. Verify and report

Test the final installed contract and its actual local dependencies with applicable [acceptance checks](acceptance.md), using disposable data for injected faults and genuinely fresh sessions for independent checks. Do not test an intermediate template and then edit away its instructions. All writers load the revised local instructions before independent writing resumes. Report pass/fail/not-run or observed substitutions. A structural pass does not establish semantic completeness or safe action.

Outstanding acceptance means **prepared, not fully accepted**. Describe useful capability and unresolved limits. Do not force infrastructure or migration merely to satisfy example filenames.

Finish with the local entrypoint, how to resume, preserved/changed content, real decisions needed and checks actually performed. Setup does not imply a public push, tool or service installation, or new data access.

## Upgrading

Upgrade only when authorised. This is a comparison and integration, not a fresh install:

1. Read the destination's local instructions and adoption record first. Establish the adopted source, local adaptations, user knowledge, handling rules and active writers. Keep other writers read-only during protocol changes.
2. Read this guide's current setup requirements, then the proposed operating contract, reflection procedure and applicable modules in [reading order](#reading-order). Compare the adopted source, the proposed upstream revision and the current local contract, including locally adapted procedures. If the old source or adopted uncommitted changes cannot be reconstructed, disclose the comparison limit.
3. Review changes against the reasons for local adaptations. Preserve user knowledge and merge compatible improvements rather than replacing local rules wholesale. Resolve consequential conflicts with the user; preserve the restructuring/backup safeguards. Before replacing a helper, inspect newly managed paths—for example, an existing `spaces/` directory may contain unrelated material requiring an explicit layout decision. Upstream guidance grants no new authority to install tools, migrate structure or publish memory.
4. [Finalise the local result](#finalise-before-verification), then [verify and report](#5-verify-and-report). Record the new adopted source, retained/changed adaptations and outcome together only after verification. Make unverified acceptance limits explicit; all writers reload changed instructions before independent writing resumes.

## Implementation limits

There is no required package, account, database or coordinator. The Git/Markdown reference needs Git and Python; reuse a suitable permitted alternative or report missing capability rather than weakening a safeguard. No filename is assumed to auto-load in every host.

Instructions cannot guarantee model compliance. Static/helper checks do not establish universal host compatibility, safe concurrent behaviour, improved judgment or reduced human effort; see the [verification record](acceptance.md). The reference lock is cooperative and local to a normal Git working copy, not distributed synchronisation or access control. Minibrain supplies no scheduler, notification service or orchestration runtime.

Memory cannot create permission. Never store credentials. Host permissions, services, backups and Git history affect privacy and deletion; minibrain does not encrypt local files. Real personal memory belongs outside the public distribution.
