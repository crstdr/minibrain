# Set up the roadmap (beta)

1. Download [roadmap.html](https://raw.githubusercontent.com/crstdr/minibrain/main/plugins/roadmap/roadmap.html) or copy it from a temporary checkout of the source outside the destination. Never clone into the destination. Save the file as `roadmap.html`, for example next to `MEMORY.md`. Refresh an existing roadmap rather than replacing its renderer. Keep the MIT header comment. Retain any separate notices under `licenses/` as described in the [core setup guide](../../SETUP.md#2-adapt-the-starter). Never replace the destination's own licence.
2. Read the destination's instructions, `MEMORY.md` and linked topic notes if present. Otherwise use the folder's own notes. Gather supported priorities, open work, owners, hard dependencies, deadlines and decisions waiting on the user. Trace each item to its source and keep unknowns explicit. If there's no usable plan, ask the user for one. Show the result from their answer, or show an empty roadmap if the plan is still unknown. Don't present sample items as the user's plan.
3. Replace the object in `const DATA = {...};`. Use JSON and encode literal `<` in strings as `\u003c` so note text cannot end the script block. Leave the renderer unchanged. Remove the visible “Sample data” label when you replace the demo data. Check that every ID reference resolves and dependencies have no cycles.
4. In a brain, add the roadmap to its existing navigation (`AGENTS.md` → This brain, `Map.md` or `MAP.md`, as applicable). Label it a derived view and point to the notes as the source. Keep the file within the destination's privacy and storage policy.
5. Open the local HTML in a browser for the user: use `open roadmap.html` on macOS or the platform's equivalent. Check that the graph, waiting decisions and critical path display when the plan has them.

## DATA fields

- `nodes`: array of records, described below.
- `order`: priority IDs in display order. Include every priority.
- `short`: object mapping those IDs to short labels for the graph and filters.
- `generated`: snapshot date, as a `YYYY-MM-DD` string.

Give each record these fields:

- `id`: unique lowercase slug (letters, digits and hyphens); reserve `all` for the view filter.
- `title`: short display title.
- `kind`: `priority`, `project`, `decision` or `gap`.
- `state`: `mapped` for priorities; `awaiting-user` for decisions waiting on the user. Other supported states: `missing`, `blocked`, `built-off`, `partial`, `unknown`, `discussed`, `specified`, `paused`, `in-progress`, `live`, `done`.
- `owner`: accountable person, role or agent; empty string if unknown.
- `serves`: comma-separated priority IDs, or an empty string. Use `needs` on priority records to connect the graph.
- `by`: who reported the state, or an empty string.
- `source`: local note path and heading, such as `MEMORY.md#Open threads`.
- `importance`: source importance label, or an empty string. Retained for compatibility; not displayed.
- `body`: current state and next action. Include any deadline, or the question and options for a user decision.
- `needs`: array of IDs of hard prerequisites. Put the prerequisite's ID on the item that needs it.
- `related`: array of IDs of related items that are not hard prerequisites. Do not use these links to create layout cycles.
- `ext`: array of descriptions of user actions not represented by records. Use empty arrays where there are no entries.
- `daysLeft`: nonnegative number of workdays remaining; use `0` for priorities and finished work, and `null` or omit when unknown. Unknown durations count as zero for the calculation. Model pending decisions explicitly rather than guessing their wait times.

The path is the longest chain of estimated work in the current view, not a delivery date. Slack is how much extra work an item can take without lengthening that estimate. Deadlines in `body` do not affect the calculation.

To refresh, reread the source notes, rebuild the DATA object, update `generated` and reopen the same file. Keep the notes authoritative.
