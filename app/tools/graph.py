"""Read-only graph tools for the analyst assistant.

The language model never computes anything itself: it calls these functions,
which read the pipeline outputs in out/ (the same snapshot the viewer uses),
and then explains the returned numbers. Identifiers are strings; a caller may
pass the last digits of a gid, which is resolved to the highest-priority match.
"""
from __future__ import annotations

from collections import deque
from typing import Any

from app.agent.registry import tool

MAX_LIST = 10


def _data() -> dict[str, Any]:
    from app.api.viewer import store  # lazy: avoids an import cycle at startup

    return store.load()


def _resolve(data: dict[str, Any], gid: str) -> str | None:
    gid = str(gid).strip().lstrip(".…")
    if gid in data["nodes"]:
        return gid
    matches = [g for g in data["nodes"] if g.endswith(gid)] if len(gid) >= 4 else []
    if not matches:
        return None
    return max(matches, key=lambda g: (data["nodes"][g].get("priority_score") or 0, g))


def _brief(data: dict[str, Any], gid: str) -> dict[str, Any]:
    n = data["nodes"][gid]
    return {
        "gid": gid,
        "role": n.get("role"),
        "priority_score": n.get("priority_score"),
        "is_seed": n.get("is_seed"),
        "evidence": n.get("evidence"),
    }


@tool(
    name="get_account",
    description=(
        "Full card of one account: role, role evidence, priority and its drivers, findings, "
        "metrics (payers, recipients, KZT in/out, case-money taint, seeds within 2 hops), cluster "
        "hypothesis and the largest incoming/outgoing links with amounts. Accepts a full gid or its last digits."
    ),
    parameters={
        "type": "object",
        "properties": {"gid": {"type": "string", "description": "Full gid or at least the last 4 digits"}},
        "required": ["gid"],
    },
)
def get_account(gid: str) -> dict[str, Any]:
    data = _data()
    g = _resolve(data, gid)
    if g is None:
        return {"error": f"Account {gid} not found"}
    n = data["nodes"][g]
    keep = (
        "role", "role_score", "priority_score", "evidence", "why", "findings", "cluster_id", "depth", "is_seed",
        "in_deg", "out_deg", "in_kzt", "out_kzt", "pass_through", "taint_kzt", "seed_sources_2hop",
        "fast_pass_share", "truncated", "peripheral_reason", "p_continues", "likely_legit_payouts", "seed_hub",
    )
    cluster = data["clusters_by_id"].get(n.get("cluster_id"), {})
    return {
        "gid": g,
        **{k: n.get(k) for k in keep if k in n},
        "cluster_hypothesis": cluster.get("hypothesis"),
        "incoming_top": data["incoming"][g][:MAX_LIST],
        "outgoing_top": data["outgoing"][g][:MAX_LIST],
        "incoming_count": len(data["incoming"][g]),
        "outgoing_count": len(data["outgoing"][g]),
    }


@tool(
    name="top_accounts",
    description="Highest-priority accounts, optionally filtered by role "
    "(coordinator, consolidator, transit, distributor, terminal, peripheral).",
    parameters={
        "type": "object",
        "properties": {
            "role": {"type": "string", "description": "Optional role filter"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 20},
        },
    },
)
def top_accounts(role: str | None = None, limit: int = 10) -> dict[str, Any]:
    data = _data()
    rows = [g for g, n in data["nodes"].items() if not role or n.get("role") == role]
    rows.sort(key=lambda g: -(data["nodes"][g].get("priority_score") or 0))
    return {"role": role, "accounts": [_brief(data, g) for g in rows[: max(1, min(limit, 20))]]}


@tool(
    name="who_collects_from",
    description=(
        "Given several accounts, find the accounts downstream (following the money, up to max_hops) that "
        "receive money from at least two of them - candidate collection points. Pass the SOURCE accounts "
        "(e.g. the payers or seeds you are interested in), at least two. To analyse the payers of an account X, "
        "first call get_account(X) and pass the gids from its incoming_top. Ranked by how many of the given "
        "accounts reach them, then by priority."
    ),
    parameters={
        "type": "object",
        "properties": {
            "gids": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 20},
            "max_hops": {"type": "integer", "minimum": 1, "maximum": 4},
        },
        "required": ["gids"],
    },
)
def who_collects_from(gids: list[str], max_hops: int = 2) -> dict[str, Any]:
    data = _data()
    resolved, missing = [], []
    for raw in gids:
        g = _resolve(data, raw)
        (resolved.append(g) if g else missing.append(raw))
    if len(resolved) < 2:
        return {
            "error": "Need at least two source accounts. To analyse the payers of one account, call get_account "
            "first and pass the gids from incoming_top.",
            "inputs": resolved,
            "not_found": missing,
        }
    reached: dict[str, dict[str, int]] = {}
    for source in resolved:
        seen = {source: 0}
        queue = deque([source])
        while queue:
            current = queue.popleft()
            if seen[current] >= max_hops:
                continue
            for link in data["outgoing"][current]:
                nxt = link["gid"]
                if nxt not in seen:
                    seen[nxt] = seen[current] + 1
                    queue.append(nxt)
        for g, hops in seen.items():
            if g != source:
                reached.setdefault(g, {})[source] = hops
    common = [(g, s) for g, s in reached.items() if len(s) >= 2]
    common.sort(key=lambda item: (-len(item[1]), -(data["nodes"][item[0]].get("priority_score") or 0)))
    return {
        "inputs": resolved,
        "not_found": missing,
        "max_hops": max_hops,
        "collectors": [
            {**_brief(data, g), "reached_from": len(s), "hops_by_source": s} for g, s in common[:MAX_LIST]
        ],
    }


@tool(
    name="money_paths",
    description=(
        "Paths the money took from one account to another (following transfer direction, up to 4 hops), "
        "with the amount on every step. Returns up to 3 paths with the largest bottleneck amount."
    ),
    parameters={
        "type": "object",
        "properties": {"source": {"type": "string"}, "target": {"type": "string"}},
        "required": ["source", "target"],
    },
)
def money_paths(source: str, target: str) -> dict[str, Any]:
    data = _data()
    s, t = _resolve(data, source), _resolve(data, target)
    if s is None or t is None:
        return {"error": "Account not found", "source": source, "target": target}
    paths: list[list[dict[str, Any]]] = []
    budget = [20000]

    def walk(node: str, path: list[dict[str, Any]], visited: set[str]) -> None:
        budget[0] -= 1
        if budget[0] <= 0 or len(path) > 4:
            return
        if node == t and path:
            paths.append(list(path))
            return
        for link in data["outgoing"][node]:
            nxt = link["gid"]
            if nxt in visited:
                continue
            path.append({"from": node, "to": nxt, "sum_kzt": link["sum_kzt"], "n_tx": link["n_tx"]})
            visited.add(nxt)
            walk(nxt, path, visited)
            visited.discard(nxt)
            path.pop()

    walk(s, [], {s})
    paths.sort(key=lambda p: -min(step["sum_kzt"] for step in p))
    return {
        "source": s,
        "target": t,
        "paths": [
            {"hops": len(p), "bottleneck_kzt": min(step["sum_kzt"] for step in p), "steps": p} for p in paths[:3]
        ],
        "note": None if paths else "No directed path of up to 4 hops in the observed graph.",
    }


@tool(
    name="cluster_summary",
    description="Summary of one cluster: size, seeds, internal turnover, role mix, hypothesis and top accounts.",
    parameters={
        "type": "object",
        "properties": {"cluster_id": {"type": "integer"}},
        "required": ["cluster_id"],
    },
)
def cluster_summary(cluster_id: int) -> dict[str, Any]:
    data = _data()
    row = data["clusters_by_id"].get(cluster_id)
    if row is None:
        return {"error": f"Cluster {cluster_id} not found"}
    return dict(row)
