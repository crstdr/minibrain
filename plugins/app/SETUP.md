# Set up minibrain app (alpha)

Local browser app with two views: **Agents Map** (shows who is running, who needs you and who oversees whom; reads RepoPrompt CE on macOS without changing it) and **Roadmap** (dependency graph for any roadmap collection; runs anywhere Python does).

## Agents Map and Roadmap (macOS, RepoPrompt CE)

1. Requires macOS, RepoPrompt CE and Python 3.9 or later. Missing one? Tell the user what is missing and stop.
2. Copy `plugins/app/` whole to `~/Library/Application Support/minibrain/app/` unless the user names another folder; keep it outside private memory and every brain. Copy from a temporary checkout outside the destination; never clone into it. Leave its files unchanged, including `LICENSE`.
3. Unless the user already chose, ask whether the app should start at login; recommend yes, so it survives restarts. Yes: from the app folder, `python3 -B agents_map.py --login-item on`. No: `python3 -B agents_map.py`; it stops when that process ends, so say so. Add any options to either command. If it fails, report its output and stop.
4. Write the install note to `~/Library/Application Support/minibrain/INSTALL.md`, even with another `--state-dir`. Record the source commit, app folder, address, login item on or off, the exact start command with all options, the `--roadmaps` registry path or none, how changes take effect (with the login item, rerun the full recorded command), how to stop, update and remove it, and the cleanup commands `--login-item on` prints. Include: "To raise an item on Agents Map: add attention fields (see `ATTENTION.md` in the app folder) to a record, and list its collection in the registry with the user's approval. For a roadmap collection, see `ROADMAP.md` in the app folder." If the user keeps agent memory, add one line there pointing to this file.
5. Tell the user what was installed and where, the address, whether it starts at login, how to stop it, where the note is, and that supported browsers can install the page as an app while it runs.

## Roadmap only (any OS, no RepoPrompt CE)

Requires Python 3.9+ and a browser. Copy `plugins/app/` whole to a new folder outside every brain (for example `~/tools/minibrain-app/`), leaving `LICENSE` intact. Inside a brain, `sample/collection.roadmap/` would break `minibrain.py check`. Follow [`ROADMAP.md`](ROADMAP.md) to create, check and serve a roadmap collection.

## Options

`--attention FILE`, `--roadmaps FILE`, `--port N`: see [`README.md`](README.md). Keep any registry outside every brain. `--login-item on` replaces its saved options: pass all of them, changed or not.

## Update, stop, remove

- Update: stage a fresh whole copy, stop the app, replace only the app folder, rerun the start command from `INSTALL.md` and update its source commit.
- Stop: `--login-item off`, which also ends login starts; or end the manual process.
- Remove: stop it (app folder already gone: run the cleanup commands in `INSTALL.md`), then delete the app folder and `INSTALL.md`. Keep saved layouts unless the user asks.
