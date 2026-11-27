# Set up Agents Map (beta)

Agents Map shows your agents and who oversees whom: who is running, who needs you, and which oversight links were recently active. Its built-in connector works with RepoPrompt CE on macOS and reads agent state without changing it. It is MIT-licensed.

1. Requires macOS, RepoPrompt CE and Python 3.9 or later. Missing one? Tell the user what is missing and stop.
2. Copy the `agents-map/` folder whole to the app folder, `~/Library/Application Support/agents-map/app/` unless the user names another; keep it outside private memory and every brain. Copy from a temporary checkout of the source outside the destination; never clone into the destination. Leave its files unchanged, including its `LICENSE`.
3. Unless the user already chose, ask whether the map should start at login; recommend yes, so it survives restarts. Yes: from the app folder, `python3 -B agents_map.py --login-item on`. No: `python3 -B agents_map.py`; it stops when that process ends, so say so. Add any options to either command. If it fails, report its output and stop.
4. Write the install note to `~/Library/Application Support/agents-map/INSTALL.md`, even with another `--state-dir`. Record the source commit, app folder, address, login item on or off, the exact start command with all options, the `--roadmaps` registry path or none, how changes take effect (with the login item, rerun the full recorded command), how to stop, update and remove it, and the cleanup commands `--login-item on` prints. Include one line: "To raise an item on the map: add attention fields (see `ATTENTION.md` in the app folder) to a record, and list its collection in the registry with the user's approval." If the user keeps agent memory, add one line there pointing to this file.
5. Tell the user what was installed and where, the address, whether it starts at login, how to stop it, where the note is, and that supported browsers can install the page as an app while the map runs.

## Options

`--attention FILE`, `--roadmaps FILE`, `--port N`: see [`README.md`](README.md). Keep any roadmap registry outside every brain. `--login-item on` replaces its saved options: pass all of them, changed or not.

## Update, stop, remove

- Update: stage a fresh whole copy, stop the map, replace only the app folder, rerun the start command from `INSTALL.md` and update its source commit.
- Stop: `--login-item off`, which also ends login starts; or end the manual process.
- Remove: stop it (app folder already gone: run the cleanup commands in `INSTALL.md`), then delete the app folder and `INSTALL.md`. Keep saved layouts unless the user asks.
