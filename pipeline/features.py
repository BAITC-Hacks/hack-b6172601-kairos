"""Graph and transaction features for every supplied node."""

import networkx as nx
import numpy as np
import pandas as pd

from pipeline.config import CONFIG


def _pagerank(graph: nx.DiGraph, damping: float = 0.85) -> dict[int, float]:
    """Weighted power iteration without a SciPy dependency."""
    gids = list(graph.nodes)
    index = {gid: i for i, gid in enumerate(gids)}
    n = len(gids)
    outgoing = np.zeros(n, dtype=float)
    sources, targets, weights = [], [], []
    for src, dst, data in graph.edges(data=True):
        weight = float(data["sum_kzt"])
        sources.append(index[src])
        targets.append(index[dst])
        weights.append(weight)
        outgoing[index[src]] += weight
    sources = np.asarray(sources, dtype=int)
    targets = np.asarray(targets, dtype=int)
    weights = np.asarray(weights, dtype=float)
    probabilities = np.divide(weights, outgoing[sources], out=np.zeros_like(weights), where=outgoing[sources] != 0)
    rank = np.full(n, 1 / n, dtype=float)
    for _ in range(500):
        new = np.full(n, (1 - damping) / n, dtype=float)
        new += damping * rank[outgoing == 0].sum() / n
        np.add.at(new, targets, damping * rank[sources] * probabilities)
        if np.abs(new - rank).sum() < n * 1e-12:
            rank = new
            break
        rank = new
    return dict(zip(gids, rank.tolist()))


def _fast_pass_share(nodes: pd.DataFrame, transactions: pd.DataFrame) -> dict[int, float]:
    incoming_dates: dict[int, list[np.datetime64]] = {}
    for row in transactions.itertuples(index=False):
        incoming_dates.setdefault(int(row.dst), []).append(row.date.to_datetime64())
    results = {}
    outgoing = transactions.groupby("src", sort=False)
    for gid in nodes.gid:
        dates = incoming_dates.get(int(gid))
        if not dates:
            results[int(gid)] = np.nan
            continue
        if gid not in outgoing.groups:
            results[int(gid)] = 0.0
            continue
        ordered = np.sort(np.asarray(dates, dtype="datetime64[ns]"))
        sent = outgoing.get_group(gid)
        sent_dates = sent.date.to_numpy(dtype="datetime64[ns]")
        positions = np.searchsorted(ordered, sent_dates, side="right") - 1
        eligible = positions >= 0
        eligible[eligible] &= (sent_dates[eligible] - ordered[positions[eligible]]) <= np.timedelta64(CONFIG.fast_pass_days, "D")
        amounts = sent.sum_kzt.to_numpy(dtype=float)
        results[int(gid)] = float(amounts[eligible].sum() / amounts.sum()) if amounts.sum() else 0.0
    return results


def compute_features(nodes: pd.DataFrame, edges: pd.DataFrame, transactions: pd.DataFrame) -> tuple[pd.DataFrame, nx.DiGraph]:
    graph = nx.DiGraph()
    graph.add_nodes_from(nodes.gid.tolist())
    graph.add_weighted_edges_from(((int(r.src), int(r.dst), float(r.sum_kzt)) for r in edges.itertuples(index=False)), weight="sum_kzt")
    result = nodes[["gid", "depth", "is_seed"]].copy().set_index("gid", drop=False)
    incoming = edges.groupby("dst", sort=False).agg(in_deg=("src", "size"), in_kzt=("sum_kzt", "sum"), in_tx=("n_tx", "sum"))
    outgoing = edges.groupby("src", sort=False).agg(out_deg=("dst", "size"), out_kzt=("sum_kzt", "sum"), out_tx=("n_tx", "sum"))
    result = result.join(incoming).join(outgoing)
    for column in ("in_deg", "in_tx", "out_deg", "out_tx"):
        result[column] = result[column].fillna(0).astype("int64")
    for column in ("in_kzt", "out_kzt"):
        result[column] = result[column].fillna(0)
    result["is_seed"] = result.is_seed.astype(bool)
    result["pass_through"] = result.out_kzt.div(result.in_kzt.replace(0, np.nan))
    result["truncated"] = result.depth.eq(4) & result.out_deg.eq(0)
    seeds = set(result.index[result.is_seed].tolist())
    direct: dict[int, set[int]] = {gid: set() for gid in graph.nodes}
    two_hop: dict[int, set[int]] = {gid: set() for gid in graph.nodes}
    for src, dst in graph.edges:
        if src in seeds:
            direct[dst].add(src)
            two_hop[dst].add(src)
    for src, dst in graph.edges:
        two_hop[dst].update(direct[src])
    result["seed_payers_direct"] = [len(direct[gid]) for gid in result.index]
    result["seed_sources_2hop"] = [len(two_hop[gid]) for gid in result.index]
    result["pagerank"] = pd.Series(_pagerank(graph))
    result["betweenness"] = pd.Series(nx.betweenness_centrality(graph, normalized=True, weight=None))
    result["fast_pass_share"] = pd.Series(_fast_pass_share(nodes, transactions))
    return result.reset_index(drop=True), graph
