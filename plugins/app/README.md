# minibrain app (alpha)

Local observability and visualisation for multi-agent work: **Agents Map** for active agents, oversight links, open tasks and attention items (macOS, RepoPrompt CE only), **Roadmap** for cross-collection dependency graphs (any OS), and **Tasks** as plain Markdown files inside each agent's brain.

To install, ask your agent to follow [`SETUP.md`](SETUP.md).

To preview with sample data, run from this folder (Python 3.9+):

```sh
python3 -B agents_map.py --demo
python3 -B tasks.py --collection sample/collection.roadmap serve
```

The app runs locally on `http://127.0.0.1:47613/` and reads your agents' files read-only. In Chrome, the install icon in the address bar adds it as an app.

For the task format, registry and CLI commands, see [`TASKS.md`](TASKS.md). To support another agent tool, add a module under `sources/` that returns the same graph document as `sources/repoprompt.py`.
