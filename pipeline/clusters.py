"""Deterministic weighted communities on the undirected money graph."""

import networkx as nx
import pandas as pd

from pipeline.config import CONFIG


def undirected_projection(graph: nx.DiGraph) -> nx.Graph:
    projected = nx.Graph()
    projected.add_nodes_from(graph.nodes)
    for src, dst, data in graph.edges(data=True):
        weight = float(data["sum_kzt"])
        if projected.has_edge(src, dst):
            projected[src][dst]["sum_kzt"] += weight
        else:
            projected.add_edge(src, dst, sum_kzt=weight)
    return projected


def assign_clusters(metrics: pd.DataFrame, edges: pd.DataFrame, graph: nx.DiGraph) -> tuple[pd.DataFrame, nx.Graph]:
    projected = undirected_projection(graph)
    active = projected.subgraph([node for node, degree in projected.degree() if degree > 0]).copy()
    communities = list(nx.community.louvain_communities(
        active, weight="sum_kzt", resolution=CONFIG.louvain_resolution, seed=CONFIG.louvain_seed
    )) if active.number_of_nodes() else []
    communities.extend({node} for node, degree in projected.degree() if degree == 0)
    communities.sort(key=lambda members: (-len(members), min(members)))
    membership = {gid: cluster_id for cluster_id, members in enumerate(communities) for gid in members}
    result = metrics.copy()
    result["cluster_id"] = result.gid.map(membership).astype(int)
    return result, projected


def add_clusters(metrics: pd.DataFrame, edges: pd.DataFrame, graph: nx.DiGraph) -> tuple[pd.DataFrame, pd.DataFrame, nx.Graph]:
    result = metrics.copy()
    projected = undirected_projection(graph)
    membership = dict(zip(result.gid, result.cluster_id))
    communities = [set(group.gid) for _, group in result.groupby("cluster_id", sort=True)]
    internal = edges[edges.src.map(membership).eq(edges.dst.map(membership))].copy()
    internal["cluster_id"] = internal.src.map(membership)
    internal_sums = internal.groupby("cluster_id").sum_kzt.sum().to_dict()
    rows = []
    for cluster_id, members in enumerate(communities):
        group = result[result.cluster_id.eq(cluster_id)]
        ranked = group.sort_values(["priority_score", "gid"], ascending=[False, True])
        n_seed = int(group.is_seed.sum())
        consolidators = group[group.role.eq("consolidator")]
        distributors = group[group.role.eq("distributor")]
        n_transit = int(group.role.eq("transit").sum())
        if len(consolidators) and n_seed >= 2:
            leader = consolidators.sort_values(["priority_score", "gid"], ascending=[False, True]).iloc[0]
            hypothesis = (f"Collection structure: {n_seed} seeds feed consolidator {int(leader.gid)}; "
                          "check as a possible cash-collection node.")
        elif len(distributors):
            leader = distributors.sort_values(["priority_score", "gid"], ascending=[False, True]).iloc[0]
            hypothesis = f"Distribution structure: funds fanned out by {int(leader.gid)} to {int(leader.out_deg)} recipients."
        elif n_transit >= 3:
            hypothesis = f"Layering chain hypothesis: {n_transit} pass-through accounts."
        elif len(members) <= 3:
            hypothesis = "Isolated fragment, low evidence."
        else:
            hypothesis = f"Mixed group of {len(members)} accounts, no dominant pattern."
        rows.append({
            "cluster_id": cluster_id,
            "n_nodes": len(members),
            "n_seed": n_seed,
            "sum_kzt_internal": internal_sums.get(cluster_id, 0),
            "top_gids": ";".join(str(int(gid)) for gid in ranked.gid.head(3)),
            "hypothesis": hypothesis,
            "n_consolidator": len(consolidators),
            "n_distributor": len(distributors),
            "n_transit": n_transit,
            "taint_kzt": group.taint_kzt.sum(),
        })
    return result, pd.DataFrame(rows), projected
