# Set up Agents Map (beta)

Agents Map shows RepoPrompt CE agents and who oversees whom: who is running, who needs the user, and which oversight links were recently active. It reads agent state without changing it. It is MIT-licensed.

1. Copy the `agents-map/` folder whole to `agents-map/` in the destination, from a temporary checkout of the source outside the destination. Never clone into the destination. Leave its files unchanged, including its `LICENSE`. To refresh, replace the whole folder.
2. From that folder, start the demo in the background: `python3 -B agents_map.py --demo`. It needs Python 3.9 or later, uses sample data and opens `http://127.0.0.1:47614/`. Tell the user the address and how to stop it.
3. For live data, follow [`agents-map/README.md`](agents-map/README.md), running its commands with `python3 -B`. Live mode needs macOS and RepoPrompt CE.
