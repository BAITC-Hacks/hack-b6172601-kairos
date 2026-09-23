"""Stable CSV tables and browser-safe graph JSON."""

import json
from datetime import datetime, timezone
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

from pipeline.config import CONFIG
from pipeline.continuation import extension_requests
from pipeline.layout import remove_overlaps


ROLE_COLUMNS = ["gid", "role", "role_score", "cluster_id", "priority_score", "evidence"]
CLUSTER_COLUMNS = ["cluster_id", "n_nodes", "n_seed", "sum_kzt_internal", "top_gids", "hypothesis",
                   "n_consolidator", "n_distributor", "n_transit", "taint_kzt"]
TOP_COLUMNS = ["rank", "gid", "role", "priority_score", "why"]


def _layout(projected: nx.Graph) -> dict[int, tuple[float, float]]:
    # NetworkX's sparse layout imports SciPy above 500 nodes. Its dense force
    # implementation has the same spring forces and works with NumPy alone.
    try:
        points = nx.spring_layout(projected, seed=CONFIG.layout_seed, weight=None,
                                  iterations=CONFIG.layout_iterations, method="force")
    except (TypeError, ModuleNotFoundError):
        gids = list(projected.nodes)
        adjacency = nx.to_numpy_array(projected, nodelist=gids, weight=None)
        raw = nx.drawing.layout._fruchterman_reingold(
            adjacency, iterations=CONFIG.layout_iterations, seed=CONFIG.layout_seed
        )
        points = dict(zip(gids, raw))
    maximum = max((max(abs(float(v)) for v in point) for point in points.values()), default=1.0)
    scale = 1000.0 / maximum if maximum else 1.0
    return {gid: (float(point[0]) * scale, float(point[1]) * scale) for gid, point in points.items()}


def write_outputs(metrics: pd.DataFrame, clusters: pd.DataFrame, edges: pd.DataFrame,
                  projected: nx.Graph, directory: str | Path) -> pd.DataFrame:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    ordered = metrics.sort_values("gid")
    extension_requests(metrics).to_csv(directory / "extension_requests.csv", index=False, float_format="%.12g")
    ordered[ROLE_COLUMNS].to_csv(directory / "nodes_roles.csv", index=False, float_format="%.12g")
    clusters[CLUSTER_COLUMNS].to_csv(directory / "clusters.csv", index=False, float_format="%.12g")
    csv_metrics = ordered.copy()
    for column in ("role_explanation", "priority_explanation", "twin_gids", "twin_shared_payers"):
        csv_metrics[column] = csv_metrics[column].map(lambda value: json.dumps(value, separators=(",", ":")))
    csv_metrics.to_csv(directory / "metrics.csv", index=False, float_format="%.12g")
    top = metrics.sort_values(["priority_score", "gid"], ascending=[False, True]).head(CONFIG.top_count).copy()
    top.insert(0, "rank", range(1, len(top) + 1))
    top[TOP_COLUMNS].to_csv(directory / "top_nodes.csv", index=False, float_format="%.12g")
    positions = remove_overlaps(_layout(projected), dict(zip(metrics.gid, metrics.priority_score)))
    nodes = []
    for row in ordered.itertuples(index=False):
        x, y = positions[int(row.gid)]
        nodes.append({
            "id": str(int(row.gid)), "role": row.role, "cluster": int(row.cluster_id),
            "priority": float(row.priority_score), "seed": bool(row.is_seed),
            "skeleton": bool(row.in_skeleton), "level": int(row.hierarchy_level),
            "depth": int(row.depth), "truncated": bool(row.truncated),
            "x": x, "y": y, "evidence": row.evidence,
            "in_kzt": float(row.in_kzt), "out_kzt": float(row.out_kzt),
            "in_deg": int(row.in_deg), "out_deg": int(row.out_deg),
            "role_explanation": row.role_explanation,
            "priority_explanation": row.priority_explanation,
        })
    links = [{"source": str(int(row.src)), "target": str(int(row.dst)),
              "sum_kzt": float(row.sum_kzt), "n_tx": int(row.n_tx)} for row in edges.itertuples(index=False)]
    counts = {role: int((metrics.role == role).sum()) for role in
              ("coordinator", "consolidator", "distributor", "transit", "terminal", "peripheral")}
    document = {"nodes": nodes, "edges": links, "roles_count": counts,
                "generated_at": datetime.now(timezone.utc).isoformat()}
    (directory / "graph.json").write_text(json.dumps(document, ensure_ascii=True, separators=(",", ":")), encoding="utf-8")
    return top
