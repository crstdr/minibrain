# minibrain

A drop-in, folder-based memory system for AI assistants—minimalist, environment-agnostic, and designed for continuity of purpose and work, self-maintenance, and proactive collaboration when human judgment is needed.

**An operating contract, not a prescribed folder tree or an autonomous runtime.** Minibrain tells an existing agent what its memory must preserve, how to resume and save work responsibly, and how to adapt those obligations to its environment. Concrete implementations are references, not compulsory templates. Minimalism means avoiding unnecessary burden—not removing safeguards or mandating a file count.

## Before you act

At the centre is a short operating check: **PURPOSE → GROUND → IMPROVE → CAPACITY**. Before acting, reconnect the next step to the user's purpose, ground it in evidence and authority, learn from recurring friction, and check whether the current context is still fit for the work.

```text
<before_you_act>
Before each substantive response or consequential action:
1. PURPOSE — What outcome is the user pursuing, and does this step advance it?
2. GROUND — What evidence, assumptions, commitments and authority boundaries matter?
3. IMPROVE — Does recurring friction reveal a problem in the approach? Preserve the safeguard's purpose; improve within your authority or propose a change.
4. CAPACITY — Is context still fit for this work? At a safe boundary, preserve continuity and compact when needed.
Apply proportionately. Do not recite the checklist or invent extra work.
</before_you_act>
```

**Recommended placement: the very beginning of your agent's AGENTS.md and CLAUDE.md**, before titles, imports or other guidance, wherever those entrypoints are used. The [starter](starter/instructions.md) begins with the canonical block; [setup](docs/setup.md#4-install-a-self-contained-local-contract) explains identical small mirrors, one authoritative full contract, consent for shared files and verified host loading. This is first in a file, not a way to outrank host instructions. The gate is guidance, not an enforcement mechanism; its behavioural effect remains unvalidated.

## Start with your existing agent

Point your agent at this repository and say:

> Adopt a memory system like https://github.com/crstdr/minibrain, adapted to this folder.

The repository carries the detailed instructions; you need not paste them into your request. The adopting agent should read the [operating contract](starter/instructions.md) and [setup guide](docs/setup.md), establish any missing purpose/scope, preserve existing knowledge and adapt to permitted tools. It records the adopted source revision and local adaptations, then verifies the result. Adoption does not authorise tool installation, publication or automatic replacement of a working brain.

There is no required package, account, database or coordinator. Particular implementations do have prerequisites: the supplied Git/Markdown example uses Git and Python. If a capability is missing, reuse an adequate permitted alternative or report the limitation—not silently weaken a safeguard. No filename is assumed to auto-load in every host.

## What is fixed, and what can change?

| Required property | Adaptable implementation |
|---|---|
| A proportionate before-action check of purpose, grounding, improvement and capacity | A prominent local instruction block in the host's verified entrypoints |
| One authoritative home per claim; current state distinct from history | Files, topic boundaries, existing notes or a suitable external store |
| Bounded, action-ready startup from durable state alone | A working index, selected records and an explicit local reading budget |
| Purpose, decisions, permission conditions and lessons survive sessions | Schema and navigation that make them findable before action |
| Verified, coherent updates; unfinished work is not discarded | Scoped edits, versioned checkpoints or an existing transaction mechanism |
| When writing may overlap, writers have clear ownership and safe coordination | An adequate existing mechanism or the cooperative-lock reference |

The full requirements and canonical resume/checkpoint procedures are in the [operating contract](starter/instructions.md). Adaptation changes the means, not the required protection. [Source inheritance](docs/source-inheritance.md) explains how this builds on the original memory guides.

## Concrete references

- [Memory spaces](docs/spaces.md): start with a note, grow into a folder with an index, assets and child spaces when useful. New file-based installs default to `spaces/`; existing brains need not rename `topics/`.
- [Git/Markdown memory](examples/git-markdown/README.md): the original-style working index, space navigation, outcome changelog, scoped Git checkpoints and standard-library validator/lock helper. Useful procedural detail is included; this is not a required maturity tier.
- [Working-memory sketch](starter/memory.md): an example of content, not an installation requirement or proof the contract is fulfilled.
- [Optional RPCE guidance](starter/environments/rpce.md): a small environment binding, not a core dependency or a copy of the tool manual.
- [Adoption and upgrades](docs/setup.md#record-adoption-and-preserve-adaptations): retain the source revision and local choices so an upgrade does not erase them.
- [Shared-writer guidance](docs/shared-writers.md): when coordination is necessary, what it protects and the limits of the supplied lock.
- [Context stewardship](docs/growth.md): preserve working capabilities and improve a named failure rather than continually reorganise.
- [Installation acceptance](docs/acceptance.md): checks inherited from the original system, including fresh-session and unfinished-work checks.

## Status and boundaries

**v0.2 (experimental)** restores the original system's operating detail and supplies its concrete implementation while allowing equivalent arrangements. It supersedes v0.1's mandatory two-file starting layout. **The unreleased revision adds the operating gate, optional RPCE binding, adoption/upgrade guidance and recursive memory spaces; VERSION and the v0.2.0 tag still identify the last release.** Existing installations are not automatically migrated; the [verification record](docs/acceptance.md#v02-reference-verification) separates tested helper behaviour from unrun agent checks.

The [verification record](docs/acceptance.md#unreleased-adoption-and-space-verification) separates static/helper checks from host loading, upgrades and behavioural effects still to be evaluated.

Instructions cannot guarantee model compliance. Automated tests concern the supplied helper and static guidance, not universal cross-host compatibility, safe behaviour by arbitrary concurrent agents, improved judgment or reduced human effort. The reference lock is cooperative and local to one normal Git working copy; it is neither distributed synchronisation nor access control. Minibrain supplies no scheduler, notification service or orchestration runtime.

Memory cannot create permission. Never store credentials. Host permissions, remote services, backups and Git history affect privacy and deletion; local files are not encrypted by minibrain. Real personal memory belongs outside this public distribution.

See [CONTRIBUTING.md](CONTRIBUTING.md) and the [change history](CHANGELOG.md).

**License:** not yet selected. Public visibility does not itself grant an open-source license; check this section before redistributing or incorporating the material.
