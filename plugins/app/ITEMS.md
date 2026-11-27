# Collection items

Each agent writes only its own items inside a `collection.<name>/` folder in its own brain. Open the app or another agent's items only when the user asks. The app reads registered collections read-only on `127.0.0.1` and never leaks host paths in metadata or errors.

## Item format

One Markdown file per item (`<id>.md`, slug ID): `# Title`, optional blank line, single-line `- key: value` headers (no duplicate keys), blank line, optional body.

- `state`: first word is the state; the rest is free detail shown with it (for example `awaiting-user Ruth`, `blocked vendor quote`, `done live`). Reserved first words:
  - `done`: closes the item (only state that closes).
  - `in-progress`: open, moving (amber).
  - `blocked`: open, cannot proceed (red).
  - `awaiting-user [who]`: open, needs a person (detail names who; default: the user).
  - Any other first word or no `state`: open, neutral, no colour. `check` warns on near-misses of reserved words.
- `needs`, `serves`: space- or comma-separated references. Bare `id` is local; `collection/id` crosses collections. `serves` may target any item. Unresolved references show as unresolved, not errors.
- `due`: `YYYY-MM-DD`.
- `lane`, `lane-link`: optional overrides of the collection defaults. `lane` is the agent's name; `lane-link` is a harness deep link (for example `repoprompt-ce://...`), used when it resolves, else `lane`.
- Other headers (including `kind`, `owner`, `source`, `tags`): shown generically. No `kind` is special.

## Derived states (never stored)

- **Attention**: open and (`awaiting-user` or past `due`). Future `due` never raises it.
- **Blocked**: state `blocked`, or a `needs` target not `done`.
- **Overdue**: open and past `due` (host local date).

## Views and registry

Registered collections are the app's only item input. Agents Map shows each agent's Attention and open counts and lists Attention items first, then other open items, with the lane link; the Roadmap graph is offered when items have `needs` or `serves`.

List collections in `~/Library/Application Support/minibrain/collections.json` (or `--collections FILE`, kept outside every brain) only with the user's approval. `id` is a unique slug, not `default`; `title`, `lane` and `lane_link` are optional defaults. Changes take effect on the next refresh.

```json
{
  "version": 1,
  "collections": [
    {
      "id": "studio-roadmap",
      "collection": "/path/to/brain/collection.roadmap",
      "title": "Studio roadmap",
      "lane": "Studio lead"
    }
  ]
}
```

## Commands

`tools/minibrain.py check` stays the authority for brain integrity; `roadmap.py check` checks item headers, `due`, cycles and near-miss states. See `sample/collection.roadmap/` in the app folder for examples.

- `python3 -B "<app folder>/roadmap.py" --collection PATH check`: validate; exits 1 on problems.
- `python3 -B "<app folder>/roadmap.py" --collection PATH summary`: Attention and open item digest.
- `python3 -B "<app folder>/roadmap.py" --collection PATH json`: graph document as JSON.
- `python3 -B "<app folder>/roadmap.py" --collection PATH serve [--title TEXT] [--lane NAME] [--port 47615] [--no-open]`: standalone read-only viewer on `127.0.0.1`.
