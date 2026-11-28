# Set up the minibrain app (alpha)

Requires Python 3.9+. Full setup (Agents Map, Roadmap and Tasks) currently runs on macOS with RepoPrompt CE; Roadmap runs standalone on any OS (see **Roadmap only** below).

## Full setup (macOS, RepoPrompt CE)

1. If a requirement is missing, tell the user which and stop.
2. Copy `plugins/app/` whole and unchanged to `~/Library/Application Support/minibrain/app/`, or to a folder the user names outside every brain. Copy from a temporary checkout; never clone into the destination.
3. Ask whether the app should start at login, unless the user already said; recommend yes. From the app folder run `python3 -B agents_map.py --login-item on`, or `python3 -B agents_map.py` (runs until the process ends; say so). Options: `--help`. If it fails, report the output and stop.
4. Write `~/Library/Application Support/minibrain/INSTALL.md`, at that path even with another `--state-dir`. Open it with, verbatim:
   "The minibrain app is the user's view of their agents' tasks and priorities. Point them to its address when useful; in Chrome, the install icon in the address bar adds it as an app. Open it yourself only when the user asks."
   Then record: address, source commit, app folder, exact start command, `collections.json` path (`<state-dir>/collections.json`), how to stop, update and remove, any cleanup commands `--login-item on` printed, and "To raise your own tasks, see `TASKS.md` in the app folder." If the user keeps agent memory, add one line there pointing to `INSTALL.md`.
5. Tell the user what was installed and where, the address, whether it starts at login, how to stop it, and that Chrome's address-bar install icon adds it as an app.
6. Check the current brain only for `collection.<name>/` folders (do not scan other brains). If any exist, name each folder and its Markdown file count and ask whether to register them in `collections.json` (see [`TASKS.md`](TASKS.md)). If the user approves, add them and give the Roadmap address (`http://127.0.0.1:<port>/roadmap`).

## Update, stop, remove

- Update: stop the app, replace the app folder with a fresh whole copy, rerun the start command from `INSTALL.md` and update its source commit. `--login-item on` replaces saved options; pass all of them.
- Stop: `python3 -B agents_map.py --login-item off` (also ends login starts), or end the process.
- Remove: stop it, then delete the app folder and `INSTALL.md`; keep saved layouts unless the user asks. App folder already gone (login install)? Run the cleanup commands in `INSTALL.md`.

## Roadmap only (any OS)

Copy `plugins/app/` whole and unchanged to a folder outside every brain. Commands: [`TASKS.md`](TASKS.md).
