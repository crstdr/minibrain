# minibrain app (alpha)

A local browser companion for minibrain with two views over the same collection items: **Agents Map** (live map of your agents, oversight links, Attention and open items) and **Roadmap** (dependency graph when items use `needs` or `serves`). The app is in alpha: Agents Map needs macOS and RepoPrompt CE, while Roadmap runs wherever Python 3.9+ does.

## Run Agents Map (macOS, RepoPrompt CE)

Requires macOS, RepoPrompt CE, Python 3.9 or later and a browser. Run from this folder (kept outside every brain):

```sh
python3 -B agents_map.py
```

The map opens at `http://127.0.0.1:47613/`. Add `--no-open` to start without opening a browser, `--port N` to choose another port, or `--demo` to preview sample data without RepoPrompt CE. Stop with Ctrl-C.

Start at login: `python3 -B agents_map.py --login-item on` with the same options you run with; `--login-item off` stops it and removes the login item. In Chrome, the install icon in the address bar installs the page as an app.

Layouts, saves and the default `collections.json` registry live in `~/Library/Application Support/minibrain` (`--state-dir DIR`), never in RepoPrompt CE's folder or any brain.

## Run Roadmap standalone (any OS)

Requires Python 3.9+ and a browser (no RepoPrompt CE needed). See [`ITEMS.md`](ITEMS.md) for the item contract and CLI commands, or try the bundled sample:

```sh
python3 -B roadmap.py --collection sample/collection.roadmap check
python3 -B roadmap.py --collection sample/collection.roadmap serve --title "Studio roadmap"
```

## Connect collections

Add approved collections to `~/Library/Application Support/minibrain/collections.json` (or pass `--collections FILE` pointing to a registry outside every brain). See [`ITEMS.md`](ITEMS.md) for the item contract.

Example registry (`id` must be a unique slug and not `default`; `title`, `lane` and `lane_link` are optional):

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

The app reads registered collections read-only on `127.0.0.1` and never leaks host paths in metadata or errors. Each agent's card shows its Attention and open counts and opens a panel listing Attention items first, then other open items, with the lane link; collections with `needs` or `serves` also open in the live side-by-side Roadmap drawer.

## Update and remove

Replace only the app folder, rerun your start command, and update the source commit in `~/Library/Application Support/minibrain/INSTALL.md`. To remove, stop it (`python3 -B agents_map.py --login-item off` for login installs, or end the manual process) and delete the app folder and `INSTALL.md` (saved layouts in the state folder stay). For a `--login-item on` install whose app folder is already gone, run the two cleanup commands `--login-item on` printed (also in `INSTALL.md`), then delete `INSTALL.md`.

## Add a source

For another agent tool, add a module under `sources/` that returns the same graph document as `sources/repoprompt.py` and pass its collector to `MapServer`.
