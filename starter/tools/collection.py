#!/usr/bin/env python3
"""Collections: related records as plain Markdown files.

Collection = brain-root folder <COLLECTION_PREFIX><name>/; default prefix
"collection." (collection.tasks/). Record = one Markdown file in it; the
filename stem is its id, stable and unique within the collection
(collection.tasks/T-0142.md has id T-0142; ids contain no spaces).

Layout: title line; optional "- key: value" bullets directly below it, ending
at the first blank line; then the brain's own Markdown. Parsed keys, all
optional: state (the brain's vocabulary); tags (#tag …); needs (space-separated
prerequisite ids: <id> in this collection, <name>/<id> in another). Other keys
and the body are the brain's.

Archive by state, never by deletion; a merged record keeps a successor link and
the reason. The core leaves collection folders unmanaged: records need no Map
entry, and a commit confined to collection folders needs no changelog line;
durable outcomes still get theirs.
"""

COLLECTION_PREFIX = "collection."

if __name__ == "__main__":
    print(__doc__.strip())
