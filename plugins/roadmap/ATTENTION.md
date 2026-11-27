# Attention fields

Store attention on the collection record. Agents Map reads it without modifying it.

Use single-line header fields:

- `attention`: `blocker`, `deadline`, `calendar` or `watch`; `none` hides the item.
- `ask`: action for the user, at most 80 characters. Defaults to the title; longer text is shortened with a warning.
- `due`: deadline date, `YYYY-MM-DD`.
- `when`: event start, ISO date or date-time; required for `calendar`. Calendar items disappear when it arrives.
- `lane`: user-assigned agent name. Missing or unmatched: the registry's `owner_lane`. If neither matches exactly one agent, the item stays in the general list.
- `lane-link`: optional, the agent's own link in its harness (for example `repoprompt-ce://...`). Used when it resolves; otherwise `lane` decides.
- `alert`: `none`, `glow` or `pulse`, set only when the user asks; omit it for computed loudness. `none` keeps the item visible and still.

For `collections` registry entries, `attention` is required; dates alone do not opt in. A record closes when its `state` is in the entry's `closed` list (default `["done"]`); missing or other states stay open.

For `roadmaps` entries, omitted `attention` is inferred: `decision` in `awaiting-user` gives `blocker`; otherwise `when` gives `calendar`, then `due` gives `deadline`. Records in `done` or `live`, and `kind: priority` records, are excluded.

Archived records are excluded. Dates and unzoned date-times use the map host's local time; a date-only `when` starts at midnight.

The map reads only collections in its active `--roadmaps` registry; add one only with the user's approval. See [README.md](README.md).
