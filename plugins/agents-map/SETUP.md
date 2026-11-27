# Set up Agents Map (beta)

Agents Map shows your agents and who oversees whom: who is running, who needs you, and which oversight links were recently active. Its built-in connector works with RepoPrompt CE on macOS and reads agent state without changing it. It is MIT-licensed.

1. Copy the `agents-map/` folder whole to `agents-map/` outside private memory and outside every brain, from a temporary checkout of the source outside the destination. Never clone into the destination. Leave its files unchanged, including its `LICENSE`. To refresh, replace the whole folder.
2. From that folder, start the server: `python3 -B agents_map.py`. It needs Python 3.9 or later and opens `http://127.0.0.1:47613/`. Tell the user the address and how to stop it.
3. Optional flags (see [`README.md`](README.md)):
   - `--attention FILE`: show external attention items (see `attention.example.json`).
   - `--roadmaps FILE`: connect one or more collection-backed roadmaps so clicking an agent opens its roadmap in a side-by-side split drawer. Keep the registry file outside every brain and quote paths containing spaces, for example:
     ```sh
     python3 -B agents_map.py \
       --roadmaps "$HOME/Library/Application Support/agents-map/roadmaps.json"
     ```
