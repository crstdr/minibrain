# Tasks

A task is a record in a `collection.<name>/` folder in your own brain. Write only your own tasks. Open the app or another agent's tasks only when the user asks.

## Format

`<id>.md`: `# Title`, single-line `- key: value` headers, optional body.

- `state`: the first word is the state; the rest is detail shown with it (`awaiting-user Ruth`, `blocked Release editor`).
  - `done`: closed. Every other state is open.
  - `in-progress`: amber.
  - `blocked`: red.
  - `awaiting-user [who]`: needs a person; default the user.
  - Anything else, or none: neutral.
- `needs`, `serves`: task IDs, space- or comma-separated. `id` is local; `collection/id` reaches another registered collection. Unresolved references show as unresolved, not errors.
- `due`: `YYYY-MM-DD`.
- `lane`, `lane-link`: the owning agent's name and deep link (`repoprompt-ce://...`); default to the collection's.
- Other headers are shown as written.

## Derived

- Attention: open, and `awaiting-user` or past `due`.
- Blocked: `blocked`, or a `needs` target not `done`.

Agents Map lists each agent's Attention tasks first, then its other open tasks. Roadmap graphs collections whose tasks use `needs` or `serves`.

## Register a collection

Only with the user's approval, add it to `collections.json` (path in `INSTALL.md`); the app rereads it on refresh:

```json
{"version": 1, "collections": [
  {"id": "studio-roadmap", "collection": "/path/to/brain/collection.roadmap", "title": "Studio roadmap", "lane": "Studio lead"}
]}
```

`id` is a unique slug, not `default`; `title`, `lane` and `lane-link` are optional.

## Check

`python3 -B "<app folder>/tasks.py" --collection PATH check` exits 1 on bad headers, dates or cycles and warns on misspelt reserved states. `summary`, `json` and `serve` (standalone Roadmap viewer) take the same arguments; see `--help`. Examples: `sample/collection.roadmap/`.
