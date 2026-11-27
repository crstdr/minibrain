# Roadmap (beta)

Renders a minibrain `collection.<name>/` folder as a live dependency graph on `http://127.0.0.1`, highlighting priorities, prerequisites, blockers, and items waiting on the user. Requires Python 3.9 or later and a browser, with no third-party packages.

Keep this plugin folder (including `sample/`) outside every brain so the example collection never collides with a brain's own `collection.roadmap/`.

## Run

From this folder:

```sh
python3 -B roadmap.py --collection /path/to/brain/collection.roadmap --title "Project roadmap"
```

Opens `http://127.0.0.1:47615/` and refreshes automatically while open whenever a record file changes. Strictly read-only on your collection files. Stop with Ctrl-C.

## Commands

- `python3 -B roadmap.py --collection PATH check`: validate mandatory fields, references, and effective prerequisite cycles (exits 1 on problems).
- `python3 -B roadmap.py --collection PATH summary`: text summary of priorities, open work, and items needing you.
- `python3 -B roadmap.py --collection PATH json`: print the roadmap JSON document.
- `python3 -B roadmap.py --collection PATH serve [--port 47615] [--no-open]`: start the local viewer.

See [`SETUP.md`](SETUP.md) for the metadata contract and how to connect roadmaps to Agents Map.
