# minibrain

A drop-in, folder-based memory system for AI assistants—minimalist, environment-agnostic, and designed for continuity of purpose and work, self-maintenance, and proactive collaboration when human judgment is needed.

**An operating contract, not a prescribed folder tree or an autonomous runtime.** Minibrain tells an existing agent what its memory must preserve, how to resume and save work responsibly, and how to adapt those obligations to its environment. Concrete implementations are references, not compulsory templates. Minimalism means avoiding unnecessary burden—not removing safeguards or mandating a file count.

## For humans

Create or choose a folder for a project or area of your life—your car, finances, holidays, or anything else you want help managing. Existing notes can stay.

Open your preferred coding agent in that folder—Claude Code, Codex, OpenCode, Pi, or another—and ask:

> Install https://github.com/crstdr/minibrain into this folder, adapting it to my needs and preserving existing instructions and knowledge.

The agent will guide you through setup. Your memory stays in your folder; you don't need to copy this repository into it.

## For agents installing minibrain

Read this repository online or use a temporary checkout outside the destination; do not clone it into the brain.

**First installation, including adapting an existing memory folder:** start with [Setup](docs/setup.md) and follow it in order.

**Upgrading an existing minibrain:** first read its local instructions and adoption record, then follow [Upgrading](docs/setup.md#upgrading). Preserve user knowledge and local adaptations.

The setup guide directs the reading order:

1. [Operating contract](starter/instructions.md)—the enduring instructions to integrate locally.
2. [Reflect](starter/skills/reflect/SKILL.md)—the maintenance procedure to install and bind locally.
3. Applicable modules and implementation examples—only those needed for this installation, as directed by setup.
4. [Acceptance checks](docs/acceptance.md)—verify the final local setup and report limitations.

After installation, use the **destination's local instructions**. This repository is the installation and upgrade source, not an everyday runtime dependency.

---

**Experimental.** See [verification](docs/acceptance.md) and [limitations](docs/setup.md#implementation-limits), [contributing](CONTRIBUTING.md) and [change history](CHANGELOG.md). No scheduler or autonomous runtime is supplied.

**License:** not yet selected. Public visibility does not itself grant an open-source license; check before redistributing or incorporating the material.
