# Agents Map (beta)

Agents Map is a local map of your agents and who oversees whom. Its built-in connector works with RepoPrompt CE on macOS and reads agent state without changing it.

## Run

Requires macOS, RepoPrompt CE, Python 3.9 or later, and a browser. Run from this folder (kept outside every brain):

```sh
python3 -B agents_map.py
```

The map opens at `http://127.0.0.1:47613/`. Add `--no-open` to start without opening a browser, or `--port N` to choose another port. Stop with Ctrl-C.

Your arrangement (layouts, groups, saves) is kept in `~/Library/Application Support/agents-map` (`--state-dir DIR`), never in RepoPrompt CE's folder or any brain.

## Connect roadmaps and attention items

- **Attention list:** pass `--attention FILE` to show items written by another program. See [`attention.example.json`](attention.example.json) for the format.
- **Collection-backed roadmaps:** pass `--roadmaps FILE` pointing to a JSON registry kept outside every brain (quote the path if it contains spaces):

```sh
python3 -B agents_map.py \
  --roadmaps "$HOME/Library/Application Support/agents-map/roadmaps.json"
```

Example registry (`id` must be a unique slug and not `default`):

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
  ]
}
```

Agents Map reads configured collections read-only on `127.0.0.1`, never exposes host collection file paths to the browser, and serves only the configured records. Clicking an agent's roadmap badge or card opens the roadmap in a live side-by-side split drawer.

## Add a source

For another agent tool, add a module under `sources/` that returns the same graph document as `sources/repoprompt.py` and pass its collector to `MapServer`.
