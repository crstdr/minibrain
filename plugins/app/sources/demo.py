"""Sample studio data, independent of local app state."""
import time

STUDIO = (
    ("Studio desk", ("Studio lead", "Schedule keeper")),
    ("Product bench", ("Feature planner", "Interview reader", "Release editor")),
    ("App workshop", ("Interaction builder", "Sync maintainer", "Build reviewer")),
    ("Web showcase", ("Gallery designer", "Asset preparer")),
    ("Support desk", ("Queue reader", "Reply drafter")),
    ("Accounts desk", ("Invoice checker", "Budget keeper")),
    ("Research room", ("Prototype builder", "Source reader", "Notes editor")),
)
# Each pair is an overseer and one of their lanes.
EDGES = ((0, 2), (0, 5), (0, 8), (0, 10), (0, 12), (0, 14), (1, 4),
         (2, 3), (5, 6), (5, 7), (10, 11), (14, 15))


def agent_id(index):
    return "DEMO-A%d" % index


def collect(recent=False, known=()):
    """Return the full sample studio for either layout or recent-agent setting."""
    now = int(time.time())
    tick = now // 20
    windows, agents = [], []
    bosses = {target: owner for owner, target in EDGES}
    linked = {index for pair in EDGES for index in pair}
    for w, (name, lanes) in enumerate(STUDIO):
        wid = "DEMO-W%d" % w
        tab = "DEMO-T%d" % len(agents)
        windows.append(dict(id=wid, name=name, count=1, tab=tab, session=agent_id(len(agents))))
        for lane in lanes:
            i = len(agents)
            at = tick * 20 - (i * 920 if i not in (5, 12) else 25)
            cli, model = (("codexExec", "Juniper 2"), ("claudeCode", "Kestrel 4"), ("openCode", "Flint 3"))[i % 3]
            agents.append(dict(id=agent_id(i), ws=wid, tab="DEMO-T%d" % i, name=lane,
                               cli=cli, model=model, effort="medium",
                               used=8000 + i * 4200, window=100000,
                               state={5: "running", 12: "waitingForApproval", 8: "failed"}.get(i, "completed"),
                               last=at, state_at=(now // 3600 * 3600 - 60 if i == 12 else at),
                               lane_of=agent_id(bosses[i]) if i in bosses else None,
                               wake=dict(all=i == 0, lanes=[], limit=0, idle=0),
                               out_hidden=0, in_hidden=0, linked=i in linked, pinned=False, stale=False))
    windows[0]["color"] = "violet"
    windows[2]["color"] = "teal"
    links = [dict(o=agent_id(o), t=agent_id(t)) for o, t in EDGES]
    for offset, kind in enumerate(("wake", "watch", "attn", "msg")):
        links[(tick + offset * 3) % len(links)][kind] = now - offset * 10
    return dict(schema=2, generated=now, windows=windows, agents=agents, links=links,
                hidden=dict(archived=0, no_window=0, no_tab=0, missing=0, links=0),
                warnings=[], app_running=True, demo=True)
