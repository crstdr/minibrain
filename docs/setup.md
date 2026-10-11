# Set up or adapt a brain

Installer guidance, not an instruction to restructure the distribution repository. The [operating contract](../starter/instructions.md) owns behaviour. The [Git/Markdown example](../examples/git-markdown/README.md) is concrete implementation guidance, not a compulsory tree or later upgrade.

## 1. Inspect before choosing

Establish purpose from the user's stated intent. Ask only consequential missing questions; do not repeat onboarding or ask a separate Focus question when already known. Inspect instructions, handling policies, knowledge, host entrypoints, versioning/backups, privacy and other writers. Do not invent permission or capabilities.

Distinguish a new personal memory folder, memory alongside work and an existing brain. Never initialise personal memory inside this public distribution. If persistence is unavailable, report it rather than promise continuity.

## 2. Choose means that satisfy the properties

Preserve the functions: operating instructions; bounded working index; authoritative current knowledge/history; discovery independent of tasks; durable outcomes; checks and coherent saves. Functions may share a file or use existing tools if they remain unambiguous and bounded. Do not start from a fixed file count.

Record each function's concrete location/procedure and why an alternative provides the protection. Prefer permitted tools. Git, Python, filenames and caps are reference choices. Missing essentials are explicit limitations needing a suitable alternative, not silently optional guarantees.

For Git, establish private-memory versioning/remote policy. Before creating a dedicated repo, check whether the target is already inside another one; do not accidentally nest a repository or adopt a public code remote for personal memory. Worktrees and multi-clone sync need appropriate mechanisms; the supplied helper supports only a normal dedicated Git working copy.

## 3. Preserve existing memory

Retain compatible instructions, structure and knowledge. Propose integration rather than automatic replacement. Before migration/substantial restructuring, obtain the user's confirmation and a suitable backup. Inventory purpose, facts, evidence, decisions, permission conditions, procedures, ownership and discovery before/after. Resolve omissions/conflicts before declaring completion.

Include legacy files such as v0.1's MINIBRAIN.md in that inventory. Integrate or explicitly retire/register them; never silently discard their contents to fit a new layout.

The Git reference's regular-file boundary is stricter than the original helper: an existing CLAUDE.md symlink to AGENTS.md will be refused. Inspect it and propose a regular thin pointer (for example `@AGENTS.md` only where the host supports it), preserving the canonical rules and the user's migration choice. Do not silently follow external targets or replace a working entrypoint.

Prefer an independent checker where available and authorised. If none checked, disclose the limit; do not launch agents without permission. Keep other writers read-only during setup/protocol changes. A replacement does not inherit a predecessor's lock.

## 4. Install a self-contained local contract

Create/update one authoritative local instruction source with the core contract and concrete bindings. Install the shared-writer module there only when overlap is possible; otherwise retain the core's trigger without loading the whole module at every startup. Preserve unrelated host/project rules. Do not leave necessary rules only in an online link or the installation conversation.

Record:
- purpose, scope and actual instruction entrypoint;
- working index and explicit reading/capacity budget;
- subject sources, discovery and outcome/history locations;
- exact resume/checkpoint check and persistence procedures;
- privacy/versioning policy and dependencies;
- assignments and coordination when overlap is possible.

Bindings describe implementation, not a second copy of the principles. Host pointers should cite authoritative local instructions. A configured host might use AGENTS.md or a CLAUDE.md import, but verify actual host behaviour; otherwise provide a startup prompt naming the real file. A pointer without its target is not portable.

Adapt distribution-relative links to actual local targets. When a conditional module is not installed, retain its self-contained trigger without a dangling file link; obtain and adopt the module before enabling overlap. Verify links after installation, not just in this distribution.

Seed only known context and real work. The [memory sketch](../starter/memory.md) is illustrative, not proof of completeness.

## 5. Verify and report

Run applicable [acceptance checks](acceptance.md), using disposable data for injected faults and genuinely fresh sessions for independent checks. Report pass/fail/not-run or observed substitutions. A structural pass does not establish semantic completeness or safe action.

Outstanding acceptance means **prepared, not fully accepted**. Describe useful capability and unresolved limits. Do not force infrastructure or migration merely to satisfy example filenames.

Finish with the local entrypoint, how to resume, preserved/changed content, real decisions needed and checks actually performed. Setup does not imply a public push, service installation or new data access.
