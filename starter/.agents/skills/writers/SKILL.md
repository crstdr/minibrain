---
name: writers
description: Save safely while MEMORY.md → Owners lists more than one writer.
---

Each save:
1. Run `python3 tools/minibrain.py lock <name>` on its own, unpiped. Continue only if it prints "lock acquired"; keep the label.
2. Re-read the files you will edit, then edit and stage them.
3. Commit with `--label <label>` and a subject starting `<name>: `, then run `python3 tools/minibrain.py unlock <label>`.

- `<name>` is your name under Owners; one session per name.
- Never hold the lock while waiting for a person or agent.
- Another writer holds the lock: no edits, staging or commits; tell the user if it blocks you. `unlock --force` only with the user's approval.
- The lock covers this folder only; separate clones or synced copies need a single writer.
