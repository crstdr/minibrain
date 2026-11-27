# Agents Map (beta)

Agents Map is a local map of your agents and who oversees whom. Its built-in connector works with RepoPrompt CE on macOS and reads agent state without changing it.

## Run

Requires macOS, RepoPrompt CE, Python 3.9 or later, and a browser. Run from this folder (kept outside every brain):

```sh
python3 -B agents_map.py
```

The map opens at `http://127.0.0.1:47613/`. Add `--no-open` to start without opening a browser, or `--port N` to choose another port. Stop with Ctrl-C.

Start at login: `python3 -B agents_map.py --login-item on` with the same options you run with; `--login-item off` stops it and removes the login item. Supported browsers can install the page as an app.

Your arrangement (layouts, groups, saves) is kept in `~/Library/Application Support/agents-map` (`--state-dir DIR`), never in RepoPrompt CE's folder or any brain.

## Update and remove

Replace only the app folder, rerun your start command, and update the source commit in `~/Library/Application Support/agents-map/INSTALL.md`. To remove, run `python3 -B agents_map.py --login-item off` and delete the app folder and `INSTALL.md` (saved layouts in the state folder stay). If the app folder is already gone, run the two cleanup commands `--login-item on` printed (also in `INSTALL.md`), then delete `INSTALL.md`.

## Connect roadmaps and attention items

- **Collection-backed roadmaps and attention items:** pass `--roadmaps FILE` pointing to a JSON registry kept outside every brain (quote the path if it contains spaces). Put roadmap collections under `roadmaps` and any other attention-bearing collections under `collections` (see [`ATTENTION.md`](ATTENTION.md) for the header fields):

```sh
python3 -B agents_map.py \
  --roadmaps "$HOME/Library/Application Support/agents-map/roadmaps.json"
```

Example registry (`id` must be a unique slug across both arrays and not `default`; `closed` defaults to `["done"]` when omitted):

```json
{
  "version": 1,
  "roadmaps": [
    {
      "id": "project-roadmap",
      "title": "Project roadmap",
      "collection": "/path/to/brain/collection.roadmap",
      "owner_lane": "Lead agent",
      "attention": true
    }
  ],
  "collections": [
    {
      "id": "finance-tasks",
      "title": "Finance",
      "collection": "/path/to/brain/collection.tasks",
      "owner_lane": "Finance",
      "closed": ["done"]
    }
  ]
}
```

- **Legacy attention JSON:** `--attention FILE` still works for an external JSON file written by another program. See [`attention.example.json`](attention.example.json) for the format.

Agents Map reads configured collections read-only on `127.0.0.1`, never exposes host collection file paths to the browser, and serves only the configured records. Clicking an agent's roadmap badge or card opens the roadmap in a live side-by-side split drawer; generic collection items highlight or open their agent without calling the roadmap drawer.

## Add a source

For another agent tool, add a module under `sources/` that returns the same graph document as `sources/repoprompt.py` and pass its collector to `MapServer`.
