# RepoPrompt CE

Add this block to `AGENTS.md`, after the XML blocks at the top, when the brain is used in RepoPrompt CE. Keep its overseer clauses only for an assigned overseer role.

<rpce_tooling_guidance>
- NAME — Title your lane `<name>` if you have a recorded agent name; otherwise keep a title the user or your creating overseer gave, or use a task name of a few words.
- ORACLES — Reserve for consequential advice, reviews or second opinions, normally one-shot rather than frequent back-and-forth. Prepare focused, sufficient context first; use Context Builder when useful. Weigh the benefit against cost, delay and urgency. Follow agreed user preferences and delegation; otherwise ask first. Authorised built-in workflows cover their scoped Oracle use.
- WORKFLOWS — For Investigate, Deep Plan, Orchestrate or Review, follow agreed user preferences and delegation; otherwise ask first. Choose by task; keep simple work direct. Answer workflow questions within stated preferences or delegated authority; clarify consequential gaps.
- PLAN — Deep Plan for substantial new development or design; Investigate for diagnosis and research. Deep Plan offers up-front, mid-flow or hands-off user involvement.
- BUILD — Implement a suitable plan directly, or use Orchestrate for complex work through authorised subagents; reuse existing plans.
- REVIEW — Use Review for post-implementation code review when warranted; it complements, not replaces, tests.
- CONTEXT — Use Context Builder independently when context discovery and curation warrant the overhead. Omitted response type or `clarify` prepares context only; `question`, `plan` and `review` also consult Oracles and follow ORACLES.
- CAPACITY — Compaction: `self_compact`. Above 40% context load, consider compaction at a useful boundary. Follow agreed user preferences and delegation; otherwise ask first.
- MAP — The minibrain app shows the user their agents' tasks and priorities. For its address, adding it as a browser app or raising an item, read `~/Library/Application Support/minibrain/INSTALL.md`; absent means not installed.

Overseer role only:
- HOME — Keep coordination memory separate from lanes' working files. Oversight links grant no file-edit authority.
- ACCESS — Use granted links. If unlinked and eligible, use `become_overseer` when available; otherwise request access. Never bypass missing links or tools.
- CREATE — Create authorised lanes with `create_lane`; specify the target `workspace` when different from yours.
- TRACK — In existing memory: lane/task, last verified state/date, next action/owner and decisions. No duplicate ledger.
- FLOW — For linked lanes, wait when the result is needed now; otherwise rely on enabled Auto-wake. Idle ≠ complete: verify the outcome.
</rpce_tooling_guidance>
