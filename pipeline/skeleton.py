"""Intersect bounded forward and backward traces of the observed hierarchy."""
from collections import deque

import networkx as nx
import pandas as pd

from pipeline.config import CONFIG


def _distances(graph: nx.DiGraph, origins: set[int]) -> dict[int, int]:
    distances = {gid: 0 for gid in sorted(origins)}
    queue = deque(distances)
    while queue:
        source = queue.popleft()
        if distances[source] >= CONFIG.skeleton_max_hops:
            continue
        for target in graph.successors(source):
            if target not in distances:
                distances[target] = distances[source] + 1
                queue.append(target)
    return distances


def add_skeleton(metrics: pd.DataFrame, edges: pd.DataFrame, graph: nx.DiGraph):
    result = metrics.copy()
    seeds = set(result.loc[result.is_seed, "gid"])
    candidates = result[result.role.isin(["coordinator", "consolidator"])]
    threshold = candidates.taint_kzt.quantile(CONFIG.skeleton_top_quantile)
    tops = set(candidates.loc[candidates.taint_kzt.ge(threshold) & candidates.taint_kzt.gt(0), "gid"])
    forward = _distances(graph, seeds)
    backward = _distances(graph.reverse(copy=False), tops)
    funded = set(result.loc[result.taint_kzt.gt(0), "gid"]) | seeds
    intersection = set(forward) & set(backward) & funded
    inflows = dict(zip(result.gid, result.in_kzt))
    keep = [
        row.src in intersection and row.dst in intersection
        and forward[row.src] < CONFIG.skeleton_max_hops
        and backward[row.dst] < CONFIG.skeleton_max_hops
        and row.sum_kzt >= CONFIG.skeleton_min_inflow_share * inflows[row.dst]
        for row in edges.itertuples(index=False)
    ]
    skeleton_edges = edges.loc[keep, ["src", "dst", "sum_kzt"]].sort_values(["src", "dst"])
    members = set(skeleton_edges.src) | set(skeleton_edges.dst)
    result["in_skeleton"] = result.gid.isin(members)
    result["hierarchy_level"] = result.gid.map(lambda gid: forward[gid] if gid in members else -1).astype(int)
    return result, skeleton_edges
