"""Shared-source account pairs and transitive review groups."""

import json
from collections import Counter, defaultdict
from itertools import combinations

import networkx as nx
import pandas as pd

from pipeline.config import CONFIG

TWIN_HYPOTHESIS = (
    "Accounts receiving from the same collectors — possibly one controller or deliberate split of proceeds; review together"
)
GROUP_COLUMNS = ["group_id", "gids", "shared_payers", "total_in_kzt", "hypothesis"]


def add_shared_sources(metrics: pd.DataFrame, graph: nx.DiGraph) -> pd.DataFrame:
    """Use distinct observed predecessors; each qualifying pair is symmetric."""
    result = metrics.copy()
    gids = {int(gid) for gid in metrics.gid}
    payers = {gid: set(graph.predecessors(gid)) if gid in graph else set() for gid in gids}
    shared = Counter()
    for payer in graph:
        recipients = sorted(gids.intersection(graph.successors(payer)))
        shared.update(combinations(recipients, 2))
    links = defaultdict(dict)
    twin_graph = nx.Graph()
    for (a, b), count in sorted(shared.items()):
        union_size = len(payers[a]) + len(payers[b]) - count
        if count < CONFIG.twin_min_shared_payers or count / union_size < CONFIG.twin_min_jaccard:
            continue
        links[a][str(b)] = count
        links[b][str(a)] = count
        twin_graph.add_edge(a, b)
    groups = {}
    components = sorted((sorted(group) for group in nx.connected_components(twin_graph)), key=lambda group: group[0])
    for index, members in enumerate(components, 1):
        for gid in members:
            groups[gid] = f"twin-{index:03d}"
    result["shared_sources_twin"] = result.gid.map(lambda gid: bool(links[int(gid)]))
    result["twin_gids"] = result.gid.map(lambda gid: sorted(links[int(gid)]))
    result["twin_shared_payers"] = result.gid.map(lambda gid: dict(sorted(links[int(gid)].items())))
    result["twin_group"] = result.gid.map(lambda gid: groups.get(int(gid), ""))
    return result


def twin_groups(metrics: pd.DataFrame, graph: nx.DiGraph) -> pd.DataFrame:
    """Shared payers is the union supporting direct qualifying pairs in a group.

    Transitive group membership does not imply every pair qualifies, or that
    every group member receives from every payer listed in the group export.
    """
    rows = []
    for group_id, members in metrics[metrics.twin_group.ne("")].groupby("twin_group", sort=True):
        shared_payers = set()
        for row in members.itertuples(index=False):
            for other in row.twin_gids:
                shared_payers.update(set(graph.predecessors(int(row.gid))) & set(graph.predecessors(int(other))))
        rows.append({
            "group_id": group_id,
            "gids": json.dumps([str(int(gid)) for gid in sorted(members.gid)], separators=(",", ":")),
            "shared_payers": json.dumps([str(int(gid)) for gid in sorted(shared_payers)], separators=(",", ":")),
            "total_in_kzt": float(members.in_kzt.sum()),
            "hypothesis": TWIN_HYPOTHESIS,
        })
    return pd.DataFrame(rows, columns=GROUP_COLUMNS)
