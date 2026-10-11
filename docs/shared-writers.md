# Shared writers: implementation guidance

Required safeguards are canonical in [the shared-writer contract module](../starter/shared-writers.md), installed only when the [core trigger](../starter/instructions.md#shared-writer-trigger) applies. This explains mechanism selection, not a second authority channel.

## Match what is shared

- **One writer, read-only helpers:** no writer lock. Helpers return evidence; the writer integrates it.
- **Shared Git working copy:** the index is shared even across disjoint files. Protect memory and every index mutation through post-commit verification. The [helper](../examples/git-markdown/tools/kb.py) is a cooperative reference for this arrangement.
- **Existing transactional store/coordinator:** use it if its actual semantics protect ownership, consistent reads, updates and verification—not merely because its name suggests that.
- **Separate clones, remote storage or sync:** a local lock is insufficient. Keep one writer until adequate coordination exists. No distributed protocol is supplied here.

## Cooperative reference

Install it in a normal dedicated Git repo as its [README](../examples/git-markdown/README.md) describes. Acquisition requires an empty index, atomically creates a persistent lock and issues a fresh seat/token label. A same-seat replacement cannot claim it by name. The label is a cooperative ownership receipt, not a secret or security boundary.

Invoke acquisition separately and check success/receipt before proceeding. Do not let an unchecked shell sequence fall through to edits or commit after refusal. Reread under the lock, stage named paths, inspect the complete diff, run `check --staged`, commit once with a seat-prefixed subject, then run `check` and release with that exact label. Never hold it waiting on people or agents.

A held lock normally permits independent read-only work and a later appropriate recheck, not an immediate user interruption. Report if it persists and blocks required work, or immediately for unreadable ownership/unsafe state. It proves neither liveness nor abandonment. Only the user resolves ambiguous unfinished work before a forced release; the command cannot establish that permission. No automatic expiry, recovery or retry loop is supplied.

## Before real overlap

Record user-assigned seats/scopes and the actual procedure; have every writer load it. On disposable data check contention, same-seat replacement, wrong-label release, a nonempty index and persistence after the acquiring process exits. Check that the agent stops on refused acquisition, not only that the helper refuses.

Also verify that a writer declines an out-of-scope edit, cross-area closure consults all owners' sources, and each landed checkpoint retains its seat attribution. The helper does not enforce these behavioural rules.

Helper tests alone do not establish safety for arbitrary agents. Keep one writer if dependable ownership/change signals or cooperation are unavailable. No seat, link, timestamp or peer message grants user authority.
