# Agents Map (beta)

Agents Map is a live map of RepoPrompt CE agents and who oversees whom. It reads agent state without changing it.

## Try it with sample data

You need Python 3.9 or later and a browser. Run this from the folder containing `agents_map.py`:

```sh
python3 agents_map.py --demo
```

The demo opens in your browser at `http://127.0.0.1:47614/`. It uses sample data and temporary state, and its links do not open other apps. Add `--no-open` to start the server without opening a browser. Stop it with Ctrl-C.

## Map your agents

Live mode requires macOS and RepoPrompt CE. Run:

```sh
python3 agents_map.py
```

The server reads RepoPrompt CE's saved state without modifying it. It keeps your map arrangement in `~/Library/Application Support/agents-map`.

If another program maintains a list of priorities, run with `--attention FILE` to show them on the map. See [`attention.example.json`](attention.example.json) for the format.

## Add a source

For a different agent tool, add a module under `sources/` that returns the same graph document as `sources/repoprompt.py`. Pass its collector to `MapServer`.
