# Set up the Roadmap plugin (beta)

The Roadmap plugin renders any minibrain `collection.<name>/` folder that follows the metadata contract below as a live dependency graph on `http://127.0.0.1`. It requires Python 3.9+ and a browser, with no third-party packages.

Core minibrain (`tools/collection.py`) stays unchanged. `tools/minibrain.py check` remains the authority for core brain and collection integrity (including governed history and cross-collection links); `roadmap.py check` validates the roadmap metadata contract below alongside core header, `source`, and `tags` syntax.

## 1. Install the plugin outside every brain and connect a collection

1. Copy this `roadmap/` plugin folder (including its bundled `sample/`) whole to a directory **outside every brain** (for example `~/tools/roadmap/` or beside `agents-map/`), from a temporary checkout of the source outside the destination. Never place the plugin folder or its `sample/` directory inside a brain: `sample/collection.roadmap/` would collide with your brain's own `collection.roadmap/` under `minibrain.py check`. Keep `LICENSE` intact and never overwrite the destination's own licence.
2. Inside your brain, create a collection folder such as `collection.roadmap/` (or point at an existing `collection.<name>/` folder). Register it under `AGENTS.md` -> This brain as usual for a minibrain collection. Refer to `~/tools/roadmap/sample/collection.roadmap/` (outside the brain) for the file layout.
3. Add one Markdown file per record following the metadata contract below.
4. Validate with both checks (from your brain folder):
   ```sh
   python3 tools/minibrain.py check
   python3 -B ~/tools/roadmap/roadmap.py --collection collection.roadmap check
   ```
5. Open the live view:
   ```sh
   python3 -B ~/tools/roadmap/roadmap.py --collection collection.roadmap --title "Project roadmap"
   ```

The viewer refreshes automatically while open whenever you save a record file. It binds only to `127.0.0.1` and is strictly read-only on your collection files. Server metadata, registry errors, and diagnostics never expose host filesystem paths; configured record fields and body text are served only to the local viewer.

## 2. Metadata contract

Every `.md` file inside `collection.<name>/` starts with `# Title`, optionally one blank line, then single-line `- key: value` headers (no duplicate header keys), followed by a blank line and optional Markdown body prose.

### Mandatory fields (enforced by `roadmap.py check`)

| Field | Required on | Allowed values |
|---|---|---|
| `# Title` | every record | First line of the file |
| `kind` | every record | `priority`, `project`, `decision`, `gap` |
| `state` | every record | `mapped` (priorities), `awaiting-user` (user decisions), `in-progress`, `specified`, `discussed`, `paused`, `blocked`, `missing`, `built-off`, `partial`, `unknown`, `live`, `done` |
| `rank` | `kind: priority` | Finite number setting display order (lower appears first) |

### Linking fields

| Field | Used on | Format |
|---|---|---|
| `serves` | non-priorities | Comma- or space-separated `priority` IDs (local `id` or qualified `NAME/ID`). Records reachable from no priority appear under "Tied to no priority". |
| `needs` | any record | Comma- or space-separated prerequisite IDs (local `id`, qualified `NAME/ID`, archived ID in sibling `collection.<name>.archive.md`, or cross-collection `other/id`). Cross-collection references are shown as external prerequisites and flagged as not validated here. |
| `related` | any record | Comma- or space-separated soft links to other record IDs. |

The viewer treats `done` and `live` as closed states. That viewer rule does not automatically configure core's `tools/collection.py`. If you also query `_unmet` through `tools/collection.py`, add an entry for your roadmap collection while preserving other collection entries:

```python
SATISFIED_STATES["roadmap"] = {"done", "live"}
```

### Optional fields (agent judgement and Agents Map linking)

- `lane`: exact agent name as shown in Agents Map (binds the record and its attention badge to that agent).
- `suggested`: candidate agent name before a task is assigned.
- `owner`: human or role accountability note (prose).
- `short`: short label for priority filter chips.
- `focus`: `yes` to pin a priority ahead of ranked priorities.
- `ask`: concise action prompt (at most 80 characters) shown on attention badges; falls back to `# Title`.
- `due`: `YYYY-MM-DD` deadline date.
- `when`: ISO date or date-time for a calendar event (drops off once started).
- `attention`: `blocker`, `deadline`, `calendar`, `watch`, or `none` (silences the item). If omitted: open `decision` in `awaiting-user` becomes `blocker`; future `when` becomes `calendar`; `due` becomes `deadline`.
- `alert`: `none`, `glow`, or `pulse` (explicit loudness override; if omitted, overdue items or blockers behind soon-due work `pulse`, the top 5 blockers by waiting count and deadlines within 2 working days `glow`, others stay still).
- `days`: estimated remaining workdays (finite number).
- `source`: `'location @ observation'` or `'unknown'` (matches `tools/collection.py`).
- `tags`: space-separated `#tags` (matches `tools/collection.py`).
- `by`, `since`, `checked`: optional reporting metadata.

## 3. Connect to Agents Map (optional)

Keep your local roadmap registry outside every brain (for example `~/Library/Application Support/agents-map/roadmaps.json`). Each entry `id` must be a unique slug (do not use the reserved id `default`):

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

Start Agents Map with the quoted registry path:

```sh
python3 -B agents_map.py \
  --roadmaps "$HOME/Library/Application Support/agents-map/roadmaps.json"
```

Agents Map reads each listed collection read-only on `127.0.0.1`, opens roadmaps in its side-by-side split drawer when you click an agent's roadmap pill or card, and never sends host collection file paths to the browser.

## CLI commands

- `python3 -B roadmap.py --collection PATH check`: validate mandatory fields, core header/source/tag syntax, references, and effective cycles (exits 1 on problems).
- `python3 -B roadmap.py --collection PATH summary`: text digest of priorities, open counts, and items needing the user.
- `python3 -B roadmap.py --collection PATH json`: print the roadmap JSON document.
- `python3 -B roadmap.py --collection PATH serve`: start the local read-only viewer on `127.0.0.1`.
