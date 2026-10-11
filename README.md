# minibrain

A drop-in, folder-based memory system for AI assistants—minimalist, environment-agnostic, and designed for continuity of purpose and work, self-maintenance, and proactive collaboration when human judgment is needed.

**An operating contract, not a prescribed folder tree or an autonomous runtime.** Minibrain tells an existing agent what its memory must preserve, how to resume and save work responsibly, and how to adapt those obligations to its environment. Concrete implementations are references, not compulsory templates. Minimalism means avoiding unnecessary burden—not removing safeguards or mandating a file count.

## Start with your existing agent

Point your agent at this repository and say:

> Read README.md, starter/instructions.md and docs/setup.md. Set up or adapt memory in [my chosen folder] to help me with [purpose]. Inspect what is already there. Preserve the operating principles and existing knowledge; choose structures and permitted tools that fit this environment. Explain consequential changes before making them. Do not install tools or publish my memory without permission.

The agent should inspect the existing setup, select or adapt an implementation, record the actual local operating instructions, and verify the resulting memory. It should not automatically replace a working system, copy every example, or impose two files. See [setup and adaptation](docs/setup.md).

There is no required package, account, database or coordinator. Particular implementations do have prerequisites: the supplied Git/Markdown example uses Git and Python. If a capability is missing, reuse an adequate permitted alternative or report the limitation—not silently weaken a safeguard. No filename is assumed to auto-load in every host.

## What is fixed, and what can change?

| Required property | Adaptable implementation |
|---|---|
| One authoritative home per claim; current state distinct from history | Files, topic boundaries, existing notes or a suitable external store |
| Bounded, action-ready startup from durable state alone | A working index, selected records and an explicit local reading budget |
| Purpose, decisions, permission conditions and lessons survive sessions | Schema and navigation that make them findable before action |
| Verified, coherent updates; unfinished work is not discarded | Scoped edits, versioned checkpoints or an existing transaction mechanism |
| When writing may overlap, writers have clear ownership and safe coordination | An adequate existing mechanism or the cooperative-lock reference |

The full requirements and canonical resume/checkpoint procedures are in the [operating contract](starter/instructions.md). Adaptation changes the means, not the required protection. [Source inheritance](docs/source-inheritance.md) explains how this builds on the original memory guides.

## Concrete references

- [Git/Markdown memory](examples/git-markdown/README.md): the original-style working index, topics, map, outcome changelog, scoped Git checkpoints and standard-library validator/lock helper. Useful procedural detail is included; this is not a required maturity tier.
- [Working-memory sketch](starter/memory.md): an example of content, not an installation requirement or proof the contract is fulfilled.
- [Shared-writer guidance](docs/shared-writers.md): when coordination is necessary, what it protects and the limits of the supplied lock.
- [Context stewardship](docs/growth.md): preserve working capabilities and improve a named failure rather than continually reorganise.
- [Installation acceptance](docs/acceptance.md): checks inherited from the original system, including fresh-session and unfinished-work checks.

## Status and boundaries

**v0.2 (experimental)** restores the original system's operating detail and supplies its concrete implementation while allowing equivalent arrangements. It supersedes v0.1's mandatory two-file starting layout. Existing installations are not automatically migrated; the [verification record](docs/acceptance.md#v02-reference-verification) separates tested helper behaviour from unrun agent checks.

Instructions cannot guarantee model compliance. Automated tests concern the supplied helper, not universal cross-host compatibility, safe behaviour by arbitrary concurrent agents, improved judgment or reduced human effort. The reference lock is cooperative and local to one normal Git working copy; it is neither distributed synchronisation nor access control. Minibrain supplies no scheduler, notification service or orchestration runtime.

Memory cannot create permission. Never store credentials. Host permissions, remote services, backups and Git history affect privacy and deletion; local files are not encrypted by minibrain. Real personal memory belongs outside this public distribution.

See [CONTRIBUTING.md](CONTRIBUTING.md) and the [change history](CHANGELOG.md).

**License:** not yet selected. Public visibility does not itself grant an open-source license; check this section before redistributing or incorporating the material.
