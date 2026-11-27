# Roadmap collections

A minibrain `collection.<name>/` following the contract below renders as a live dependency graph on `127.0.0.1` via `roadmap.py` (standalone) or inside Agents Map. `tools/minibrain.py check` stays the authority for brain and collection integrity; `roadmap.py check` adds the contract below.

To add one in a brain: create `collection.roadmap/` (or use an existing `collection.<name>/`), register it under This brain in `AGENTS.md`, add one Markdown file per record (see `sample/collection.roadmap/` in the app folder for the layout), and run both `python3 tools/minibrain.py check` and `python3 -B "<app folder>/roadmap.py" --collection collection.roadmap check`.

## Metadata contract

Each record file: `# Title`, an optional blank line, single-line `- key: value` headers (no duplicate keys), a blank line, then optional body text. ID lists are comma- or space-separated.

### Mandatory fields (checked by `roadmap.py check`)

| Field | Required on | Allowed values |
|---|---|---|
| `# Title` | every record | first line |
| `kind` | every record | `priority`, `project`, `decision`, `gap` |
| `state` | every record | `mapped` (priorities), `awaiting-user` (user decisions), `in-progress`, `specified`, `discussed`, `paused`, `blocked`, `missing`, `built-off`, `partial`, `unknown`, `live`, `done` |
| `rank` | `kind: priority` | number; lower shows first |

### Linking fields

| Field | Used on | Format |
|---|---|---|
| `serves` | non-priorities | `priority` IDs: local `id` or `NAME/ID`. Records not reached by any priority show under "Tied to no priority". |
| `needs` | any record | prerequisite IDs: local `id`, `NAME/ID`, an archived ID in sibling `collection.<name>.archive.md`, or `other/id` in another collection (shown as external, not validated). |
| `related` | any record | soft links to record IDs |

`done` and `live` count as closed. For `_unmet` queries through `tools/collection.py` to agree, add this, keeping other entries:

```python
SATISFIED_STATES["roadmap"] = {"done", "live"}
```

### Optional fields

- `lane`: agent name as shown in Agents Map; binds the record and its badge to that agent (rules in [`ATTENTION.md`](ATTENTION.md)).
- `suggested`: candidate agent before assignment.
- `owner`: accountability note.
- `short`: label for priority filter chips.
- `focus`: `yes` pins a priority ahead of ranked ones.
- Attention fields (`attention`, `ask`, `due`, `when`, `lane-link`, `alert`): see [`ATTENTION.md`](ATTENTION.md). Computed loudness: overdue items and blockers holding soon-due work pulse; the top 5 blockers by waiting count and deadlines within 2 working days glow; others stay still.
- `days`: remaining workdays (number).
- `source`, `tags`: same syntax as `tools/collection.py`.
- `by`, `since`, `checked`: reporting metadata.

## Connect to Agents Map (optional)

List the collection in a registry outside every brain (for example `~/Library/Application Support/minibrain/roadmaps.json`); `id` is a unique slug, not `default`:

```json
{
  "version": 1,
  "roadmaps": [
    {
      "id": "studio-roadmap",
      "title": "Studio roadmap",
      "collection": "/path/to/brain/collection.roadmap",
      "owner_lane": "Studio lead",
      "attention": true
    }
  ]
}
```

Start Agents Map with `--roadmaps "<registry path>"`; with its login item on, rerun the full start command from `INSTALL.md`. Clicking an agent's roadmap pill or card opens the roadmap in a side drawer.

## Commands

- `python3 -B roadmap.py --collection PATH check`: mandatory fields, core header, `source` and `tags` syntax, references and cycles; exits 1 on problems.
- `python3 -B roadmap.py --collection PATH summary`: priorities, open counts and items needing the user.
- `python3 -B roadmap.py --collection PATH json`: the roadmap as JSON.
- `python3 -B roadmap.py --collection PATH serve [--title TEXT] [--port 47615]`: read-only viewer on `127.0.0.1` (refreshes on save; never leaks host paths in metadata or errors).
