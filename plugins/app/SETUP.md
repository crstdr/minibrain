# Set up minibrain app (alpha)

Local browser app with two views: **Agents Map** (live agent status, oversight links, Attention and open items; reads RepoPrompt CE on macOS read-only) and **Roadmap** (dependency graph for collections using `needs`/`serves`; runs anywhere Python 3.9+ does).

## Agents Map and Roadmap (macOS, RepoPrompt CE)

1. Requires macOS, RepoPrompt CE and Python 3.9+. Missing one? Tell the user what is missing and stop.
2. Copy `plugins/app/` whole to `~/Library/Application Support/minibrain/app/` unless the user names another folder; keep it outside private memory and every brain. Copy from a temporary checkout outside the destination; never clone into it. Leave its files unchanged, including `LICENSE`.
3. Unless the user already chose, ask whether the app should start at login; recommend yes. Yes: from the app folder, `python3 -B agents_map.py --login-item on`. No: `python3 -B agents_map.py` (stops when the process ends; say so). Add any options to either command. If it fails, report its output and stop.
4. Write `~/Library/Application Support/minibrain/INSTALL.md` (even with another `--state-dir`). Open it verbatim with:
   "The minibrain app is the user's view of their agents' tasks and priorities. Point them to its address when useful; in Chrome, the install icon in the address bar adds it as an app. Open it yourself only when the user asks."
   Then record: address, source commit, app folder, login item on or off, exact start command with all options, `collections.json` path (default `<state-dir>/collections.json`; default state dir `~/Library/Application Support/minibrain`), how to stop, update and remove it, if using `--login-item on`, the cleanup commands it prints, and one line: "To raise your own items, see `ITEMS.md` in the app folder." If the user keeps agent memory, add one line pointing to `INSTALL.md`.
5. Tell the user what was installed and where, the address, whether it starts at login, how to stop it, where `INSTALL.md` is, and that Chrome can install the page as an app from the address bar.

## Roadmap only (any OS, no RepoPrompt CE)

Requires Python 3.9+ and a browser. Copy `plugins/app/` whole to a folder outside every brain (for example `~/tools/minibrain-app/`), leaving `LICENSE` intact. Inside a brain, `sample/collection.roadmap/` would fail `minibrain.py check`. See [`ITEMS.md`](ITEMS.md) for the item contract and standalone `roadmap.py` commands.

## Options

`--port N`, `--no-open`, `--state-dir DIR`, `--collections FILE`, `--demo`: see [`README.md`](README.md). Keep the registry outside every brain. `--login-item on` replaces its saved options: pass all of them, changed or not.

## Update, stop, remove

- Update: stage a fresh whole copy, stop the app, replace only the app folder, rerun the start command from `INSTALL.md` and update its source commit.
- Stop: `--login-item off` (also ends login starts), or end the manual process.
- Remove: stop it (for `--login-item on` installs whose app folder is already gone, run the cleanup commands in `INSTALL.md`), then delete the app folder and `INSTALL.md`. Keep saved layouts unless the user asks.
